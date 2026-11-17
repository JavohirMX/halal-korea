"""Tests that IP geolocation never blocks a request.

These tests use SimpleTestCase, which forbids database access. A test in this
module therefore also proves that the geolocation path performs no queries.
"""

import time
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase
from django.utils.functional import SimpleLazyObject

from utils import location
from utils.location_manager import get_user_location

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Public addresses only. Python's ipaddress module reports the documentation
# ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) as private, so they
# would take the private-address branch and not exercise the intended path.
PUBLIC_IP = "8.8.8.8"
OTHER_PUBLIC_IP = "1.1.1.1"
KOREA_IP = "175.114.21.96"


class FakeSession(dict):
    """A session object with the small surface the location code needs."""


def make_request(path="/", user_agent=BROWSER_UA, ip=PUBLIC_IP, **params):
    request = RequestFactory().get(path, params)
    request.META["HTTP_USER_AGENT"] = user_agent
    request.META["REMOTE_ADDR"] = ip
    request.META.pop("HTTP_X_FORWARDED_FOR", None)
    request.session = FakeSession()
    return request


def api_response(status="success", **extra):
    payload = {"status": status}
    payload.update(extra)
    response = MagicMock()
    response.json.return_value = payload
    return response


class LocationTestBase(SimpleTestCase):
    """Base class that makes every test in this module hermetic.

    Background task dispatch is blocked by default. Without this, a test that
    lets schedule_geo_lookup run really would fire a live HTTP request on a
    worker thread, which outlives the patch that guards the request path.
    """

    def setUp(self):
        cache.clear()
        location._public_ip_cache["ip"] = None
        location._public_ip_cache["fetched_at"] = 0.0
        location._public_ip_pending = False

        # No background task may reach the network during a test.
        submit = patch.object(location._geo_executor, "submit")
        submit.start()
        self.addCleanup(submit.stop)

        self.addCleanup(cache.clear)

    def assert_no_network(self):
        """Fail if any code under test attempts an external HTTP call."""
        boom = AssertionError("geolocation made a blocking network call")

        def explode(*args, **kwargs):
            raise boom

        session_factory = patch.object(
            location, "_create_session_with_retries", side_effect=explode
        )
        direct_get = patch.object(location.requests, "get", side_effect=explode)
        session_factory.start()
        direct_get.start()
        self.addCleanup(session_factory.stop)
        self.addCleanup(direct_get.stop)
        return session_factory, direct_get


class RequestPathIsNeverBlocking(LocationTestBase):
    def test_get_user_location_does_not_call_the_network_on_cache_miss(self):
        self.assert_no_network()
        request = make_request()

        result = get_user_location(request)

        self.assertEqual(result["city"], "Unknown")
        self.assertTrue(result["is_fallback"])

    def test_get_client_ip_does_not_block_on_a_private_address(self):
        """A private client IP must not wait for the ipify call."""
        self.assert_no_network()
        # No X-Forwarded-For, so the private REMOTE_ADDR path is taken.
        request = make_request(ip="172.18.0.4")

        ip = location.get_client_ip(request)

        # The original value is returned so IP-bucketing callers stay correct.
        self.assertEqual(ip, "172.18.0.4")

    def test_public_ip_is_read_from_the_process_cache_without_a_call(self):
        self.assert_no_network()
        location._public_ip_cache["ip"] = KOREA_IP
        location._public_ip_cache["fetched_at"] = location.time.time()
        request = make_request(ip="172.18.0.4")

        self.assertEqual(location.get_client_ip(request), KOREA_IP)

    def test_x_forwarded_for_wins_over_the_server_address(self):
        self.assert_no_network()
        request = make_request(ip="172.18.0.4")
        request.META["HTTP_X_FORWARDED_FOR"] = f"{OTHER_PUBLIC_IP}, 172.18.0.4"

        self.assertEqual(location.get_client_ip(request), OTHER_PUBLIC_IP)


