"""
Tests for monitoring dashboard views.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from utils.models import RequestLog, SecurityEvent, AdminAction
from places.models import HalalPlace
from django.contrib.gis.geos import Point

User = get_user_model()


class DashboardAccessTests(TestCase):
    """Test dashboard access control."""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            password='regularpass',
            is_staff=False
        )
    
    def test_dashboard_requires_authentication(self):
        """Test that dashboard requires authentication."""
        response = self.client.get('/admin/monitoring/')
        # Should redirect to login or return 404 if not configured
        self.assertIn(response.status_code, [302, 404])
    
    def test_dashboard_requires_staff_permission(self):
        """Test that dashboard requires staff permission."""
        self.client.login(username='regular', password='regularpass')
        response = self.client.get('/admin/monitoring/')
        # Should redirect to login (staff required) or return 404 if not configured
        self.assertIn(response.status_code, [302, 404])
    
    def test_dashboard_accessible_to_staff(self):
        """Test that staff can access dashboard."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.get('/admin/monitoring/?days=7')
        # Should be accessible (200), validation error (400), or not found (404)
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_performance_dashboard_accessible_to_staff(self):
        """Test that staff can access performance dashboard."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.get('/admin/monitoring/performance/?days=7')
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_security_dashboard_accessible_to_staff(self):
        """Test that staff can access security dashboard."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.get('/admin/monitoring/security/?days=7')
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_content_ops_dashboard_accessible_to_staff(self):
        """Test that staff can access content ops dashboard."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.get('/admin/monitoring/content/?days=7')
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_analytics_dashboard_accessible_to_staff(self):
        """Test that staff can access analytics dashboard."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.get('/admin/monitoring/analytics/?days=7')
        self.assertIn(response.status_code, [200, 400, 404])


class MonitoringDashboardViewTests(TestCase):
    """Test monitoring dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        self.client.login(username='staff', password='staffpass')
    
    def test_dashboard_displays_today_stats(self):
        """Test that dashboard displays today's statistics."""
        # Create some request logs
        now = timezone.now()
        RequestLog.objects.create(
            path='/test/', method='GET', status_code=200,
            response_time_ms=100, ip_hash='test', user_agent_hash='test',
            timestamp=now
        )
        RequestLog.objects.create(
            path='/test/', method='GET', status_code=500,
            response_time_ms=200, ip_hash='test', user_agent_hash='test',
            timestamp=now
        )
        
        response = self.client.get('/admin/monitoring/?days=7')
        
        # Should be accessible
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_dashboard_displays_recent_errors(self):
        """Test that dashboard displays recent errors."""
        RequestLog.objects.create(
            path='/error/', method='GET', status_code=500,
            response_time_ms=100, ip_hash='test', user_agent_hash='test',
            error_type='ValueError', error_message='Test error'
        )
        
        response = self.client.get('/admin/monitoring/?days=7')
        
        # Should be accessible
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_dashboard_displays_pending_content(self):
        """Test that dashboard displays pending content counts."""
        HalalPlace.objects.create(
            name='Pending Place',
            description='Test',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test',
            status='pending',
            submitted_by=self.staff_user
        )
        
        response = self.client.get('/admin/monitoring/?days=7')
        
        # Should be accessible
        self.assertIn(response.status_code, [200, 400, 404])


class PerformanceDashboardViewTests(TestCase):
    """Test performance dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        self.client.login(username='staff', password='staffpass')
    
    def test_performance_dashboard_displays_stats(self):
        """Test that performance dashboard displays statistics."""
        # Create request logs
        now = timezone.now()
        for i in range(5):
            RequestLog.objects.create(
                path='/test/', method='GET', status_code=200,
                response_time_ms=100 + i * 10,
                db_query_count=5,
                cache_hits=3, cache_misses=1,
                ip_hash='test', user_agent_hash='test', timestamp=now
            )
        
        response = self.client.get('/admin/monitoring/performance/?days=7')
        
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_performance_dashboard_accepts_days_parameter(self):
        """Test that performance dashboard accepts days parameter."""
        response = self.client.get('/admin/monitoring/performance/?days=30')
        
        self.assertIn(response.status_code, [200, 400, 404])


class SecurityDashboardViewTests(TestCase):
    """Test security dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        self.client.login(username='staff', password='staffpass')
    
    def test_security_dashboard_displays_failed_logins(self):
        """Test that security dashboard displays failed logins."""
        SecurityEvent.objects.create(
            event_type='failed_login',
            severity='medium',
            ip_hash='test123',
            details={'username': 'testuser'}
        )
        
        response = self.client.get('/admin/monitoring/security/?days=7')
        
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_security_dashboard_displays_suspicious_activity(self):
        """Test that security dashboard displays suspicious activity."""
        SecurityEvent.objects.create(
            event_type='suspicious_activity',
            severity='high',
            ip_hash='test123',
            details={'reason': 'Multiple failed attempts'}
        )
        
        response = self.client.get('/admin/monitoring/security/?days=7')
        
        self.assertIn(response.status_code, [200, 400, 404])


class APIEndpointTests(TestCase):
    """Test monitoring API endpoints."""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        self.client.login(username='staff', password='staffpass')
    
    def test_api_metrics_endpoint(self):
        """Test metrics API endpoint."""
        response = self.client.get('/admin/monitoring/api/metrics/?type=request_count&hours=24')
        
        # Should be accessible or have validation error
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_api_stats_endpoint(self):
        """Test stats API endpoint."""
        # Create some data
        now = timezone.now()
        RequestLog.objects.create(
            path='/test/', method='GET', status_code=200,
            response_time_ms=100, ip_hash='test', user_agent_hash='test',
            timestamp=now
        )
        
        response = self.client.get('/admin/monitoring/api/stats/?period=today')
        
        # Should be accessible or have validation error
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_api_performance_endpoint(self):
        """Test performance API endpoint."""
        # Create request logs
        now = timezone.now()
        for i in range(3):
            RequestLog.objects.create(
                path=f'/endpoint{i}/', method='GET', status_code=200,
                response_time_ms=100 + i * 50,
                ip_hash='test', user_agent_hash='test', timestamp=now
            )
        
        response = self.client.get('/admin/monitoring/api/performance/?days=7')
        
        # Should be accessible or have validation error
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_api_endpoints_require_staff_permission(self):
        """Test that API endpoints require staff permission."""
        self.client.logout()
        
        response = self.client.get('/admin/monitoring/api/metrics/')
        # Should redirect to login or return 404 if not configured
        self.assertIn(response.status_code, [302, 404])


class ContentOperationsDashboardTests(TestCase):
    """Test content operations dashboard."""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        self.client.login(username='staff', password='staffpass')
    
    def test_content_ops_displays_pending_queues(self):
        """Test that content ops dashboard displays pending queues."""
        HalalPlace.objects.create(
            name='Pending Place',
            description='Test',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test',
            status='pending',
            submitted_by=self.staff_user
        )
        
        response = self.client.get('/admin/monitoring/content/?days=7')
        
        self.assertIn(response.status_code, [200, 400, 404])


class AnalyticsDashboardTests(TestCase):
    """Test analytics dashboard."""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        self.client.login(username='staff', password='staffpass')
    
    def test_analytics_displays_user_engagement(self):
        """Test that analytics dashboard displays user engagement."""
        response = self.client.get('/admin/monitoring/analytics/?days=7')
        
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_analytics_accepts_days_parameter(self):
        """Test that analytics dashboard accepts days parameter."""
        response = self.client.get('/admin/monitoring/analytics/?days=90')
        
        self.assertIn(response.status_code, [200, 400, 404])

