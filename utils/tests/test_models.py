"""
Tests for monitoring models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from utils.models import (
    SystemMetric, RequestLog, AdminAction, ContentModerationLog,
    SecurityEvent, AdminNotification, AlertRule, hash_ip, hash_user_agent
)
from places.models import HalalPlace
from django.contrib.gis.geos import Point

User = get_user_model()


class HashFunctionTests(TestCase):
    """Test IP and user agent hashing functions."""
    
    def test_hash_ip_returns_consistent_hash(self):
        """Test that hashing same IP returns same hash."""
        ip = "192.168.1.1"
        hash1 = hash_ip(ip)
        hash2 = hash_ip(ip)
        self.assertEqual(hash1, hash2)
    
    def test_hash_ip_returns_different_for_different_ips(self):
        """Test that different IPs produce different hashes."""
        hash1 = hash_ip("192.168.1.1")
        hash2 = hash_ip("192.168.1.2")
        self.assertNotEqual(hash1, hash2)
    
    def test_hash_ip_returns_16_char_string(self):
        """Test that hash is 16 characters long."""
        result = hash_ip("192.168.1.1")
        self.assertEqual(len(result), 16)
    
    def test_hash_ip_handles_none(self):
        """Test that None IP returns None."""
        result = hash_ip(None)
        self.assertIsNone(result)
    
    def test_hash_user_agent_handles_empty(self):
        """Test that empty user agent returns empty string."""
        result = hash_user_agent('')
        self.assertEqual(result, '')
        
        result = hash_user_agent(None)
        self.assertEqual(result, '')
    
    def test_hash_user_agent_works(self):
        """Test user agent hashing."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        hash1 = hash_user_agent(ua)
        hash2 = hash_user_agent(ua)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)


class SystemMetricModelTests(TestCase):
    """Test SystemMetric model."""
    
    def test_create_system_metric(self):
        """Test creating a system metric."""
        metric = SystemMetric.objects.create(
            timestamp=timezone.now(),
            metric_type='request_count',
            metric_name='total_requests',
            value=100,
            metadata={'source': 'test'}
        )
        self.assertEqual(metric.metric_type, 'request_count')
        self.assertEqual(metric.value, 100)
        self.assertIn('source', metric.metadata)
    
    def test_system_metric_str(self):
        """Test string representation."""
        metric = SystemMetric.objects.create(
            timestamp=timezone.now(),
            metric_type='error_count',
            metric_name='server_errors',
            value=5
        )
        str_repr = str(metric)
        self.assertIn('error_count', str_repr)
        self.assertIn('server_errors', str_repr)


