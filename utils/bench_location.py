"""Before/after benchmark for the IP geolocation request path.

Simulates a black-holed network: every external call waits for its full
time-out and then fails. This is the condition the 26 second maximum came from.

The "old" column reproduces the previous implementation, including its original
narrow path filter, so the comparison is fair.

Usage:  python utils/bench_location.py
"""

import os
import sys
import time
from unittest.mock import patch

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.cache import cache  # noqa: E402
from django.test import RequestFactory, override_settings  # noqa: E402

from utils import location  # noqa: E402
from utils.location_manager import get_user_location  # noqa: E402

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Paths taken from the slowest-endpoints report.
SCANNER_PATHS = [
    "/mysql.sql",
    "/sql.gz",
    "/cron/.env.production.local",
    "/application/.env.save",
    "/sites/default/files/backup_migrate/backups/api_keys.json.gz",
    "/%2f_next%2fbuild-manifest.json",
]

# The filter as it was before this change.
OLD_NON_PAGE_PATHS = ("/robots.txt", "/sitemap.xml", "/favicon.ico")
OLD_NON_PAGE_PATH_SUFFIXES = (".php", ".env", ".git", ".yaml", ".yml", ".json")
OLD_BOT_USER_AGENT_TOKENS = (
    "bot", "crawl", "spider", "slurp", "curl", "wget", "python-requests", "headless",
)

OLD_IPIFY_TIMEOUT = 5.0
OLD_API_TIMEOUT = 5.0


class FakeSession(dict):
    """A session object with the small surface the location code needs."""


def make_request(path="/", user_agent=BROWSER_UA, ip="1.1.1.1"):
    request = RequestFactory().get(path)
    request.META["HTTP_USER_AGENT"] = user_agent
    request.META["REMOTE_ADDR"] = ip
    request.session = FakeSession()
    return request


def old_is_bot_or_non_page_request(request):
    """The previous filter. No dot-segment rule, no empty-UA rule, short lists."""
    path = request.path.lower()
    if path in OLD_NON_PAGE_PATHS or path.startswith("/.well-known"):
        return True
    if path.endswith(OLD_NON_PAGE_PATH_SUFFIXES):
        return True
    user_agent = (request.META.get("HTTP_USER_AGENT") or "").lower()
    return any(token in user_agent for token in OLD_BOT_USER_AGENT_TOKENS)


def old_get_user_location(request):
    """The previous implementation: three blocking calls, run inline."""
    if old_is_bot_or_non_page_request(request):
        return {"city": "Unknown", "country": "Unknown", "is_fallback": True}

    session_loc = request.session.get("user_location")
    if session_loc and time.time() - session_loc["timestamp"] < 3600:
        return session_loc

    # _get_public_ip(): one 5 second call, returns UNKNOWN after it fails
    time.sleep(OLD_IPIFY_TIMEOUT)

    # _fetch_from_ip_api(): 5 seconds, one retry
    for _ in range(2):
        time.sleep(OLD_API_TIMEOUT)
    # _fetch_from_ipwhois(): 5 seconds, one retry
    for _ in range(2):
        time.sleep(OLD_API_TIMEOUT)

    fallback = {"city": "Unknown", "country": "Unknown", "is_fallback": True}
    request.session["user_location"] = dict(fallback, timestamp=time.time())
    return fallback


def no_network():
    """Any external call from the request path is a bug."""
    return patch.multiple(
        location,
        _create_session_with_retries=patch.DEFAULT,
        requests=patch.DEFAULT,
    )


def time_it(label, func, *args):
    start = time.perf_counter()
    func(*args)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"  {label:<56} {elapsed_ms:>10.1f} ms")
    return elapsed_ms


def banner(text):
    print()
    print(text)
    print("-" * 70)


def render_404(path):
    from places.views import handler404

    request = make_request(path)
    response = handler404(request, None)
    assert response.status_code == 404, response.status_code