class FallbackIsNotPersisted(LocationTestBase):
    """The fallback must never be written to the session.

    If it were, the visitor would keep the fallback for a full hour even after
    the background lookup had produced the real result.
    """

    def test_session_stays_empty_after_a_cache_miss(self):
        self.assert_no_network()
        request = make_request()

        get_user_location(request)

        self.assertNotIn("user_location", request.session)

    def test_session_stays_empty_for_a_cached_failure(self):
        self.assert_no_network()
        cache.set(f"ip_location_{PUBLIC_IP}", {"_cached_failure": True}, 300)
        request = make_request()

        get_user_location(request)

        self.assertNotIn("user_location", request.session)

    def test_real_result_is_persisted_with_a_timestamp(self):
        cached = {
            "ip": PUBLIC_IP,
            "country": "United States",
            "country_code": "US",
            "city": "Ashburn",
            "lat": 39.03,
            "lng": -77.5,
        }
        cache.set(f"ip_location_{PUBLIC_IP}", cached, 3600)
        request = make_request()

        result = get_user_location(request)

        self.assertEqual(result["city"], "Ashburn")
        self.assertFalse(result["is_fallback"])
        self.assertIn("timestamp", result)
        self.assertEqual(request.session["user_location"]["city"], "Ashburn")


class BackgroundLookup(LocationTestBase):
    def test_lookup_writes_a_successful_result_to_the_cache(self):
        session = MagicMock()
        session.get.return_value = api_response(
            country="South Korea",
            countryCode="KR",
            regionName="Seoul",
            city="Seoul",
            lat=37.56,
            lon=126.97,
            isp="Example ISP",
        )
        with patch.object(
            location, "_create_session_with_retries", return_value=session
        ):
            location._run_geo_lookup(KOREA_IP)

        cached = cache.get(f"ip_location_{KOREA_IP}")
        self.assertEqual(cached["city"], "Seoul")
        self.assertEqual(cached["country_code"], "KR")

    def test_lookup_writes_a_failure_marker_when_both_services_fail(self):
        session = MagicMock()
        session.get.return_value = api_response(status="fail", message="nope")
        with patch.object(
            location, "_create_session_with_retries", return_value=session
        ):
            location._run_geo_lookup(KOREA_IP)

        cached = cache.get(f"ip_location_{KOREA_IP}")
        self.assertEqual(cached, {"_cached_failure": True})

    def test_scheduling_claims_one_slot_per_ip(self):
        """A burst from one new IP must not queue one lookup per request."""
        submitted = []
        with patch.object(
            location._geo_executor, "submit", side_effect=lambda *a: submitted.append(a)
        ):
            location.schedule_geo_lookup(OTHER_PUBLIC_IP)
            location.schedule_geo_lookup(OTHER_PUBLIC_IP)
            location.schedule_geo_lookup(OTHER_PUBLIC_IP)

        self.assertEqual(len(submitted), 1)
        self.assertEqual(submitted[0][0], location._run_geo_lookup)
        self.assertEqual(submitted[0][1], OTHER_PUBLIC_IP)

    def test_a_second_ip_gets_its_own_slot(self):
        submitted = []
        with patch.object(
            location._geo_executor, "submit", side_effect=lambda *a: submitted.append(a)
        ):
            location.schedule_geo_lookup(OTHER_PUBLIC_IP)
            location.schedule_geo_lookup(KOREA_IP)

        self.assertEqual(len(submitted), 2)

    def test_scheduling_is_skipped_for_private_addresses(self):
        with patch.object(location._geo_executor, "submit") as submit:
            location.schedule_geo_lookup("172.18.0.4")
            location.schedule_geo_lookup("")
            location.schedule_geo_lookup("127.0.0.1")

        submit.assert_not_called()

    def test_scheduling_is_skipped_when_both_circuits_are_open(self):
        cache.set("geo_circuit_open_ip-api", 1, 900)
        cache.set("geo_circuit_open_ipwho.is", 1, 900)
        with patch.object(location._geo_executor, "submit") as submit:
            location.schedule_geo_lookup(OTHER_PUBLIC_IP)

        submit.assert_not_called()


