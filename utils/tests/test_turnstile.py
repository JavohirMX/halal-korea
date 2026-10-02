"""
Unit tests for Cloudflare Turnstile helpers (mocked siteverify).
"""

from unittest.mock import MagicMock, patch

import requests
from django import forms
from django.test import RequestFactory, SimpleTestCase, override_settings

from utils.turnstile import (
    TurnstileField,
    get_client_ip,
    require_turnstile,
    verify_turnstile,
)

DUMMY_SITEKEY = "1x00000000000000000000AA"
DUMMY_SECRET = "1x0000000000000000000000000000000AA"
VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


@override_settings(
    TURNSTILE_SITEKEY=DUMMY_SITEKEY,
    TURNSTILE_SECRET=DUMMY_SECRET,
    TURNSTILE_VERIFY_URL=VERIFY_URL,
    TURNSTILE_TIMEOUT=5,
)
class VerifyTurnstileTests(SimpleTestCase):
    """verify_turnstile() with mocked requests.post."""

    def test_empty_token_returns_false(self):
        with patch("utils.turnstile.requests.post") as mock_post:
            self.assertFalse(verify_turnstile(""))
            self.assertFalse(verify_turnstile(None))
            mock_post.assert_not_called()

    @patch("utils.turnstile.requests.post")
    def test_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.assertTrue(verify_turnstile("valid-token", remoteip="1.2.3.4"))

        mock_post.assert_called_once_with(
            VERIFY_URL,
            data={
                "secret": DUMMY_SECRET,
                "response": "valid-token",
                "remoteip": "1.2.3.4",
            },
            timeout=5,
        )

    @patch("utils.turnstile.requests.post")
    def test_failure_success_false(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error-codes": ["invalid-input-response"],
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.assertFalse(verify_turnstile("bad-token"))

    @patch("utils.turnstile.requests.post")
    def test_timeout_returns_false(self, mock_post):
        mock_post.side_effect = requests.Timeout("timed out")
        self.assertFalse(verify_turnstile("any-token"))

    @patch("utils.turnstile.requests.post")
    def test_http_error_returns_false(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")
        mock_post.return_value = mock_response
        self.assertFalse(verify_turnstile("any-token"))

    @patch("utils.turnstile.requests.post")
    def test_action_mismatch_returns_false(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "action": "login",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.assertFalse(verify_turnstile("valid-token", action="register"))

    @patch("utils.turnstile.requests.post")
    def test_action_match_returns_true(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "action": "register",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.assertTrue(verify_turnstile("valid-token", action="register"))

    @patch("utils.turnstile.requests.post")
    def test_action_omitted_in_response_skips_check(self, mock_post):
        """If Cloudflare omits action, do not fail when action was requested."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.assertTrue(verify_turnstile("valid-token", action="register"))


@override_settings(
    TURNSTILE_SITEKEY=DUMMY_SITEKEY,
    TURNSTILE_SECRET=DUMMY_SECRET,
    TURNSTILE_VERIFY_URL=VERIFY_URL,
    TURNSTILE_TIMEOUT=5,
)
class RequireTurnstileTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("utils.turnstile.requests.post")
    def test_reads_token_from_post(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        request = self.factory.post(
            "/login/",
            {"cf-turnstile-response": "tok"},
            HTTP_X_FORWARDED_FOR="9.9.9.9",
        )
        self.assertTrue(require_turnstile(request, action="login"))
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["remoteip"], "9.9.9.9")
        self.assertEqual(kwargs["data"]["response"], "tok")


@override_settings(
    TURNSTILE_SITEKEY=DUMMY_SITEKEY,
    TURNSTILE_SECRET=DUMMY_SECRET,
    TURNSTILE_VERIFY_URL=VERIFY_URL,
    TURNSTILE_TIMEOUT=5,
)
class TurnstileFieldTests(SimpleTestCase):
    @patch("utils.turnstile.requests.post")
    def test_clean_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "action": "contact"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        field = TurnstileField(action="contact")
        self.assertEqual(field.clean("tok"), "tok")

    @patch("utils.turnstile.requests.post")
    def test_clean_failure_raises_validation_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": False}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        field = TurnstileField(action="contact")
        with self.assertRaises(forms.ValidationError):
            field.clean("bad")

    def test_widget_reads_cf_turnstile_response(self):
        field = TurnstileField(action="register")
        value = field.widget.value_from_datadict(
            {"cf-turnstile-response": "abc"}, {}, "captcha"
        )
        self.assertEqual(value, "abc")

    def test_widget_includes_sitekey_and_action(self):
        field = TurnstileField(action="register")
        html = field.widget.render("captcha", None)
        self.assertIn('data-sitekey="%s"' % DUMMY_SITEKEY, html)
        self.assertIn('data-action="register"', html)
        self.assertIn('class="cf-turnstile"', html)


class GetClientIpTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_x_forwarded_for(self):
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2")
        self.assertEqual(get_client_ip(request), "1.1.1.1")

    def test_remote_addr(self):
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "8.8.8.8"
        self.assertEqual(get_client_ip(request), "8.8.8.8")