def main():
    print("Simulated network: every external call waits for its full time-out.")
    print("This is the condition behind the 26078 ms maximum.")
    print("Paths are taken from the slowest-endpoints report.")
    print()
    print("Two independent changes are measured separately:")
    print("  a) the location value became lazy, so unused templates never resolve it")
    print("  b) the resolver no longer makes external calls during a request")

    with override_settings(ALLOWED_HOSTS=["testserver", "localhost", "*"]):
        banner("1. Cost of the previous resolver, called once")
        old_resolver = time_it(
            "old: resolve location during render",
            old_get_user_location,
            make_request("/mysql.sql"),
        )
        print(f"  {'breakdown: 5 s ipify + 5 s x2 ip-api + 5 s x2 ipwho.is':<56}")

        banner("2. Cost of the new resolver, called once")
        location._public_ip_cache["ip"] = None
        with patch.object(location, "_create_session_with_retries",
                          side_effect=AssertionError("network")), \
             patch.object(location.requests, "get",
                          side_effect=AssertionError("network")):
            new_resolver = time_it(
                "new: resolve location, cache read only",
                get_user_location,
                make_request("/mysql.sql"),
            )

        banner("3. Full 404 handler, template render included")
        print("  (a) before: eager context processor + old resolver")
        print(f"      {old_resolver:>10.1f} ms  resolver + ~1 ms template render")
        print(f"      {old_resolver + 1:>10.1f} ms  total")

        print("  (b) lazy wrapper + old resolver")
        lazy_old = None
        for path in SCANNER_PATHS[:3]:
            with patch("utils.context_processors.get_user_location",
                       old_get_user_location), \
                 patch.object(location.requests, "get",
                              side_effect=AssertionError("network")):
                elapsed = time_it(f"      handler404 {path[:30]}", render_404, path)
            lazy_old = elapsed if lazy_old is None else max(lazy_old, elapsed)

        print("  (c) lazy wrapper + new resolver")
        new_404 = []
        for path in SCANNER_PATHS:
            with patch.object(location, "_create_session_with_retries",
                              side_effect=AssertionError("network")), \
                 patch.object(location.requests, "get",
                              side_effect=AssertionError("network")), \
                 patch.object(location._geo_executor, "submit"):
                new_404.append(time_it(f"      handler404 {path[:30]}",
                                       render_404, path))

        banner("4. A real page: /explore/ reads the location, so it does resolve")
        print("  (a) before: eager context processor + old resolver")
        print(f"      {old_resolver:>10.1f} ms  resolver + ~1 ms template render")
        print(f"      {old_resolver + 1:>10.1f} ms  total")

        print("  (b) after: cache read only, task runs in the background")
        cache.clear()
        with patch.object(location, "_create_session_with_retries",
                          side_effect=AssertionError("network")), \
             patch.object(location.requests, "get",
                          side_effect=AssertionError("network")):
            cold = time_it("      get_user_location, cold cache",
                           get_user_location, make_request("/explore/"))

        cache.set(
            "ip_location_1.1.1.1",
            {"ip": "1.1.1.1", "city": "Seoul", "country": "South Korea",
             "country_code": "KR", "lat": 37.56, "lng": 126.97},
            3600,
        )
        request = make_request("/explore/")
        request.session = FakeSession()
        with patch.object(location, "_create_session_with_retries",
                          side_effect=AssertionError("network")), \
             patch.object(location.requests, "get",
                          side_effect=AssertionError("network")):
            warm = time_it("      get_user_location, warm cache",
                           get_user_location, request)

        print()
        print("  Summary")
        print(f"    {'404 handler, before':<38}{old_resolver + 1:>10.1f} ms")
        print(f"    {'404 handler, after':<38}{max(new_404):>10.1f} ms")
        print(f"    {'page location, before':<38}{old_resolver:>10.1f} ms")
        print(f"    {'page location, after (cold cache)':<38}{cold:>10.1f} ms")
        print(f"    {'page location, after (warm cache)':<38}{warm:>10.1f} ms")
        print()


if __name__ == "__main__":
    main()
