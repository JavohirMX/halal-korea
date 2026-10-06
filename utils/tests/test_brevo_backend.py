"""
Unit tests for BrevoAPIBackend.
"""
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
from django.core.mail import EmailMessage, EmailMultiAlternatives
import requests
from utils.email_backends.brevo_api import BrevoAPIBackend


class BrevoAPIBackendTests(SimpleTestCase):
    def setUp(self):
        self.backend = BrevoAPIBackend(api_key="test-api-key-12345")

    @patch("utils.email_backends.brevo_api.requests.post")
    def test_send_plain_text_message(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"messageId": "<msg-123>"}'
        mock_response.json.return_value = {"messageId": "<msg-123>"}
        mock_post.return_value = mock_response

        msg = EmailMessage(
            subject="Welcome!",
            body="Hello from Halal Korea",
            from_email="Halal Korea <noreply@halal-korea.com>",
            to=["user@example.com"],
        )

        sent = self.backend.send_messages([msg])

        self.assertEqual(sent, 1)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        self.assertEqual(call_kwargs["headers"]["api-key"], "test-api-key-12345")
        payload = call_kwargs["json"]
        self.assertEqual(payload["subject"], "Welcome!")
        self.assertEqual(payload["textContent"], "Hello from Halal Korea")
        self.assertEqual(payload["sender"], {"name": "Halal Korea", "email": "noreply@halal-korea.com"})
        self.assertEqual(payload["to"], [{"email": "user@example.com"}])

    @patch("utils.email_backends.brevo_api.requests.post")
    def test_send_html_message(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"messageId": "<msg-456>"}'
        mock_response.json.return_value = {"messageId": "<msg-456>"}
        mock_post.return_value = mock_response

        msg = EmailMultiAlternatives(
            subject="HTML Test",
            body="Plain fallback",
            from_email="noreply@halal-korea.com",
            to=["recipient <recipient@example.com>"],
        )
        msg.attach_alternative("<p>HTML Content</p>", "text/html")

        sent = self.backend.send_messages([msg])

        self.assertEqual(sent, 1)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["textContent"], "Plain fallback")
        self.assertEqual(payload["htmlContent"], "<p>HTML Content</p>")
        self.assertEqual(payload["to"], [{"name": "recipient", "email": "recipient@example.com"}])

    @patch("utils.email_backends.brevo_api.requests.post")
    def test_send_with_cc_bcc_and_reply_to(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"messageId": "<msg-789>"}'
        mock_response.json.return_value = {"messageId": "<msg-789>"}
        mock_post.return_value = mock_response

        msg = EmailMessage(
            subject="CC Test",
            body="Body text",
            from_email="noreply@halal-korea.com",
            to=["to@example.com"],
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
            reply_to=["support@halal-korea.com"],
        )

        sent = self.backend.send_messages([msg])

        self.assertEqual(sent, 1)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["cc"], [{"email": "cc@example.com"}])
        self.assertEqual(payload["bcc"], [{"email": "bcc@example.com"}])
        self.assertEqual(payload["replyTo"], {"email": "support@halal-korea.com"})

    @patch("utils.email_backends.brevo_api.requests.post")
    def test_send_with_attachment(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"messageId": "<msg-att>"}'
        mock_response.json.return_value = {"messageId": "<msg-att>"}
        mock_post.return_value = mock_response

        msg = EmailMessage(
            subject="Attachment Test",
            body="See attached",
            from_email="noreply@halal-korea.com",
            to=["to@example.com"],
        )
        msg.attach("sample.txt", "Hello World Content", "text/plain")

        sent = self.backend.send_messages([msg])

        self.assertEqual(sent, 1)
        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("attachment", payload)
        self.assertEqual(payload["attachment"][0]["name"], "sample.txt")
        self.assertEqual(payload["attachment"][0]["content"], "SGVsbG8gV29ybGQgQ29udGVudA==")

    def test_missing_api_key_raises_when_not_fail_silently(self):
        backend = BrevoAPIBackend(api_key="", fail_silently=False)
        msg = EmailMessage(subject="Test", body="Test", to=["a@b.com"])

        with self.assertRaises(ValueError):
            backend.send_messages([msg])

    def test_missing_api_key_suppressed_when_fail_silently(self):
        backend = BrevoAPIBackend(api_key="", fail_silently=True)
        msg = EmailMessage(subject="Test", body="Test", to=["a@b.com"])

        sent = backend.send_messages([msg])
        self.assertEqual(sent, 0)

    @patch("utils.email_backends.brevo_api.requests.post")
    def test_api_http_error_handling(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"code": "unauthorized", "message": "Key not found"}'
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Client Error")
        mock_post.return_value = mock_response

        msg = EmailMessage(subject="Test", body="Test", to=["a@b.com"])

        # fail_silently=False should raise
        backend = BrevoAPIBackend(api_key="bad-key", fail_silently=False)
        with self.assertRaises(requests.exceptions.HTTPError):
            backend.send_messages([msg])

        # fail_silently=True should suppress
        backend_silent = BrevoAPIBackend(api_key="bad-key", fail_silently=True)
        sent = backend_silent.send_messages([msg])
        self.assertEqual(sent, 0)

    def test_empty_messages_list(self):
        sent = self.backend.send_messages([])
        self.assertEqual(sent, 0)