class CircuitBreaker(LocationTestBase):
    def test_circuit_opens_after_the_failure_limit(self):
        for _ in range(location.GEO_CIRCUIT_FAILURE_LIMIT):
            location._circuit_record_failure("ip-api")

        self.assertTrue(location._circuit_is_open("ip-api"))
        self.assertEqual(cache.get("geo_circuit_open_ip-api"), 1)

    def test_circuit_stays_closed_below_the_failure_limit(self):
        for _ in range(location.GEO_CIRCUIT_FAILURE_LIMIT - 1):
            location._circuit_record_failure("ip-api")

        self.assertFalse(location._circuit_is_open("ip-api"))

    def test_success_resets_the_failure_counter(self):
        location._circuit_record_failure("ip-api")
        location._circuit_record_success("ip-api")
        location._circuit_record_failure("ip-api")

        self.assertEqual(cache.get("geo_circuit_fails_ip-api"), 1)

    def test_open_circuit_skips_the_service(self):
        cache.set("geo_circuit_open_ip-api", 1, 900)
        with patch.object(location, "_create_session_with_retries") as factory:
            self.assertIsNone(location._fetch_from_ip_api("8.8.8.8"))

        factory.assert_not_called()


class RobotAndNonPageFilter(LocationTestBase):
    """These paths come from the slowest-endpoints report. Each one returned a
    404 that took 3 to 10 seconds."""

    SCANNER_PATHS = [
        "/mysql.sql",
        "/sql.gz",
        "/cron/.env.production.local",
        "/application/.env.save",
        "/sites/default/files/backup_migrate/backups/api_keys.json.gz",
        "/%2f_next%2fbuild-manifest.json",
        "/.git/config",
        "/.env",
        "/.well-known/traffic-advice",
        "/wp-config.php.bak",
        "/backup.sql",
        "/dump.tar.gz",
        "/.aws/credentials",
    ]

    def test_scanner_paths_are_treated_as_non_page(self):
        for path in self.SCANNER_PATHS:
            with self.subTest(path=path):
                self.assertTrue(location.is_bot_or_non_page_request(make_request(path)))

    def test_scanner_requests_never_schedule_a_lookup(self):
        for path in self.SCANNER_PATHS:
            with self.subTest(path=path):
                cache.clear()
                with patch.object(location._geo_executor, "submit") as submit:
                    get_user_location(make_request(path))

                submit.assert_not_called()

    SCANNER_AGENTS = [
        "Go-http-client/1.1",
        "python-urllib/3.11",
        "curl/8.4.0",
        "Wget/1.21",
        "python-requests/2.32.3",
        "masscan/1.3",
        "zgrab/0.x",
        "Nmap Scripting Engine",
        "Java/17.0.9",
        "okhttp/4.12.0",
        "PostmanRuntime/7.36.0",
        "axios/1.6.2",
        "libwww-perl/6.72",
        "Mozilla/5.0 (compatible; SemrushBot/7~bl)",
        "",
        "   ",
    ]

    def test_scanner_user_agents_are_treated_as_non_page(self):
        for agent in self.SCANNER_AGENTS:
            with self.subTest(user_agent=agent):
                request = make_request("/", user_agent=agent)
                self.assertTrue(location.is_bot_or_non_page_request(request))

    def test_real_browsers_are_not_filtered(self):
        agents = [
            BROWSER_UA,
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 Version/17.0 Mobile Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]
        for agent in agents:
            with self.subTest(user_agent=agent):
                request = make_request("/", user_agent=agent)
                self.assertFalse(location.is_bot_or_non_page_request(request))

    def test_normal_pages_are_not_filtered(self):
        for path in ["/", "/explore/", "/place/660/", "/blog/", "/admin/places/"]:
            with self.subTest(path=path):
                self.assertFalse(location.is_bot_or_non_page_request(make_request(path)))


