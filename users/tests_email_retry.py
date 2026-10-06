"""
Unit tests for email retry logic in users/utils.py.
"""
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
import socket
from users.utils import _deliver_email


class DeliverEmailRetryTests(SimpleTestCase):
    @patch("users.utils.send_mail")
    @patch("users.utils.time.sleep")
    def test_deliver_email_succeeds_first_attempt(self, mock_sleep, mock_send_mail):
        mock_send_mail.return_value = 1

        _deliver_email(
            subject="Test",
            plain_message="Body",
            html_message="<p>Body</p>",
            recipient="test@example.com",
            success_log="Success!",
            error_log="Error!",
            max_retries=2,
        )

        self.assertEqual(mock_send_mail.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("users.utils.send_mail")
    @patch("users.utils.time.sleep")
    def test_deliver_email_succeeds_on_retry(self, mock_sleep, mock_send_mail):
        # First call fails with TimeoutError, second call succeeds
        mock_send_mail.side_effect = [socket.timeout("Connection timed out"), 1]

        _deliver_email(
            subject="Test",
            plain_message="Body",
            html_message="<p>Body</p>",
            recipient="test@example.com",
            success_log="Success!",
            error_log="Error!",
            max_retries=2,
        )

        self.assertEqual(mock_send_mail.call_count, 2)
        mock_sleep.assert_called_once_with(1.5)

    @patch("users.utils.send_mail")
    @patch("users.utils.time.sleep")
    def test_deliver_email_fails_after_max_retries(self, mock_sleep, mock_send_mail):
        # All 3 attempts fail
        mock_send_mail.side_effect = [
            socket.timeout("timed out"),
            socket.timeout("timed out"),
            socket.timeout("timed out"),
        ]

        _deliver_email(
            subject="Test",
            plain_message="Body",
            html_message="<p>Body</p>",
            recipient="test@example.com",
            success_log="Success!",
            error_log="Error!",
            max_retries=2,
        )

        self.assertEqual(mock_send_mail.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