class RequestLogModelTests(TestCase):
    """Test RequestLog model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    def test_create_request_log(self):
        """Test creating a request log."""
        log = RequestLog.objects.create(
            path='/api/test/',
            method='GET',
            status_code=200,
            response_time_ms=150.5,
            user=self.user,
            is_staff=False,
            ip_hash='abc123',
            user_agent_hash='def456',
            db_query_count=5,
            cache_hits=2,
            cache_misses=1
        )
        self.assertEqual(log.path, '/api/test/')
        self.assertEqual(log.status_code, 200)
        self.assertEqual(log.user, self.user)
    
    def test_is_error_property(self):
        """Test is_error property."""
        log_ok = RequestLog.objects.create(
            path='/test/', method='GET', status_code=200,
            response_time_ms=100, ip_hash='test'
        )
        log_error = RequestLog.objects.create(
            path='/test/', method='GET', status_code=500,
            response_time_ms=100, ip_hash='test'
        )
        self.assertFalse(log_ok.is_error)
        self.assertTrue(log_error.is_error)
    
    def test_is_slow_property(self):
        """Test is_slow property."""
        log_fast = RequestLog.objects.create(
            path='/test/', method='GET', status_code=200,
            response_time_ms=500, ip_hash='test'
        )
        log_slow = RequestLog.objects.create(
            path='/test/', method='GET', status_code=200,
            response_time_ms=2000, ip_hash='test'
        )
        self.assertFalse(log_fast.is_slow)
        self.assertTrue(log_slow.is_slow)
    
    def test_request_log_with_error(self):
        """Test logging request with error."""
        log = RequestLog.objects.create(
            path='/api/fail/',
            method='POST',
            status_code=500,
            response_time_ms=250,
            ip_hash='test123',
            error_type='ValueError',
            error_message='Test error message'
        )
        self.assertEqual(log.error_type, 'ValueError')
        self.assertTrue(log.is_error)


class AdminActionModelTests(TestCase):
    """Test AdminAction model."""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass',
            is_staff=True
        )
        self.place = HalalPlace.objects.create(
            name='Test Place',
            description='Test',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test Address',
            status='pending',
            submitted_by=self.admin_user
        )
    
    def test_create_admin_action(self):
        """Test creating an admin action."""
        content_type = ContentType.objects.get_for_model(HalalPlace)
        action = AdminAction.objects.create(
            admin_user=self.admin_user,
            action_type='approve',
            content_type=content_type,
            object_id=self.place.pk,
            object_repr=str(self.place),
            changes={'status': {'old': 'pending', 'new': 'approved'}},
            ip_hash='test123'
        )
        self.assertEqual(action.action_type, 'approve')
        self.assertEqual(action.admin_user, self.admin_user)
        self.assertIn('status', action.changes)
    
    def test_admin_action_str(self):
        """Test string representation."""
        content_type = ContentType.objects.get_for_model(HalalPlace)
        action = AdminAction.objects.create(
            admin_user=self.admin_user,
            action_type='update',
            content_type=content_type,
            object_id=self.place.pk,
            object_repr='Test Place',
            ip_hash='test'
        )
        str_repr = str(action)
        self.assertIn('admin', str_repr)
        self.assertIn('update', str_repr)


class ContentModerationLogModelTests(TestCase):
    """Test ContentModerationLog model."""
    
    def setUp(self):
        self.moderator = User.objects.create_user(
            username='moderator',
            password='modpass',
            is_staff=True
        )
    
    def test_create_moderation_log(self):
        """Test creating a moderation log."""
        log = ContentModerationLog.objects.create(
            moderator=self.moderator,
            content_type='place',
            object_id=1,
            action='approved',
            time_in_queue_hours=24.5,
            reason='Looks good'
        )
        self.assertEqual(log.action, 'approved')
        self.assertEqual(log.time_in_queue_hours, 24.5)
    
    def test_moderation_log_str(self):
        """Test string representation."""
        log = ContentModerationLog.objects.create(
            moderator=self.moderator,
            content_type='suggestion',
            object_id=5,
            action='rejected'
        )
        str_repr = str(log)
        self.assertIn('moderator', str_repr)
        self.assertIn('rejected', str_repr)


class SecurityEventModelTests(TestCase):
    """Test SecurityEvent model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_create_security_event(self):
        """Test creating a security event."""
        event = SecurityEvent.objects.create(
            event_type='failed_login',
            severity='medium',
            user=self.user,
            ip_hash='test123',
            details={'username': 'testuser', 'attempts': 3}
        )
        self.assertEqual(event.event_type, 'failed_login')
        self.assertEqual(event.severity, 'medium')
        self.assertFalse(event.resolved)
    
    def test_mark_resolved(self):
        """Test marking event as resolved."""
        resolver = User.objects.create_user(username='admin', is_staff=True)
        event = SecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='high',
            ip_hash='test'
        )
        
        event.mark_resolved(resolver, 'False positive')
        
        self.assertTrue(event.resolved)
        self.assertIsNotNone(event.resolved_at)
        self.assertEqual(event.resolved_by, resolver)
        self.assertEqual(event.resolution_notes, 'False positive')
    
    def test_security_event_str(self):
        """Test string representation."""
        event = SecurityEvent.objects.create(
            event_type='rate_limit_hit',
            severity='low',
            ip_hash='test'
        )
        str_repr = str(event)
        self.assertIn('rate_limit_hit', str_repr)


