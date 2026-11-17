"""IP geolocation helpers.

Geolocation runs on a background thread pool. The request path only reads the
shared cache. A cache miss schedules a lookup and returns a fallback straight
away, so page rendering never waits for an external service.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.core.cache import cache
import logging
import ipaddress

logger = logging.getLogger(__name__)

# Constants for IP geolocation
IP_LOCATION_CACHE_TIMEOUT = 3600  # 1 hour for successful lookups
IP_LOCATION_FAILURE_CACHE_TIMEOUT = (
    300  # 5 minutes for failed lookups (prevents hammering)
)

# Process-level cache for the server's own public IP (behind proxy/private networks)
PUBLIC_IP_CACHE_TIMEOUT = 21600  # 6 hours for successful lookups
PUBLIC_IP_FAILURE_CACHE_TIMEOUT = 600  # 10 minutes for failed lookups

# Time-outs. These calls run on a background thread, so the values protect the
# worker pool rather than the visitor. They are deliberately short.
PUBLIC_IP_TIMEOUT = 1.0
IP_API_TIMEOUT = 1.5

# Background lookup pool
GEO_WORKER_COUNT = 2
GEO_PENDING_TTL = 60  # dedupe window: one scheduled lookup per IP at a time

# Circuit breaker. ip-api.com's free tier allows 45 requests/minute, so the
# site must stop calling a service that is failing or rate limiting.
GEO_CIRCUIT_FAILURE_LIMIT = 5
GEO_CIRCUIT_FAILURE_TTL = 300  # 5 minutes for the failure counter
GEO_CIRCUIT_OPEN_TTL = 900  # 15 minutes with the circuit open

# Opt-in wait, used only by endpoints that cannot answer without coordinates.
GEO_WAIT_POLL_INTERVAL = 0.025
GEO_WAIT_MAX_SECONDS = 2.0

# Non-page paths/extensions and User-Agent tokens that must never trigger
# external geolocation lookups
NON_PAGE_PATHS = ("/robots.txt", "/sitemap.xml", "/favicon.ico")
NON_PAGE_PATH_SUFFIXES = (
    ".php",
    ".env",
    ".git",
    ".yaml",
    ".yml",
    ".json",
    # Archive, dump and backup targets that scanners request constantly.
    ".sql",
    ".gz",
    ".zip",
    ".tar",
    ".bz2",
    ".xz",
    ".7z",
    ".bak",
    ".old",
    ".save",
    ".swp",
    ".orig",
    ".dump",
    ".local",
    ".conf",
    ".ini",
    ".cfg",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".key",
    ".pem",
    ".crt",
    ".p12",
    ".asc",
    ".gpg",
    ".kdbx",
)
BOT_USER_AGENT_TOKENS = (
    "bot",
    "crawl",
    "spider",
    "slurp",
    "curl",
    "wget",
    "python-requests",
    "headless",
    # HTTP clients and scanners that do not advertise themselves as bots.
    "go-http-client",
    "java/",
    "okhttp",
    "python-urllib",
    "libwww-perl",
    "zgrab",
    "masscan",
    "nmap",
    "nuclei",
    "nikto",
    "sqlmap",
    "acunetix",
    "nessus",
    "openvas",
    "dirbuster",
    "gobuster",
    "ffuf",
    "wpscan",
    "postmanruntime",
    "insomnia",
    "node-fetch",
    "axios",
    "httpclient",
    "phpcrawl",
    "yandex",
    "baidu",
    "semrush",
    "ahrefs",
    "mj12",
    "dotbot",
    "petalbot",
    "seekport",
    "ia_archiver",
)

# Background executor for geolocation work. The tasks never touch the database,
# so no thread-local connection is created.
_geo_executor = ThreadPoolExecutor(
    max_workers=GEO_WORKER_COUNT, thread_name_prefix="geo"
)

# Process-level cache for the server's own public IP
_public_ip_cache = {"ip": None, "fetched_at": 0.0}
_public_ip_lock = threading.Lock()
_public_ip_pending = False


def _is_private_or_internal_ip(ip):
    """
    Check if an IP address is private, internal, or localhost.
    This includes Docker networks, private LANs, and localhost.
    Returns True for IPs that should not be used for geolocation.
    """
    if not ip or ip in ["127.0.0.1", "localhost", "::1", "UNKNOWN"]:
        return True

    try:
        ip_obj = ipaddress.ip_address(ip)
        # Check for:
        # - 127.0.0.0/8 (localhost)
        # - 10.0.0.0/8 (private)
        # - 172.16.0.0/12 (private - Docker default)
        # - 192.168.0.0/16 (private)
        # - 169.254.0.0/16 (link-local)
        # - fc00::/7 (unique local addresses - IPv6)
        return (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
        )
    except ValueError:
        # Not a valid IP address
        return True


def _create_session_with_retries(retries=1, backoff_factor=0.2):
    """Create a requests session with retry logic for transient failures."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _has_dot_segment(path):
    """
    Return True if any path segment starts with a dot.

    A dot segment marks a hidden file or directory, for example
    /.git/config, /.well-known/traffic-advice or /cron/.env.production.local.
    None of these are real pages, and background scanners request them in bulk.
    """
    return any(segment.startswith(".") for segment in path.split("/") if segment)


