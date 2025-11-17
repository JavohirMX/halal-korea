"""
Tests for monitoring email system.
"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from utils.monitoring_emails import (
    send_daily_digest, send_critical_alert, _gather_daily_stats,
    _format_digest_text
)
from utils.models import RequestLog, SecurityEvent
from places.models import HalalPlace
from django.contrib.gis.geos import Point
from unittest.mock import patch

User = get_user_model()


class SendDailyDigestTests(TestCase):
    """Test send_daily_digest function."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    @override_settings(ALERT_EMAIL_ENABLED=False)
    def test_send_daily_digest_disabled(self):
        """Test that digest is not sent when disabled."""
        result = send_daily_digest()
        self.assertFalse(result)
    
    @override_settings(ALERT_EMAIL_ENABLED=True, ALERT_EMAIL_RECIPIENTS=[])
    def test_send_daily_digest_no_recipients(self):
        """Test that digest is not sent with no recipients."""
        result = send_daily_digest()
        self.assertFalse(result)
    
    @override_settings(
        ALERT_EMAIL_ENABLED=True,
        ALERT_EMAIL_RECIPIENTS=['admin@test.com'],
        DEFAULT_FROM_EMAIL='noreply@test.com'
    )
    def test_send_daily_digest_success(self):
        """Test successful daily digest send."""
        # Create some data for yesterday
        yesterday = timezone.now() - timezone.timedelta(days=1)
        RequestLog.objects.create(
            path='/test/', method='GET', status_code=200,
            response_time_ms=100, ip_hash='test', timestamp=yesterday
        )
        
        result = send_daily_digest()
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn('Daily Monitoring Digest', email.subject)
        self.assertEqual(email.to, ['admin@test.com'])
        self.assertIn('REQUEST STATISTICS', email.body)
    
    @override_settings(
        ALERT_EMAIL_ENABLED=True,
        ALERT_EMAIL_RECIPIENTS=['admin1@test.com', 'admin2@test.com'],
        DEFAULT_FROM_EMAIL='noreply@test.com'
    )
    def test_send_daily_digest_multiple_recipients(self):
        """Test digest sent to multiple recipients."""
        result = send_daily_digest()
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertEqual(len(email.to), 2)
        self.assertIn('admin1@test.com', email.to)
        self.assertIn('admin2@test.com', email.to)


