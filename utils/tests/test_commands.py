"""
Tests for monitoring management commands.
"""
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.gis.geos import Point
from utils.models import RequestLog, SystemMetric, AlertRule, SecurityEvent
from places.models import HalalPlace
from io import StringIO
from unittest.mock import patch

User = get_user_model()


class AggregateMetricsCommandTests(TestCase):
    """Test aggregate_metrics management command."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_aggregate_metrics_command_runs(self):
        """Test that aggregate_metrics command runs successfully."""
        # Create some request logs
        now = timezone.now()
        for i in range(10):
            RequestLog.objects.create(
                path='/test/',
                method='GET',
                status_code=200,
                response_time_ms=100 + i * 10,
                ip_hash='test',
                timestamp=now
            )
        
        out = StringIO()
        call_command('aggregate_metrics', stdout=out)
        
        output = out.getvalue()
        self.assertIn('aggregation', output.lower())
    
    def test_aggregate_metrics_creates_system_metrics(self):
        """Test that aggregation creates system metrics."""
        # Create request logs
        now = timezone.now()
        for i in range(5):
            RequestLog.objects.create(
                path='/test/', method='GET', status_code=200,
                response_time_ms=100, ip_hash='test', timestamp=now
            )
        
        initial_count = SystemMetric.objects.count()
        
        call_command('aggregate_metrics', '--hours', '1', stdout=StringIO())
        
        # Should have created metrics
        self.assertGreater(SystemMetric.objects.count(), initial_count)
    
    def test_aggregate_metrics_with_cleanup(self):
        """Test aggregate_metrics with cleanup option."""
        # Create old request logs
        old_time = timezone.now() - timezone.timedelta(days=60)
        RequestLog.objects.create(
            path='/old/', method='GET', status_code=200,
            response_time_ms=100, ip_hash='test', user_agent_hash='test',
            timestamp=old_time
        )
        
        out = StringIO()
        call_command('aggregate_metrics', '--cleanup', stdout=out)
        
        output = out.getvalue()
        # Should mention cleanup
        self.assertTrue('cleanup' in output.lower() or 'cleaned' in output.lower() or 'old logs' in output.lower())
    
    def test_aggregate_metrics_with_no_logs(self):
        """Test aggregate_metrics with no logs to process."""
        out = StringIO()
        call_command('aggregate_metrics', stdout=out)
        
        output = out.getvalue()
        # Should handle gracefully
        self.assertIn('0', output)


class CheckAlertsCommandTests(TestCase):
    """Test check_alerts management command."""
    
    def test_check_alerts_command_runs(self):
        """Test that check_alerts command runs successfully."""
        out = StringIO()
        call_command('check_alerts', stdout=out)
        
        # Should complete without error
        self.assertEqual(out.getvalue(), '')  # Quiet mode by default
    
    def test_check_alerts_verbose_mode(self):
        """Test check_alerts in verbose mode."""
        out = StringIO()
        call_command('check_alerts', '--verbose', stdout=out)
        
        output = out.getvalue()
        self.assertIn('alert', output.lower())
    
    def test_check_alerts_with_triggerable_rule(self):
        """Test check_alerts with a rule that triggers."""
        # Create alert rule
        AlertRule.objects.create(
            name='Test Alert',
            condition='error_rate_above',
            threshold=10.0,
            window_minutes=10,
            alert_channels=['in_app'],
            enabled=True
        )
        
        # Create logs that trigger the alert (50% error rate)
        now = timezone.now()
        for i in range(10):
            RequestLog.objects.create(
                path='/test/', method='GET', status_code=500,
                response_time_ms=100, ip_hash='test', timestamp=now
            )
        for i in range(10):
            RequestLog.objects.create(
                path='/test/', method='GET', status_code=200,
                response_time_ms=100, ip_hash='test', timestamp=now
            )
        
        out = StringIO()
        call_command('check_alerts', '--verbose', stdout=out)
        
        output = out.getvalue()
        # Should mention triggered alert
        self.assertTrue('triggered' in output.lower() or 'alert' in output.lower())


class CheckMonitoringHealthCommandTests(TestCase):
    """Test check_monitoring_health management command."""
    
    def test_check_monitoring_health_command_runs(self):
        """Test that check_monitoring_health command runs successfully."""
        out = StringIO()
        call_command('check_monitoring_health', stdout=out)
        
        output = out.getvalue()
        self.assertIn('health', output.lower())
    
    def test_check_monitoring_health_with_recent_metrics(self):
        """Test health check with recent metrics."""
        # Create recent request log
        RequestLog.objects.create(
            path='/test/', method='GET', status_code=200,
            response_time_ms=100, ip_hash='test', user_agent_hash='test',
            timestamp=timezone.now()
        )
        
        out = StringIO()
        call_command('check_monitoring_health', stdout=out)
        
        output = out.getvalue()
        # Should indicate healthy or show some health status
        self.assertTrue('health' in output.lower())


class SendDailyDigestCommandTests(TestCase):
    """Test send_daily_digest management command."""
    
    @override_settings(ALERT_EMAIL_ENABLED=False)
    def test_send_daily_digest_disabled(self):
        """Test send_daily_digest when email alerts are disabled."""
        out = StringIO()
        call_command('send_daily_digest', stdout=out)
        
        output = out.getvalue()
        # Should indicate disabled or not sent
        self.assertTrue('disabled' in output.lower() or 'not' in output.lower())
    
    @override_settings(ALERT_EMAIL_ENABLED=True, ALERT_EMAIL_RECIPIENTS=['test@example.com'])
    def test_send_daily_digest_with_recipients(self):
        """Test that command runs with recipients configured."""
        out = StringIO()
        call_command('send_daily_digest', stdout=out)
        
        output = out.getvalue()
        # Should attempt to send or complete
        self.assertTrue(len(output) > 0)


class CommandIntegrationTests(TestCase):
    """Integration tests for commands working together."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            is_staff=True
        )
    
    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        # 1. Create request logs
        now = timezone.now()
        for i in range(5):
            RequestLog.objects.create(
                path='/test/', method='GET', status_code=200,
                response_time_ms=100, ip_hash='test', user_agent_hash='test',
                timestamp=now
            )
        
        # 2. Aggregate metrics
        call_command('aggregate_metrics', stdout=StringIO())
        
        # Should have created metrics
        self.assertGreater(SystemMetric.objects.count(), 0)
        
        # 3. Check alerts
        call_command('check_alerts', stdout=StringIO())
        
        # Should complete without error
        self.assertTrue(True)
    
    def test_commands_handle_empty_database(self):
        """Test that commands handle empty database gracefully."""
        # Commands should work with no data
        call_command('aggregate_metrics', stdout=StringIO())
        call_command('check_alerts', stdout=StringIO())
        call_command('check_monitoring_health', stdout=StringIO())
        
        # Should complete without errors
        self.assertTrue(True)