def is_bot_or_non_page_request(request):
    """
    Check if a request comes from a bot/crawler or targets a non-page path
    (robots.txt, sitemaps, favicons, scanner probes). Such requests should
    skip IP geolocation entirely to avoid any external lookup.
    """
    path = request.path.lower()

    if path in NON_PAGE_PATHS or path.startswith("/.well-known"):
        return True

    if path.endswith(NON_PAGE_PATH_SUFFIXES):
        return True

    if _has_dot_segment(path):
        return True

    user_agent = (request.META.get("HTTP_USER_AGENT") or "").lower()

    # A missing User-Agent is almost always a script, not a browser.
    if not user_agent.strip():
        return True

    return any(token in user_agent for token in BOT_USER_AGENT_TOKENS)


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


def _circuit_open_key(service):
    return f"geo_circuit_open_{service}"


def _circuit_fail_key(service):
    return f"geo_circuit_fails_{service}"


def _circuit_is_open(service):
    """Return True while the circuit for this service is open."""
    try:
        return cache.get(_circuit_open_key(service)) is not None
    except Exception:
        return False


def _circuit_record_failure(service):
    """Count a failure and open the circuit once the limit is reached."""
    try:
        count = cache.get(_circuit_fail_key(service)) or 0
        if count + 1 >= GEO_CIRCUIT_FAILURE_LIMIT:
            cache.set(_circuit_fail_key(service), 0, GEO_CIRCUIT_FAILURE_TTL)
            cache.set(_circuit_open_key(service), 1, GEO_CIRCUIT_OPEN_TTL)
            logger.warning(
                "Geolocation circuit opened for %s for %ss",
                service,
                GEO_CIRCUIT_OPEN_TTL,
            )
        else:
            cache.set(_circuit_fail_key(service), count + 1, GEO_CIRCUIT_FAILURE_TTL)
    except Exception:
        # A cache failure must not break the caller.
        pass


def _circuit_record_success(service):
    try:
        cache.delete(_circuit_fail_key(service))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Server public IP (non-blocking)
# ---------------------------------------------------------------------------


def _read_cached_public_ip():
    """Return the cached server public IP, or None if the cache is empty."""
    cached_ip = _public_ip_cache["ip"]
    if not cached_ip:
        return None

    ttl = (
        PUBLIC_IP_FAILURE_CACHE_TIMEOUT
        if cached_ip == "UNKNOWN"
        else PUBLIC_IP_CACHE_TIMEOUT
    )
    if time.time() - _public_ip_cache["fetched_at"] < ttl:
        return cached_ip

    return None


def _schedule_public_ip_refresh():
    """Refresh the server public IP on the background pool. Returns at once."""
    global _public_ip_pending

    with _public_ip_lock:
        if _public_ip_pending:
            return
        _public_ip_pending = True

    try:
        _geo_executor.submit(_run_public_ip_refresh)
    except RuntimeError:
        with _public_ip_lock:
            _public_ip_pending = False


