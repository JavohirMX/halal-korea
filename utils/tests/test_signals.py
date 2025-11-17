"""
Tests for monitoring signal handlers.
"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone
from utils.models import ContentModerationLog, SecurityEvent, SystemMetric, AdminNotification
from places.models import HalalPlace, PlaceEditSuggestion
from blog.models import BlogPost, Category
from contact.models import ContactMessage
from unittest.mock import Mock, patch

User = get_user_model()


class PlaceModerationSignalTests(TestCase):
    """Test place moderation signal handlers."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            is_staff=True
        )
    
    @override_settings(MONITORING_ENABLED=True)
    def test_place_approval_creates_moderation_log(self):
        """Test that approving a place creates a moderation log."""
        place = HalalPlace.objects.create(
            name='Test Place',
            description='Test',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test Address',
            status='pending',
            submitted_by=self.user
        )
        
        initial_count = ContentModerationLog.objects.count()
        
        # Change status to approved
        place._moderator = self.user
        place.status = 'approved'
        place.save()
        
        # Should create a moderation log
        self.assertGreater(ContentModerationLog.objects.count(), initial_count)
        
        log = ContentModerationLog.objects.latest('timestamp')
        self.assertEqual(log.content_type, 'place')
        self.assertEqual(log.action, 'approved')
        self.assertEqual(log.moderator, self.user)
    
    @override_settings(MONITORING_ENABLED=True)
    def test_place_rejection_creates_moderation_log(self):
        """Test that rejecting a place creates a moderation log."""
        place = HalalPlace.objects.create(
            name='Test Place',
            description='Test',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test Address',
            status='pending',
            submitted_by=self.user
        )
        
        initial_count = ContentModerationLog.objects.count()
        
        place._moderator = self.user
        place.status = 'rejected'
        place.save()
        
        self.assertGreater(ContentModerationLog.objects.count(), initial_count)
        
        log = ContentModerationLog.objects.latest('timestamp')
        self.assertEqual(log.action, 'rejected')
    
    @override_settings(MONITORING_ENABLED=False)
    def test_place_moderation_disabled(self):
        """Test that monitoring can be disabled."""
        place = HalalPlace.objects.create(
            name='Test Place',
            description='Test',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test Address',
            status='pending',
            submitted_by=self.user
        )
        
        initial_count = ContentModerationLog.objects.count()
        
        place._moderator = self.user
        place.status = 'approved'
        place.save()
        
        # Should not create log when disabled
        self.assertEqual(ContentModerationLog.objects.count(), initial_count)