class SendCriticalAlertTests(TestCase):
    """Test send_critical_alert function."""
    
    @override_settings(ALERT_EMAIL_ENABLED=False)
    def test_send_critical_alert_disabled(self):
        """Test that alert is not sent when disabled."""
        result = send_critical_alert('Test Alert', 'Test message')
        self.assertFalse(result)
    
    @override_settings(ALERT_EMAIL_ENABLED=True, ALERT_EMAIL_RECIPIENTS=[])
    def test_send_critical_alert_no_recipients(self):
        """Test that alert is not sent with no recipients."""
        result = send_critical_alert('Test Alert', 'Test message')
        self.assertFalse(result)
    
    @override_settings(
        ALERT_EMAIL_ENABLED=True,
        ALERT_EMAIL_RECIPIENTS=['admin@test.com'],
        DEFAULT_FROM_EMAIL='noreply@test.com'
    )
    def test_send_critical_alert_success(self):
        """Test successful critical alert send."""
        result = send_critical_alert(
            'High Error Rate',
            'Error rate has exceeded 50%',
            details={'error_count': 100, 'total_requests': 200},
            link='/admin/monitoring/'
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn('ALERT', email.subject)
        self.assertIn('High Error Rate', email.subject)
        self.assertIn('Error rate has exceeded 50%', email.body)
        self.assertIn('error_count', email.body)
        self.assertIn('/admin/monitoring/', email.body)
    
    @override_settings(
        ALERT_EMAIL_ENABLED=True,
        ALERT_EMAIL_RECIPIENTS=['admin@test.com'],
        DEFAULT_FROM_EMAIL='noreply@test.com',
        SITE_URL='https://example.com'
    )
    def test_send_critical_alert_includes_site_url(self):
        """Test that alert includes full site URL."""
        result = send_critical_alert(
            'Test Alert',
            'Test message',
            link='/admin/test/'
        )
        
        self.assertTrue(result)
        email = mail.outbox[0]
        self.assertIn('https://example.com/admin/test/', email.body)


class GatherDailyStatsTests(TestCase):
    """Test _gather_daily_stats function."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            is_staff=True
        )
        self.today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.yesterday = self.today - timezone.timedelta(days=1)
    
    def test_gather_daily_stats_request_statistics(self):
        """Test gathering request statistics."""
        # Create request logs for today (can't override auto_now_add fields for yesterday)
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timezone.timedelta(days=1)
        
        # Create logs
        for i in range(10):
            RequestLog.objects.create(
                path='/test/', method='GET', status_code=200,
                response_time_ms=100, ip_hash='test', user_agent_hash='test'
            )
        
        # Create one error
        RequestLog.objects.create(
            path='/test/', method='GET', status_code=500,
            response_time_ms=200, ip_hash='test', user_agent_hash='test'
        )
        
        stats = _gather_daily_stats(today_start, tomorrow_start)
        
        # Check if stats were gathered correctly
        self.assertGreaterEqual(stats['requests']['total'], 11)
        self.assertGreaterEqual(stats['requests']['errors'], 1)
        self.assertGreater(stats['requests']['error_rate'], 0)
        self.assertGreater(stats['requests']['avg_response_time'], 0)
    
    def test_gather_daily_stats_security_events(self):
        """Test gathering security event statistics."""
        # Create security events for today
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timezone.timedelta(days=1)
        
        for i in range(3):
            SecurityEvent.objects.create(
                event_type='failed_login',
                severity='medium',
                ip_hash='test'
            )
        
        SecurityEvent.objects.create(
            event_type='rate_limit_hit',
            severity='low',
            ip_hash='test'
        )
        
        stats = _gather_daily_stats(today_start, tomorrow_start)
        
        self.assertGreaterEqual(stats['security']['total'], 4)
        self.assertIn('failed_login', stats['security']['by_type'])
        self.assertGreaterEqual(stats['security']['by_type']['failed_login'], 3)
    
    def test_gather_daily_stats_content_statistics(self):
        """Test gathering content statistics."""
        # Note: created_at has auto_now_add=True, so we can't override it in tests
        # Instead, test with today's data
        HalalPlace.objects.create(
            name='Test Place',
            description='Test',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test',
            status='pending',
            submitted_by=self.user
        )
        
        # Gather today's stats
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timezone.timedelta(days=1)
        stats = _gather_daily_stats(today_start, tomorrow_start)
        
        self.assertGreaterEqual(stats['content']['new_places'], 1)
        self.assertGreaterEqual(stats['content']['pending_places'], 1)
    
    def test_gather_daily_stats_with_no_data(self):
        """Test gathering stats with no data."""
        stats = _gather_daily_stats(self.yesterday, self.today)
        
        # Should return zero values, not crash
        self.assertEqual(stats['requests']['total'], 0)
        self.assertEqual(stats['security']['total'], 0)
        self.assertEqual(stats['content']['new_places'], 0)


class FormatDigestTextTests(TestCase):
    """Test _format_digest_text function."""
    
    def test_format_digest_text_includes_all_sections(self):
        """Test that formatted text includes all sections."""
        yesterday = timezone.now() - timezone.timedelta(days=1)
        stats = {
            'requests': {
                'total': 1000,
                'errors': 10,
                'error_rate': 1.0,
                'avg_response_time': 150.5
            },
            'security': {
                'total': 5,
                'unresolved': 2,
                'by_type': {'failed_login': 3, 'rate_limit_hit': 2}
            },
            'content': {
                'new_places': 3,
                'approved_places': 2,
                'pending_places': 5,
                'pending_suggestions': 1,
                'unread_contacts': 2
            },
            'admin_actions': {
                'total': 20,
                'by_type': {'approve': 10, 'reject': 5, 'update': 5}
            },
            'users': {
                'new_users': 10,
                'active_users': 50
            }
        }
        
        text = _format_digest_text(stats, yesterday)
        
        # Check all sections are present
        self.assertIn('REQUEST STATISTICS', text)
        self.assertIn('SECURITY EVENTS', text)
        self.assertIn('CONTENT STATISTICS', text)
        self.assertIn('ADMIN ACTIVITY', text)
        
        # Check specific values
        self.assertIn('1,000', text)  # Total requests with comma
        self.assertIn('10', text)  # Errors
        self.assertIn('150', text)  # Avg response time
        self.assertIn('failed_login: 3', text)
    
    def test_format_digest_text_handles_zero_values(self):
        """Test formatting with zero values."""
        yesterday = timezone.now() - timezone.timedelta(days=1)
        stats = {
            'requests': {'total': 0, 'errors': 0, 'error_rate': 0, 'avg_response_time': 0},
            'security': {'total': 0, 'unresolved': 0, 'by_type': {}},
            'content': {
                'new_places': 0, 'approved_places': 0,
                'pending_places': 0, 'pending_suggestions': 0, 'unread_contacts': 0
            },
            'admin_actions': {'total': 0, 'by_type': {}},
            'users': {'new_users': 0, 'active_users': 0}
        }
        
        text = _format_digest_text(stats, yesterday)
        
        # Should not crash and should include sections
        self.assertIn('REQUEST STATISTICS', text)
        self.assertIn('Total Requests:', text)
        self.assertIn('0', text)


class EmailIntegrationTests(TestCase):
    """Integration tests for email system."""
    
    @override_settings(
        ALERT_EMAIL_ENABLED=True,
        ALERT_EMAIL_RECIPIENTS=['admin@test.com'],
        DEFAULT_FROM_EMAIL='noreply@test.com'
    )
    def test_email_system_end_to_end(self):
        """Test complete email workflow."""
        # Create some data
        yesterday = timezone.now() - timezone.timedelta(days=1)
        RequestLog.objects.create(
            path='/test/', method='GET', status_code=200,
            response_time_ms=100, ip_hash='test', timestamp=yesterday
        )
        
        # Send daily digest
        result = send_daily_digest()
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        # Send critical alert
        result = send_critical_alert('Test', 'Message')
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 2)
        
        # Verify both emails
        digest_email = mail.outbox[0]
        alert_email = mail.outbox[1]
        
        self.assertIn('Digest', digest_email.subject)
        self.assertIn('ALERT', alert_email.subject)

