"""
Tests for Telegram notification formatting helpers.
"""
from django.test import SimpleTestCase, override_settings
from utils.telegram_notifications import (
    format_telegram_message,
    send_telegram_message,
    send_telegram_notification,
)


class FormatTelegramMessageTests(SimpleTestCase):
    """Shared HTML + hashtag formatter."""

    @override_settings(ENVIRONMENT='production', SITE_URL='https://halal-korea.com')
    def test_includes_severity_badge_env_and_hashtags(self):
        msg = format_telegram_message(
            'Monitoring System Health: Warnings',
            ['No recent system metrics - Run aggregate_metrics command'],
            severity='warning',
            category='monitoring',
            link='/admin/monitoring/',
        )

        self.assertIn('⚠️ <b>Monitoring System Health: Warnings</b>', msg)
        self.assertIn('<code>WARNING</code>', msg)
        self.assertIn('production', msg)
        self.assertIn('• No recent system metrics - Run aggregate_metrics command', msg)
        self.assertIn('🔗 <a href="https://halal-korea.com/admin/monitoring/">Open dashboard</a>', msg)
        self.assertIn('#halalkorea #monitoring #warning #production', msg)

    @override_settings(ENVIRONMENT='development', SITE_URL='http://localhost:8000')
    def test_places_category_info_hashtags(self):
        msg = format_telegram_message(
            'New Place Submission!',
            ['Name: Test Cafe'],
            severity='info',
            category='places',
        )
        self.assertIn('#halalkorea #places #info #development', msg)
        self.assertIn('<code>INFO</code>', msg)

    @override_settings(ENVIRONMENT='production')
    def test_escapes_user_controlled_html(self):
        msg = format_telegram_message(
            'Contact',
            ['Name: <script>alert(1)</script>'],
            severity='info',
            category='contact',
        )
        self.assertNotIn('<script>', msg)
        self.assertIn('&lt;script&gt;', msg)

    @override_settings(ENVIRONMENT='staging')
    def test_maps_high_severity_to_warning_hashtag(self):
        msg = format_telegram_message(
            'Alert',
            ['error_rate: 12%'],
            severity='high',
            category='monitoring',
        )
        self.assertIn('#warning', msg)
        self.assertIn('<code>WARNING</code>', msg)

    def test_send_telegram_message_is_alias(self):
        self.assertIs(send_telegram_message, send_telegram_notification)
