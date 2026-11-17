"""Behaviour parity checks for the geolocation change.

Each test states the previous behaviour, so a regression is visible as a
failure rather than as a subtle difference nobody notices.
"""

import time
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase

from utils import location, location_manager

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PUBLIC_IP = "8.8.8.8"
KOREA = {
    "ip": PUBLIC_IP, "country": "South Korea", "country_code": "KR",
    "region": "Seoul", "city": "Seoul", "lat": 37.5665, "lng": 126.978,
}
SEOUL = {
    "ip": PUBLIC_IP, "country": "United States", "country_code": "US",
    "region": "Virginia", "city": "Ashburn", "lat": 39.03, "lng": -77.5,
}


class FakeSession(dict):
    pass


def make_request(path="/", user_agent=BROWSER_UA, ip=PUBLIC_IP, **params):
    request = RequestFactory().get(path, params)
    request.META["HTTP_USER_AGENT"] = user_agent
    request.META["REMOTE_ADDR"] = ip
    request.session = FakeSession()
    return request


class ParityBase(SimpleTestCase):
    def setUp(self):
        cache.clear()
        location._public_ip_cache["ip"] = None
        location._public_ip_cache["fetched_at"] = 0.0
        location._public_ip_pending = False
        submit = patch.object(location._geo_executor, "submit")
        submit.start()
        self.addCleanup(submit.stop)
        self.addCleanup(cache.clear)


class ReturnShapeIsUnchanged(ParityBase):
    """Every consumer reads these keys. They must all still be present."""

    def test_cold_cache_returns_the_same_keys_as_before(self):
        result = location_manager.get_user_location(make_request())

        self.assertEqual(
            sorted(result.keys()),
            ["city", "country", "is_fallback"],
        )

    def test_warm_cache_returns_the_same_keys_as_a_real_lookup_did(self):
        # The stored shape is exactly what _fetch_from_ip_api produces.
        cache.set(f"ip_location_{PUBLIC_IP}", dict(KOREA), 3600)
        result = location_manager.get_user_location(make_request())

        self.assertEqual(
            sorted(result.keys()),
            [
                "city", "country", "country_code", "ip", "is_fallback",
                "lat", "lng", "region", "timestamp",
            ],
        )
        self.assertEqual(result["region"], "Seoul")
        self.assertEqual(result["country_code"], "KR")

    def test_context_returns_the_same_three_keys(self):
        cache.set(f"ip_location_{PUBLIC_IP}", dict(KOREA), 3600)
        context = location_manager.get_user_location_context(make_request())

        self.assertEqual(sorted(context.keys()), ["is_in_korea", "location", "user_type"])

    def test_a_korean_ip_is_still_detected_as_local(self):
        cache.set(f"ip_location_{PUBLIC_IP}", dict(KOREA), 3600)
        context = location_manager.get_user_location_context(make_request())

        self.assertTrue(context["is_in_korea"])
        self.assertEqual(context["user_type"], "local")

    def test_a_foreign_ip_is_still_detected_as_international(self):
        cache.set(f"ip_location_{PUBLIC_IP}", dict(SEOUL), 3600)
        context = location_manager.get_user_location_context(make_request())

        self.assertFalse(context["is_in_korea"])
        self.assertEqual(context["user_type"], "international")


class SessionContract(ParityBase):
    """Before the change, a successful lookup wrote to this session key."""

    def test_the_session_key_is_unchanged(self):
        cache.set(f"ip_location_{PUBLIC_IP}", dict(KOREA), 3600)
        request = make_request()

        location_manager.get_user_location(request)

        self.assertIn("user_location", request.session)
        self.assertEqual(request.session["user_location"]["city"], "Seoul")

    def test_a_session_value_is_still_reused(self):
        request = make_request()
        request.session["user_location"] = dict(KOREA, timestamp=time.time())

        result = location_manager.get_user_location(request)

        self.assertEqual(result["city"], "Seoul")

    def test_an_expired_session_value_is_ignored(self):
        request = make_request()
        stale = dict(KOREA, timestamp=time.time() - 7200)
        request.session["user_location"] = stale

        with patch("utils.location_manager.schedule_geo_lookup") as schedule:
            result = location_manager.get_user_location(request)

        self.assertTrue(result["is_fallback"])
        schedule.assert_called_once()

    def test_a_session_value_without_a_timestamp_no_longer_raises(self):
        """The old code did session_loc["timestamp"] and could raise KeyError."""
        request = make_request()
        request.session["user_location"] = dict(KOREA)

        result = location_manager.get_user_location(request)

        self.assertTrue(result["is_fallback"])