class SuggestionModerationSignalTests(TestCase):
    """Test suggestion moderation signal handlers."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.moderator = User.objects.create_user(
            username='moderator',
            password='modpass',
            is_staff=True
        )
        self.place = HalalPlace.objects.create(
            name='Test Place',
            description='Test',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test Address',
            status='approved',
            submitted_by=self.user
        )
    
    @override_settings(MONITORING_ENABLED=True)
    def test_suggestion_approval_creates_log(self):
        """Test that approving a suggestion creates a log."""
        suggestion = PlaceEditSuggestion.objects.create(
            place=self.place,
            suggested_by=self.user,
            field_name='name',
            current_value='Test Place',
            suggested_value='Better Name',
            reason='More accurate',
            status='pending'
        )
        
        initial_count = ContentModerationLog.objects.count()
        
        suggestion.reviewed_by = self.moderator
        suggestion.status = 'approved'
        suggestion.save()
        
        self.assertGreater(ContentModerationLog.objects.count(), initial_count)
        
        log = ContentModerationLog.objects.latest('timestamp')
        self.assertEqual(log.content_type, 'suggestion')
        self.assertEqual(log.action, 'approved')


class ContactMessageSignalTests(TestCase):
    """Test contact message signal handlers."""
    
    @override_settings(MONITORING_ENABLED=True)
    def test_contact_message_creates_notification(self):
        """Test that new contact message creates admin notification."""
        initial_count = AdminNotification.objects.count()
        
        ContactMessage.objects.create(
            name='John Doe',
            email='john@example.com',
            subject='Test Subject',
            message='Test message',
            ip_address='127.0.0.1'
        )
        
        # Should create admin notification
        self.assertGreater(AdminNotification.objects.count(), initial_count)
        
        notification = AdminNotification.objects.latest('timestamp')
        self.assertIn('Contact Message', notification.title)
        self.assertEqual(notification.severity, 'info')
    
    @override_settings(MONITORING_ENABLED=True)
    def test_contact_message_creates_metric(self):
        """Test that contact message creates system metric."""
        initial_count = SystemMetric.objects.count()
        
        ContactMessage.objects.create(
            name='Jane Doe',
            email='jane@example.com',
            message='Test',
            ip_address='127.0.0.1'
        )
        
        # Should create system metric
        self.assertGreater(SystemMetric.objects.count(), initial_count)


class AuthenticationSignalTests(TestCase):
    """Test authentication signal handlers."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    @override_settings(MONITORING_ENABLED=True)
    def test_successful_login_creates_metric(self):
        """Test that successful login creates a metric."""
        from django.contrib.auth.signals import user_logged_in
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.post('/login/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        initial_count = SystemMetric.objects.count()
        
        # Trigger signal
        user_logged_in.send(sender=User, request=request, user=self.user)
        
        # Should create metric
        self.assertGreater(SystemMetric.objects.count(), initial_count)
    
    @override_settings(MONITORING_ENABLED=True)
    def test_failed_login_creates_security_event(self):
        """Test that failed login creates security event."""
        from django.contrib.auth.signals import user_login_failed
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.post('/login/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        initial_count = SecurityEvent.objects.count()
        
        # Trigger signal
        user_login_failed.send(
            sender=User,
            credentials={'username': 'testuser'},
            request=request
        )
        
        # Should create security event
        self.assertGreater(SecurityEvent.objects.count(), initial_count)
        
        event = SecurityEvent.objects.latest('timestamp')
        self.assertEqual(event.event_type, 'failed_login')
        self.assertEqual(event.severity, 'medium')
    
    @override_settings(MONITORING_ENABLED=True)
    def test_multiple_failed_logins_create_alert(self):
        """Test that multiple failed logins create high-severity alert."""
        from django.contrib.auth.signals import user_login_failed
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.post('/login/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Create 5 failed login attempts
        for i in range(5):
            user_login_failed.send(
                sender=User,
                credentials={'username': 'testuser'},
                request=request
            )
        
        # Should have created suspicious activity event
        suspicious_events = SecurityEvent.objects.filter(
            event_type='suspicious_activity'
        )
        self.assertGreater(suspicious_events.count(), 0)
        
        # Should have created admin notification
        notifications = AdminNotification.objects.filter(
            title__icontains='Failed Login'
        )
        self.assertGreater(notifications.count(), 0)
    
    @override_settings(MONITORING_ENABLED=True)
    def test_logout_creates_metric(self):
        """Test that logout creates a metric."""
        from django.contrib.auth.signals import user_logged_out
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.post('/logout/')
        
        initial_count = SystemMetric.objects.filter(
            metric_name='user_logout'
        ).count()
        
        # Trigger signal
        user_logged_out.send(sender=User, request=request, user=self.user)
        
        # Should create metric
        new_count = SystemMetric.objects.filter(
            metric_name='user_logout'
        ).count()
        self.assertGreater(new_count, initial_count)


class SignalHelperFunctionTests(TestCase):
    """Test signal helper functions."""
    
    @override_settings(MONITORING_ENABLED=True)
    def test_log_rate_limit_hit(self):
        """Test logging rate limit hits."""
        from utils.monitoring_signals import log_rate_limit_hit
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.post('/api/test/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.user = User.objects.create_user(username='test', password='pass')
        
        initial_count = SecurityEvent.objects.filter(
            event_type='rate_limit_hit'
        ).count()
        
        log_rate_limit_hit(request, 'email_send', {'limit': 5})
        
        new_count = SecurityEvent.objects.filter(
            event_type='rate_limit_hit'
        ).count()
        self.assertGreater(new_count, initial_count)
    
    @override_settings(MONITORING_ENABLED=True)
    def test_log_permission_denied(self):
        """Test logging permission denied events."""
        from utils.monitoring_signals import log_permission_denied
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/admin/secret/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.user = User.objects.create_user(username='test', password='pass')
        
        initial_count = SecurityEvent.objects.filter(
            event_type='permission_denied'
        ).count()
        
        log_permission_denied(request, 'Not staff user')
        
        new_count = SecurityEvent.objects.filter(
            event_type='permission_denied'
        ).count()
        self.assertGreater(new_count, initial_count)

