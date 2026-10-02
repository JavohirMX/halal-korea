"""Tests for feedback submission API (Turnstile-protected)."""

import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from feedback.models import FeedbackResponse

TURNSTILE_TOKEN = "test-turnstile-token"
TURNSTILE_SETTINGS = {
    "TURNSTILE_SITEKEY": "1x00000000000000000000AA",
    "TURNSTILE_SECRET": "1x0000000000000000000000000000000AA",
}


@override_settings(**TURNSTILE_SETTINGS)
class SubmitFeedbackTurnstileTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client()
        self.url = reverse("feedback:submit")
        self.payload = {
            "rating": 5,
            "page_url": "http://testserver/",
            "page_type": "home",
            "session_id": "test-session-123",
            "time_on_site": 10,
            "time_on_page": 5,
            "language": "en",
            "device_type": "desktop",
            "cf-turnstile-response": TURNSTILE_TOKEN,
        }

    def _post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_missing_turnstile_token_rejected(self):
        payload = dict(self.payload)
        del payload["cf-turnstile-response"]
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("security check", data["error"].lower())
        self.assertEqual(FeedbackResponse.objects.count(), 0)

    @patch("feedback.views.verify_turnstile", return_value=False)
    def test_invalid_turnstile_token_rejected(self, mock_verify):
        response = self._post(self.payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("security check", data["error"].lower())
        self.assertEqual(FeedbackResponse.objects.count(), 0)
        mock_verify.assert_called_once()

    @patch("feedback.views.verify_turnstile", return_value=True)
    def test_valid_turnstile_accepted(self, mock_verify):
        response = self._post(self.payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(FeedbackResponse.objects.count(), 1)
        mock_verify.assert_called_once()
        _, kwargs = mock_verify.call_args
        self.assertEqual(kwargs.get("action"), "feedback")
