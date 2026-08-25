import threading
import time

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
IP_API_TIMEOUT = 5  # Reduced timeout for faster failover

# Process-level cache for the server's own public IP (behind proxy/private networks)
PUBLIC_IP_CACHE_TIMEOUT = 21600  # 6 hours for successful lookups
PUBLIC_IP_FAILURE_CACHE_TIMEOUT = 600  # 10 minutes for failed lookups
_public_ip_cache = {"ip": None, "fetched_at": 0.0}
_public_ip_lock = threading.Lock()

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
)
BOT_USER_AGENT_TOKENS = (
    "bot",
    "crawl",
    "spider",
    "slurp",
    "curl",
    "wget",
    "python-requests",
    "jscrawler",
    "headless",
)


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


def _create_session_with_retries(retries=2, backoff_factor=0.3):
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


def is_bot_or_non_page_request(request):
    """
    Check if a request comes from a bot/crawler or targets a non-page path
    (robots.txt, sitemaps, favicons, scanner probes). Such requests should
    skip IP geolocation entirely to avoid blocking external HTTP calls.
    """
    path = request.path.lower()

    if path in NON_PAGE_PATHS or path.startswith("/.well-known"):
        return True

    if path.endswith(NON_PAGE_PATH_SUFFIXES):
        return True

    user_agent = (request.META.get("HTTP_USER_AGENT") or "").lower()
    return any(token in user_agent for token in BOT_USER_AGENT_TOKENS)


def _get_public_ip():
    """
    Fetch the server's public IP from ipify with process-level caching.
    Successful lookups are cached for 6 hours and failures for 10 minutes,
    so the external service is contacted at most once per TTL per process.
    """
    now = time.time()
    with _public_ip_lock:
        cached_ip = _public_ip_cache["ip"]
        if cached_ip:
            ttl = (
                PUBLIC_IP_FAILURE_CACHE_TIMEOUT
                if cached_ip == "UNKNOWN"
                else PUBLIC_IP_CACHE_TIMEOUT
            )
            if now - _public_ip_cache["fetched_at"] < ttl:
                logger.debug(f"Using cached public IP: {cached_ip}")
                return cached_ip

        try:
            response = requests.get("https://api64.ipify.org?format=json", timeout=5)
            public_ip = response.json().get("ip")
            if public_ip:
                logger.info(f"Public IP fetched for geolocation: {public_ip}")
            else:
                logger.warning("Failed to get public IP from ipify service")
                public_ip = "UNKNOWN"
        except requests.RequestException as e:
            logger.error(f"Failed to fetch public IP: {str(e)}")
            public_ip = "UNKNOWN"
        except Exception as e:
            logger.error(f"Unexpected error fetching public IP: {str(e)}")
            public_ip = "UNKNOWN"

        _public_ip_cache["ip"] = public_ip
        _public_ip_cache["fetched_at"] = now
        return public_ip


def get_client_ip(request):
    """Extracts the client's IP address from the request."""
    logger.debug("Extracting client IP address from request")

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # Take the first IP if there are multiple (proxy chain)
        ip = x_forwarded_for.split(",")[0].strip()
        logger.debug(f"Client IP extracted from X-Forwarded-For header: {ip}")
    else:
        ip = request.META.get("REMOTE_ADDR")
        logger.debug(f"Client IP extracted from REMOTE_ADDR: {ip}")

    # If running locally, in Docker, or behind private network, get public IP for geolocation
    if _is_private_or_internal_ip(ip):
        logger.debug(
            f"Private/internal IP detected ({ip}), fetching public IP for geolocation"
        )
        ip = _get_public_ip()

    logger.debug(f"Final client IP determined: {ip}")
    return ip


def get_ip_location(ip):
    """
    Fetches location details for the given IP address using external APIs, with caching.

    Features:
    - Caches successful lookups for 1 hour
    - Caches failures for 5 minutes to prevent hammering failing services
    - Retries with exponential backoff on transient failures
    - Falls back to alternative API if primary fails
    - Returns graceful default on complete failure
    """

    # Check if IP location is already cached (success or failure)
    cache_key = f"ip_location_{ip}"
    cached_location = cache.get(cache_key)
    if cached_location is not None:
        if cached_location.get("_cached_failure"):
            logger.debug(f"IP location failure cache hit for IP: {ip}, skipping lookup")
            return _get_default_location(ip)
        logger.debug(
            f"IP location cache hit for IP: {ip} -> {cached_location.get('city', 'Unknown')}, {cached_location.get('country', 'Unknown')}"
        )
        return cached_location

    logger.info(f"Fetching location for IP: {ip} (cache miss)")

    # Try primary API (ip-api.com)
    location_data = _fetch_from_ip_api(ip)

    # If primary fails, try fallback API (ipwho.is - free, HTTPS, no rate limit issues)
    if location_data is None:
        logger.info(f"Primary API failed for IP {ip}, trying fallback API")
        location_data = _fetch_from_ipwhois(ip)

    # If all APIs fail, cache the failure and return default
    if location_data is None:
        logger.warning(f"All geolocation APIs failed for IP: {ip}, caching failure")
        cache.set(
            cache_key,
            {"_cached_failure": True},
            timeout=IP_LOCATION_FAILURE_CACHE_TIMEOUT,
        )
        return _get_default_location(ip)

    # Cache successful result
    cache.set(cache_key, location_data, timeout=IP_LOCATION_CACHE_TIMEOUT)
    logger.info(
        f"Location data fetched successfully for IP {ip}: {location_data.get('city', 'Unknown')}, {location_data.get('country', 'Unknown')}"
    )

    return location_data


def _fetch_from_ip_api(ip):
    """Fetch location from ip-api.com (primary service)."""
    try:
        session = _create_session_with_retries(retries=1, backoff_factor=0.2)
        logger.debug(f"Making API call to ip-api.com for IP: {ip}")
        response = session.get(f"http://ip-api.com/json/{ip}", timeout=IP_API_TIMEOUT)
        data = response.json()

        logger.debug(f"IP API response status: {data.get('status')} for IP: {ip}")

        if data.get("status") == "success":
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
        else:
            error_msg = data.get("message", "Unknown error")
            logger.warning(f"ip-api.com returned error for IP {ip}: {error_msg}")
            return None
    except requests.RequestException as e:
        logger.warning(f"Network error with ip-api.com for IP {ip}: {str(e)}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error with ip-api.com for IP {ip}: {str(e)}")
        return None


def _fetch_from_ipwhois(ip):
    """Fetch location from ipwho.is (fallback service - free, HTTPS, generous limits)."""
    try:
        session = _create_session_with_retries(retries=1, backoff_factor=0.2)
        logger.debug(f"Making API call to ipwho.is for IP: {ip}")
        response = session.get(f"https://ipwho.is/{ip}", timeout=IP_API_TIMEOUT)
        data = response.json()

        if data.get("success", False):
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
        else:
            error_msg = data.get("message", "Unknown error")
            logger.warning(f"ipwho.is returned error for IP {ip}: {error_msg}")
            return None
    except requests.RequestException as e:
        logger.warning(f"Network error with ipwho.is for IP {ip}: {str(e)}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error with ipwho.is for IP {ip}: {str(e)}")
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
    ip = "175.114.21.96"
    location = get_ip_location(ip)

    print(location)