class AdminNotificationModelTests(TestCase):
    """Test AdminNotification model."""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            is_staff=True
        )
    
    def test_create_notification(self):
        """Test creating a notification."""
        notification = AdminNotification.objects.create(
            recipient=self.admin,
            title='Test Alert',
            message='This is a test notification',
            severity='warning',
            link='/admin/test/'
        )
        self.assertEqual(notification.title, 'Test Alert')
        self.assertFalse(notification.read)
        self.assertFalse(notification.dismissed)
    
    def test_create_notification_for_all_admins(self):
        """Test creating notification for all admins."""
        notification = AdminNotification.objects.create(
            recipient=None,  # All admins
            title='System Alert',
            message='Important message',
            severity='critical'
        )
        self.assertIsNone(notification.recipient)
    
    def test_mark_read(self):
        """Test marking notification as read."""
        notification = AdminNotification.objects.create(
            recipient=self.admin,
            title='Test',
            message='Test message',
            severity='info'
        )
        
        notification.mark_read()
        
        self.assertTrue(notification.read)
        self.assertIsNotNone(notification.read_at)
    
    def test_mark_dismissed(self):
        """Test marking notification as dismissed."""
        notification = AdminNotification.objects.create(
            recipient=self.admin,
            title='Test',
            message='Test message',
            severity='info'
        )
        
        notification.mark_dismissed()
        
        self.assertTrue(notification.dismissed)
        self.assertIsNotNone(notification.dismissed_at)
    
    def test_notification_str(self):
        """Test string representation."""
        notification = AdminNotification.objects.create(
            recipient=self.admin,
            title='Test Alert',
            message='Message',
            severity='info'
        )
        str_repr = str(notification)
        self.assertIn('Test Alert', str_repr)
        self.assertIn('admin', str_repr)


class AlertRuleModelTests(TestCase):
    """Test AlertRule model."""
    
    def test_create_alert_rule(self):
        """Test creating an alert rule."""
        rule = AlertRule.objects.create(
            name='High Error Rate',
            description='Alert when error rate exceeds 5%',
            condition='error_rate_above',
            threshold=5.0,
            window_minutes=10,
            alert_channels=['telegram', 'email'],
            cooldown_minutes=60,
            enabled=True
        )
        self.assertEqual(rule.name, 'High Error Rate')
        self.assertEqual(rule.threshold, 5.0)
        self.assertTrue(rule.enabled)
    
    def test_can_trigger_when_never_triggered(self):
        """Test can_trigger returns True when never triggered."""
        rule = AlertRule.objects.create(
            name='Test Rule',
            condition='error_rate_above',
            threshold=5.0,
            enabled=True
        )
        self.assertTrue(rule.can_trigger())
    
    def test_can_trigger_respects_cooldown(self):
        """Test can_trigger respects cooldown period."""
        rule = AlertRule.objects.create(
            name='Test Rule',
            condition='error_rate_above',
            threshold=5.0,
            cooldown_minutes=60,
            enabled=True,
            last_triggered=timezone.now() - timezone.timedelta(minutes=30)
        )
        self.assertFalse(rule.can_trigger())
    
    def test_can_trigger_after_cooldown(self):
        """Test can_trigger returns True after cooldown."""
        rule = AlertRule.objects.create(
            name='Test Rule',
            condition='error_rate_above',
            threshold=5.0,
            cooldown_minutes=60,
            enabled=True,
            last_triggered=timezone.now() - timezone.timedelta(minutes=90)
        )
        self.assertTrue(rule.can_trigger())
    
    def test_can_trigger_disabled_rule(self):
        """Test can_trigger returns False for disabled rule."""
        rule = AlertRule.objects.create(
            name='Test Rule',
            condition='error_rate_above',
            threshold=5.0,
            enabled=False
        )
        self.assertFalse(rule.can_trigger())
    
    def test_record_trigger(self):
        """Test recording a trigger."""
        rule = AlertRule.objects.create(
            name='Test Rule',
            condition='error_rate_above',
            threshold=5.0,
            enabled=True
        )
        
        initial_count = rule.trigger_count
        rule.record_trigger()
        
        self.assertIsNotNone(rule.last_triggered)
        self.assertEqual(rule.trigger_count, initial_count + 1)
    
    def test_alert_rule_str(self):
        """Test string representation."""
        rule = AlertRule.objects.create(
            name='Test Alert',
            condition='error_rate_above',
            threshold=5.0,
            enabled=True
        )
        str_repr = str(rule)
        self.assertIn('Test Alert', str_repr)
        self.assertIn('Enabled', str_repr)