def _run_public_ip_refresh():
    """Fetch the server public IP. The lock is not held during the call."""
    global _public_ip_pending

    try:
        try:
            response = requests.get(
                "https://api64.ipify.org?format=json", timeout=PUBLIC_IP_TIMEOUT
            )
            public_ip = response.json().get("ip") or "UNKNOWN"
            if public_ip != "UNKNOWN":
                logger.info("Public IP fetched for geolocation: %s", public_ip)
        except Exception as e:
            logger.warning("Failed to fetch public IP: %s", e)
            public_ip = "UNKNOWN"

        with _public_ip_lock:
            _public_ip_cache["ip"] = public_ip
            _public_ip_cache["fetched_at"] = time.time()
    finally:
        with _public_ip_lock:
            _public_ip_pending = False


# ---------------------------------------------------------------------------
# Client IP
# ---------------------------------------------------------------------------


def get_client_ip(request):
    """
    Extracts the client's IP address from the request.

    This function never makes a network call. When the request arrives from a
    private address and the server public IP is not in the process cache, the
    refresh runs in the background and the original address is returned so that
    callers which bucket by IP stay correct.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR") or ""

    if _is_private_or_internal_ip(ip):
        public_ip = _read_cached_public_ip()
        if public_ip:
            return public_ip

        _schedule_public_ip_refresh()
        return ip

    return ip


# ---------------------------------------------------------------------------
# Location lookup (background only)
# ---------------------------------------------------------------------------


def _location_cache_key(ip):
    return f"ip_location_{ip}"


def get_ip_location(ip):
    """
    Return the cached location for the given IP address.

    This function never makes a network call. It returns None on a cache miss
    so that the caller can schedule a background lookup.
    """
    if not ip or _is_private_or_internal_ip(ip):
        return None

    try:
        cached_location = cache.get(_location_cache_key(ip))
    except Exception as e:
        logger.warning("Location cache read failed for IP %s: %s", ip, e)
        return None

    if cached_location is None:
        return None

    if cached_location.get("_cached_failure"):
        logger.debug("IP location failure cache hit for IP: %s", ip)
        return _get_default_location(ip)

    return cached_location


def fetch_ip_location(ip):
    """
    Perform the external lookups for an IP address. Blocking. Background use only.

    Tries ip-api.com first, then ipwho.is. Returns None when both fail.
    """
    location_data = _fetch_from_ip_api(ip)

    if location_data is None:
        location_data = _fetch_from_ipwhois(ip)

    return location_data


def wait_for_ip_location(ip, timeout=GEO_WAIT_MAX_SECONDS):
    """
    Block until a scheduled lookup publishes a result, or the timeout expires.

    The shared cache is polled rather than an in-process event, because the
    lookup may run on a different gunicorn worker than the one waiting.

    Returns the cached location, or None if no result arrives in time. Used only
    by endpoints that cannot produce an answer without coordinates.
    """
    if not ip or _is_private_or_internal_ip(ip):
        return None

    deadline = time.monotonic() + timeout

    while True:
        cached = get_ip_location(ip)
        if cached is not None:
            return cached

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None

        time.sleep(min(GEO_WAIT_POLL_INTERVAL, remaining))


def _run_geo_lookup(ip):
    """Background task. Writes the result, or the failure marker, to the cache."""
    location = fetch_ip_location(ip)

    if location is None:
        logger.warning("All geolocation APIs failed for IP: %s, caching failure", ip)
        try:
            cache.set(
                _location_cache_key(ip),
                {"_cached_failure": True},
                timeout=IP_LOCATION_FAILURE_CACHE_TIMEOUT,
            )
        except Exception as e:
            logger.warning("Could not cache geolocation failure for %s: %s", ip, e)
        return

    try:
        cache.set(_location_cache_key(ip), location, timeout=IP_LOCATION_CACHE_TIMEOUT)
        logger.info(
            "Location data fetched successfully for IP %s: %s, %s",
            ip,
            location.get("city", "Unknown"),
            location.get("country", "Unknown"),
        )
    except Exception as e:
        logger.warning("Could not cache geolocation result for %s: %s", ip, e)


def schedule_geo_lookup(ip):
    """
    Schedule a background geolocation lookup for an IP address. Returns at once.

    cache.add() is atomic in Redis, so a burst of requests from the same new IP
    address produces a single lookup instead of one lookup per request.
    """
    if not ip or _is_private_or_internal_ip(ip):
        return

    # Nothing to gain if both services are unavailable.
    if _circuit_is_open("ip-api") and _circuit_is_open("ipwho.is"):
        return

    pending_key = f"geo_pending_{ip}"
    try:
        if not cache.add(pending_key, 1, GEO_PENDING_TTL):
            logger.debug("Geolocation lookup already scheduled for IP: %s", ip)
            return
    except Exception as e:
        logger.warning("Could not claim geolocation slot for %s: %s", ip, e)
        return

    try:
        _geo_executor.submit(_run_geo_lookup, ip)
    except RuntimeError:
        # The pool is shutting down. Release the claim so a later request retries.
        try:
            cache.delete(pending_key)
        except Exception:
            pass


def _fetch_from_ip_api(ip):
    """Fetch location from ip-api.com (primary service)."""
    if _circuit_is_open("ip-api"):
        logger.debug("Skipping ip-api.com, circuit is open")
        return None

    try:
        session = _create_session_with_retries(retries=1, backoff_factor=0.2)
        logger.debug("Making API call to ip-api.com for IP: %s", ip)
        response = session.get(f"http://ip-api.com/json/{ip}", timeout=IP_API_TIMEOUT)
        data = response.json()

        logger.debug("IP API response status: %s for IP: %s", data.get("status"), ip)

        if data.get("status") == "success":
            _circuit_record_success("ip-api")
            return {
                "ip": ip,
                "country": data.get("country"),
                "country_code": data.get("countryCode"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lng": data.get("lon"),
                "isp": data.get("isp"),
            }

        _circuit_record_failure("ip-api")
        logger.warning("ip-api.com returned error for IP %s: %s", ip, data.get("message", "Unknown error"))
        return None
    except requests.RequestException as e:
        _circuit_record_failure("ip-api")
        logger.warning("Network error with ip-api.com for IP %s: %s", ip, e)
        return None
    except Exception as e:
        _circuit_record_failure("ip-api")
        logger.warning("Unexpected error with ip-api.com for IP %s: %s", ip, e)
        return None


def _fetch_from_ipwhois(ip):
    """Fetch location from ipwho.is (fallback service - free, HTTPS, generous limits)."""
    if _circuit_is_open("ipwho.is"):
        logger.debug("Skipping ipwho.is, circuit is open")
        return None

    try:
        session = _create_session_with_retries(retries=1, backoff_factor=0.2)
        logger.debug("Making API call to ipwho.is for IP: %s", ip)
        response = session.get(f"https://ipwho.is/{ip}", timeout=IP_API_TIMEOUT)
        data = response.json()

        if data.get("success", False):
            _circuit_record_success("ipwho.is")
            return {
                "ip": ip,
                "country": data.get("country"),
                "country_code": data.get("country_code"),
                "region": data.get("region"),
                "city": data.get("city"),
                "lat": data.get("latitude"),
                "lng": data.get("longitude"),
                "isp": data.get("connection", {}).get("isp"),
            }

        _circuit_record_failure("ipwho.is")
        logger.warning("ipwho.is returned error for IP %s: %s", ip, data.get("message", "Unknown error"))
        return None
    except requests.RequestException as e:
        _circuit_record_failure("ipwho.is")
        logger.warning("Network error with ipwho.is for IP %s: %s", ip, e)
        return None
    except Exception as e:
        _circuit_record_failure("ipwho.is")
        logger.warning("Unexpected error with ipwho.is for IP %s: %s", ip, e)
        return None


def _get_default_location(ip):
    """Return a default location object when all lookups fail."""
    return {
        "ip": ip,
        "country": None,
        "country_code": None,
        "region": None,
        "city": None,
        "lat": None,
        "lng": None,
        "isp": None,
        "lookup_failed": True,
    }


if __name__ == "__main__":
    import time as _time

    demo_ip = "175.114.21.96"

    # Cache miss: no network call, returns None, schedules a background lookup.
    print("cached lookup:", get_ip_location(demo_ip))
    schedule_geo_lookup(demo_ip)

    # The worker needs a moment to finish.
    _time.sleep(3)
    print("after background lookup:", get_ip_location(demo_ip))
