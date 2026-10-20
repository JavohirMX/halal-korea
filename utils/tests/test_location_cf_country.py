"""
Tests for the Cloudflare CF-IPCountry short-circuit in get_user_location.

For non-Korean visitors the exact IP geolocation (city/lat/lng) is never
used, so when Cloudflare already provides the visitor country we must not
make a blocking external geolocation HTTP call.
"""
import time
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from utils.location_manager import get_user_location, is_user_in_korea


class _DictSession(dict):
    """Minimal stand-in for request.session (no DB/cache needed)."""

    modified = False


def _request(meta=None, session=None):
    request = RequestFactory().get("/")
    request.META.update(meta or {})
    request.session = session if session is not None else _DictSession()
    return request


class CloudflareCountryShortCircuitTests(SimpleTestCase):
    @patch("utils.location_manager.get_ip_location")
    @patch("utils.location_manager.get_client_ip")
    def test_non_korean_cf_country_skips_external_lookup(
        self, mock_client_ip, mock_ip_location
    ):
        request = _request(meta={"HTTP_CF_IPCOUNTRY": "us"})

        location = get_user_location(request)

        mock_client_ip.assert_not_called()
        mock_ip_location.assert_not_called()
        self.assertEqual(location["country_code"], "US")
        self.assertFalse(location["is_fallback"])
        self.assertFalse(is_user_in_korea(location))
        # Header-derived locations must not create a session row
        self.assertNotIn("user_location", request.session)

    @patch("utils.location_manager.get_ip_location")
    @patch("utils.location_manager.get_client_ip", return_value="1.2.3.4")
    def test_korean_cf_country_still_uses_full_lookup(
        self, mock_client_ip, mock_ip_location
    ):
        mock_ip_location.return_value = {
            "country_code": "KR",
            "city": "Seoul",
            "lat": 37.56,
            "lng": 126.97,
        }
        request = _request(meta={"HTTP_CF_IPCOUNTRY": "KR"})

        location = get_user_location(request)

        mock_ip_location.assert_called_once_with("1.2.3.4")
        self.assertEqual(location["city"], "Seoul")
        self.assertTrue(is_user_in_korea(location))

    @patch("utils.location_manager.get_ip_location")
    @patch("utils.location_manager.get_client_ip", return_value="1.2.3.4")
    def test_unknown_cf_country_falls_through_to_lookup(
        self, mock_client_ip, mock_ip_location
    ):
        mock_ip_location.return_value = {
            "country_code": "US",
            "city": "Ashburn",
        }
        for header_value in ("XX", "T1", ""):
            request = _request(meta={"HTTP_CF_IPCOUNTRY": header_value})
            get_user_location(request)

        self.assertEqual(mock_ip_location.call_count, 3)

    @patch("utils.location_manager.get_ip_location")
    @patch("utils.location_manager.get_client_ip")
    def test_fresh_session_location_still_wins(self, mock_client_ip, mock_ip_location):
        cached = {"city": "Busan", "country_code": "KR", "timestamp": time.time()}
        request = _request(
            meta={"HTTP_CF_IPCOUNTRY": "US"}, session=_DictSession(user_location=cached)
        )

        location = get_user_location(request)

        self.assertIs(location, cached)
        mock_client_ip.assert_not_called()
        mock_ip_location.assert_not_called()


class SessionWritePolicyTests(SimpleTestCase):
    @patch("utils.location_manager.get_ip_location")
    @patch("utils.location_manager.get_client_ip", return_value="1.2.3.4")
    def test_successful_lookup_is_saved_to_session(
        self, mock_client_ip, mock_ip_location
    ):
        mock_ip_location.return_value = {
            "country_code": "KR",
            "city": "Seoul",
            "lat": 37.56,
            "lng": 126.97,
        }
        request = _request()

        get_user_location(request)

        self.assertIn("user_location", request.session)

    @patch("utils.location_manager.get_ip_location", return_value=None)
    @patch("utils.location_manager.get_client_ip", return_value="1.2.3.4")
    def test_failed_lookup_is_not_saved_to_session(
        self, mock_client_ip, mock_ip_location
    ):
        request = _request()

        location = get_user_location(request)

        self.assertTrue(location["is_fallback"])
        self.assertNotIn("user_location", request.session)