class DevOverridesStillWork(ParityBase):
    """force_korea and force_international are documented test hooks."""

    def test_force_korea(self):
        result = location_manager.get_user_location(
            make_request("/explore/", force_korea="1")
        )

        self.assertEqual(result["city"], "Mapo-gu")
        self.assertFalse(result["is_fallback"])

    def test_force_international(self):
        result = location_manager.get_user_location(
            make_request("/explore/", force_international="1")
        )

        self.assertEqual(result["country_code"], "US")
        self.assertFalse(result["is_fallback"])

    def test_force_korea_overrides_a_cached_value(self):
        cache.set(f"ip_location_{PUBLIC_IP}", dict(SEOUL), 3600)

        result = location_manager.get_user_location(
            make_request("/explore/", force_korea="1")
        )

        self.assertEqual(result["city"], "Mapo-gu")


class UpdateLocationIsUntouched(ParityBase):
    """update_user_location is the browser-driven path. It must still work
    synchronously, because the response echoes the resolved city back."""

    def test_a_city_is_stored_in_the_session(self):
        request = make_request()

        result = location_manager.update_user_location(
            request, {"city": "Seoul", "country": "South Korea"}
        )

        self.assertEqual(result["city"], "Seoul")
        self.assertEqual(request.session["user_location"]["city"], "Seoul")

    def test_coordinates_in_korea_are_stored(self):
        request = make_request()

        with patch.object(location_manager, "get_korea_location_from_coordinates",
                          return_value=None):
            result = location_manager.update_user_location(
                request, {"lat": 37.5665, "lng": 126.978}
            )

        self.assertEqual(result["country"], "South Korea")
        self.assertEqual(result["lat"], 37.5665)

    def test_a_known_korean_city_name_implies_the_country(self):
        request = make_request()

        result = location_manager.update_user_location(request, {"city": "Busan"})

        self.assertEqual(result["country"], "South Korea")

    def test_bots_are_still_skipped(self):
        request = make_request(user_agent="Go-http-client/1.1")

        result = location_manager.update_user_location(request, {"city": "Seoul"})

        self.assertEqual(result, {"is_fallback": True})

    def test_clear_user_location_still_removes_the_key(self):
        request = make_request()
        request.session["user_location"] = dict(KOREA, timestamp=time.time())

        location_manager.clear_user_location(request)

        self.assertNotIn("user_location", request.session)


class ProbeEndpointsStillWork(ParityBase):
    """Views pass these to the template as location_context and user_location."""

    def test_a_point_can_still_be_built_from_the_location(self):
        from django.contrib.gis.geos import Point

        cache.set(f"ip_location_{PUBLIC_IP}", dict(KOREA), 3600)
        request = make_request()
        context = location_manager.get_user_location_context(request)
        loc = context["location"]

        point = Point(loc["lng"], loc["lat"], srid=4326)

        self.assertAlmostEqual(point.y, 37.5665)
        self.assertEqual(point.srid, 4326)

    def test_the_fallback_yields_no_point(self):
        """places.views guards on is_fallback before building a Point, and
        nothing in the codebase indexes lat/lng on the fallback dict."""
        request = make_request()
        loc = location_manager.get_user_location(request)

        self.assertTrue(loc["is_fallback"])
        self.assertNotIn("lat", loc)
        self.assertNotIn("lng", loc)

    def test_get_ip_location_returns_none_where_a_fetch_used_to_return_a_dict(self):
        """Callers must handle None. The only caller does."""
        self.assertIsNone(location.get_ip_location(PUBLIC_IP))

    def test_a_private_address_yields_no_lookup_key(self):
        self.assertIsNone(location.get_ip_location("172.18.0.4"))
        self.assertIsNone(location.get_ip_location(""))


class TwoRequestJourney(ParityBase):
    """The documented trade: request one is the fallback, request two is real."""

    def test_first_request_fallback_then_second_request_real(self):
        first = make_request()

        result_one = location_manager.get_user_location(first)
        self.assertTrue(result_one["is_fallback"])

        # The background task has now published the result.
        cache.set(f"ip_location_{PUBLIC_IP}", dict(KOREA), 3600)

        second = make_request()
        result_two = location_manager.get_user_location(second)

        self.assertEqual(result_two["city"], "Seoul")
        self.assertFalse(result_two["is_fallback"])
        self.assertTrue(
            location_manager.is_user_in_korea(result_two),
            "the second request must classify the visitor as local",
        )

    def test_the_second_request_does_not_need_the_network(self):
        cache.set(f"ip_location_{PUBLIC_IP}", dict(KOREA), 3600)
        request = make_request()

        with patch.object(location, "_create_session_with_retries",
                          side_effect=AssertionError("network")), \
             patch.object(location.requests, "get",
                          side_effect=AssertionError("network")):
            result = location_manager.get_user_location(request)

        self.assertEqual(result["city"], "Seoul")