class TimeoutsAreShort(LocationTestBase):
    """The old values produced the 26078 ms maximum.

    Old worst case: ipify 5 s + ip-api 5 s x2 + ipwho.is 5 s x2 = 25.4 s.
    """

    def test_timeouts_match_the_agreed_values(self):
        self.assertEqual(location.PUBLIC_IP_TIMEOUT, 1.0)
        self.assertEqual(location.IP_API_TIMEOUT, 1.5)

    def test_worst_case_is_far_below_the_old_maximum(self):
        worst_case = (
            location.PUBLIC_IP_TIMEOUT
            + (location.IP_API_TIMEOUT * 2 + 0.2)
            + (location.IP_API_TIMEOUT * 2 + 0.2)
        )
        self.assertLess(worst_case, 8.0)


class OptInWait(LocationTestBase):
    """wait_for_lookup=True is used only where coordinates are required.

    Without it, the prayer times endpoint would answer 400 to any visitor who
    declines the browser location prompt, because a cold cache yields the
    fallback instead of a blocking lookup.
    """

    REAL = {
        "ip": PUBLIC_IP,
        "city": "Ashburn",
        "country": "United States",
        "country_code": "US",
        "lat": 39.03,
        "lng": -77.5,
    }

    def test_wait_resolves_the_location_when_the_task_publishes_in_time(self):
        request = make_request()

        with patch("utils.location_manager.schedule_geo_lookup"), patch(
            "utils.location_manager.wait_for_ip_location", return_value=dict(self.REAL)
        ):
            result = get_user_location(request, wait_for_lookup=True)

        self.assertEqual(result["city"], "Ashburn")
        self.assertFalse(result["is_fallback"])
        self.assertEqual(request.session["user_location"]["city"], "Ashburn")

    def test_wait_gives_up_and_returns_the_fallback(self):
        request = make_request()

        with patch("utils.location_manager.schedule_geo_lookup"), patch(
            "utils.location_manager.wait_for_ip_location", return_value=None
        ):
            result = get_user_location(request, wait_for_lookup=True)

        self.assertTrue(result["is_fallback"])
        self.assertNotIn("user_location", request.session)

    def test_a_failure_marker_does_not_satisfy_the_wait(self):
        request = make_request()

        with patch("utils.location_manager.schedule_geo_lookup"), patch(
            "utils.location_manager.wait_for_ip_location",
            return_value=location._get_default_location(PUBLIC_IP),
        ):
            result = get_user_location(request, wait_for_lookup=True)

        self.assertTrue(result["is_fallback"])
        self.assertNotIn("user_location", request.session)

    def test_the_task_is_still_scheduled_before_waiting(self):
        """The wait must not be the only thing that triggers the lookup."""
        request = make_request()

        with patch("utils.location_manager.schedule_geo_lookup") as schedule, patch(
            "utils.location_manager.wait_for_ip_location", return_value=None
        ):
            get_user_location(request, wait_for_lookup=True)

        schedule.assert_called_once_with(PUBLIC_IP)

    def test_the_default_path_never_waits(self):
        """Page views must not pay the wait cost."""
        request = make_request()

        with patch("utils.location_manager.schedule_geo_lookup"), patch(
            "utils.location_manager.wait_for_ip_location"
        ) as wait_fn:
            get_user_location(request)

        wait_fn.assert_not_called()

    def test_context_passes_the_flag_through(self):
        from utils import location_manager

        request = make_request()

        with patch.object(location_manager, "get_user_location") as resolve:
            location_manager.get_user_location_context(request, wait_for_lookup=True)

        resolve.assert_called_once_with(request, wait_for_lookup=True)


class WaitPollsTheSharedCache(LocationTestBase):
    """wait_for_ip_location polls the shared cache, not an in-process event.

    The lookup may run on a different gunicorn worker than the one waiting.
    """

    def test_it_returns_once_the_task_publishes(self):
        import threading
        import time as time_module

        result_payload = {
            "ip": PUBLIC_IP, "city": "Seoul", "country": "South Korea",
            "country_code": "KR", "lat": 37.56, "lng": 126.97,
        }

        def publisher():
            time_module.sleep(0.05)
            cache.set(f"ip_location_{PUBLIC_IP}", result_payload, 3600)

        threading.Thread(target=publisher, daemon=True).start()

        found = location.wait_for_ip_location(PUBLIC_IP, timeout=2.0)

        self.assertIsNotNone(found)
        self.assertEqual(found["city"], "Seoul")

    def test_it_returns_none_after_the_timeout(self):
        start = time.perf_counter()
        found = location.wait_for_ip_location(PUBLIC_IP, timeout=0.2)
        elapsed = time.perf_counter() - start

        self.assertIsNone(found)
        self.assertLess(elapsed, 1.5)
        self.assertGreaterEqual(elapsed, 0.15)

    def test_the_default_timeout_is_bounded(self):
        self.assertLessEqual(location.GEO_WAIT_MAX_SECONDS, 2.0)
        self.assertEqual(
            location.wait_for_ip_location.__defaults__[0], location.GEO_WAIT_MAX_SECONDS
        )

    def test_it_returns_immediately_for_a_private_address(self):
        self.assertIsNone(location.wait_for_ip_location("172.18.0.4", timeout=2.0))
        self.assertIsNone(location.wait_for_ip_location("", timeout=2.0))


class ContextProcessorIsLazy(SimpleTestCase):
    """The 404 page and other location-free templates must cost nothing.

    Wrapping the value in a SimpleLazyObject means the lookup only runs if a
    template actually reads it.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_user_location_is_wrapped_in_a_lazy_object(self):
        from utils.context_processors import user_location as processor

        request = make_request()

        context = processor(request)

        self.assertIsInstance(context["user_location"], SimpleLazyObject)

    def test_the_lookup_does_not_run_until_a_template_reads_the_value(self):
        from utils.context_processors import user_location as processor

        request = make_request()

        with patch(
            "utils.context_processors.get_user_location",
            return_value={"city": "Seoul", "country": "South Korea"},
        ) as lookup:
            lazy = processor(request)["user_location"]

            # Building the context must not run the lookup.
            lookup.assert_not_called()

            # Reading a key, as a template does, forces it.
            self.assertEqual(lazy["city"], "Seoul")
            lookup.assert_called_once()

            # The value is memoised, so a second read does not call again.
            self.assertEqual(lazy["country"], "South Korea")
            lookup.assert_called_once()

    def test_a_truthiness_check_also_forces_evaluation(self):
        from utils.context_processors import user_location as processor

        request = make_request()

        with patch(
            "utils.context_processors.get_user_location",
            return_value={"city": "Seoul"},
        ) as lookup:
            lazy = processor(request)["user_location"]
            lookup.assert_not_called()

            # {% if user_location %} in a template.
            self.assertTrue(bool(lazy))
            lookup.assert_called_once()

    def test_a_missing_key_raises_keyerror_for_the_template_engine(self):
        from utils.context_processors import user_location as processor

        request = make_request()

        with patch(
            "utils.context_processors.get_user_location",
            return_value={"city": "Seoul"},
        ):
            lazy = processor(request)["user_location"]

            # Django catches this and falls back to string_if_invalid.
            with self.assertRaises(KeyError):
                lazy["country_code"]


class TemplatesWithoutLocation(LocationTestBase):
    """A guard against a future template starting to read the location.

    If the 404 page ever reads user_location, the lazy object evaluates and the
    lookup runs again. This test makes that change visible.
    """

    def test_the_404_template_does_not_read_the_location(self):
        from pathlib import Path

        template = (
            Path(__file__).resolve().parent.parent.parent
            / "places"
            / "templates"
            / "places"
            / "404.html"
        ).read_text(encoding="utf-8")

        for needle in ("user_location", "location_context", "is_in_korea"):
            with self.subTest(needle=needle):
                self.assertNotIn(needle, template)

    def test_the_base_template_does_not_read_the_location(self):
        from pathlib import Path

        template = (
            Path(__file__).resolve().parent.parent.parent
            / "places"
            / "templates"
            / "places"
            / "base.html"
        ).read_text(encoding="utf-8")

        for needle in ("user_location", "location_context", "is_in_korea"):
            with self.subTest(needle=needle):
                self.assertNotIn(needle, template)
