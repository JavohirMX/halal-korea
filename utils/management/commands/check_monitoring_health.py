"""
Management command to check monitoring system health and detect anomalies.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Avg
from utils.models import RequestLog, SystemMetric, AdminNotification
from utils.telegram_notifications import send_telegram_message
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check monitoring system health and detect anomalies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--alert',
            action='store_true',
            help='Send alerts if issues are detected'
        )
    
    def handle(self, *args, **options):
        send_alerts = options['alert']
        
        self.stdout.write(self.style.SUCCESS('Checking monitoring system health...'))
        
        issues = []
        
        # Check 1: Verify recent metrics exist
        if not self._check_recent_metrics():
            issues.append('No metrics recorded in the last hour')
        
        # Check 2: Check for error spikes
        error_spike = self._check_error_spike()
        if error_spike:
            issues.append(f'Error spike detected: {error_spike}')
        
        # Check 3: Check for traffic drops
        traffic_drop = self._check_traffic_drop()
        if traffic_drop:
            issues.append(f'Traffic drop detected: {traffic_drop}')
        
        # Check 4: Check for slow performance
        slow_performance = self._check_slow_performance()
        if slow_performance:
            issues.append(f'Slow performance detected: {slow_performance}')
        
        # Report results
        if issues:
            self.stdout.write(self.style.ERROR(f'⚠️  {len(issues)} issue(s) detected:'))
            for issue in issues:
                self.stdout.write(self.style.WARNING(f'  - {issue}'))
            
            if send_alerts:
                self._send_health_alert(issues)
        else:
            self.stdout.write(self.style.SUCCESS('✓ Monitoring system is healthy'))
    
    def _check_recent_metrics(self):
        """Check if metrics have been recorded recently."""
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        recent_logs = RequestLog.objects.filter(timestamp__gte=one_hour_ago).exists()
        
        if recent_logs:
            self.stdout.write('  ✓ Recent metrics found')
            return True
        else:
            self.stdout.write(self.style.WARNING('  ✗ No recent metrics (last hour)'))
            return False
    
    def _check_error_spike(self):
        """Check for unusual error rates."""
        now = timezone.now()
        last_hour = now - timezone.timedelta(hours=1)
        last_day = now - timezone.timedelta(days=1)
        
        # Get error count for last hour
        recent_errors = RequestLog.objects.filter(
            timestamp__gte=last_hour,
            status_code__gte=500
        ).count()
        
        # Get average error count per hour for last day
        daily_errors = RequestLog.objects.filter(
            timestamp__gte=last_day,
            status_code__gte=500
        ).count()
        avg_errors_per_hour = daily_errors / 24 if daily_errors > 0 else 0
        
        # Alert if recent errors are 3x the average
        if avg_errors_per_hour > 0 and recent_errors > (avg_errors_per_hour * 3):
            message = f'{recent_errors} errors in last hour (avg: {avg_errors_per_hour:.1f}/hour)'
            self.stdout.write(self.style.WARNING(f'  ✗ Error spike: {message}'))
            return message
        
        self.stdout.write('  ✓ Error rate normal')
        return None
    
    def _check_traffic_drop(self):
        """Check for unusual traffic drops."""
        now = timezone.now()
        last_hour = now - timezone.timedelta(hours=1)
        previous_hour = last_hour - timezone.timedelta(hours=1)
        
        # Get request counts
        recent_requests = RequestLog.objects.filter(
            timestamp__gte=last_hour
        ).count()
        
        previous_requests = RequestLog.objects.filter(
            timestamp__gte=previous_hour,
            timestamp__lt=last_hour
        ).count()
        
        # Alert if traffic dropped by more than 50%
        if previous_requests > 10 and recent_requests < (previous_requests * 0.5):
            message = f'{recent_requests} requests (was {previous_requests} previous hour)'
            self.stdout.write(self.style.WARNING(f'  ✗ Traffic drop: {message}'))
            return message
        
        self.stdout.write('  ✓ Traffic levels normal')
        return None
    
    def _check_slow_performance(self):
        """Check for slow response times."""
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        
        avg_response = RequestLog.objects.filter(
            timestamp__gte=one_hour_ago
        ).aggregate(avg_time=Avg('response_time_ms'))
        
        avg_time = avg_response['avg_time']
        
        if avg_time and avg_time > 2000:  # 2 seconds
            message = f'Average response time: {avg_time:.0f}ms'
            self.stdout.write(self.style.WARNING(f'  ✗ Slow performance: {message}'))
            return message
        
        self.stdout.write('  ✓ Performance normal')
        return None
    
    def _send_health_alert(self, issues):
        """Send alert notifications about health issues."""
        try:
            # Create admin notification
            AdminNotification.objects.create(
                recipient=None,  # All admins
                title='🚨 Monitoring System Health Alert',
                message=f'{len(issues)} issue(s) detected:\n' + '\n'.join(f'• {issue}' for issue in issues),
                severity='critical',
                link='/admin/monitoring/'
            )
            
            # Send Telegram alert if enabled
            try:
                from django.conf import settings
                if getattr(settings, 'TELEGRAM_NOTIFICATIONS_ENABLED', False):
                    message = f"🚨 *Monitoring Health Alert*\n\n"
                    message += f"{len(issues)} issue(s) detected:\n"
                    for issue in issues:
                        message += f"• {issue}\n"
                    send_telegram_message(message)
                    self.stdout.write('  ✓ Telegram alert sent')
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")
            
            self.stdout.write(self.style.SUCCESS('  ✓ Health alerts sent'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Failed to send alerts: {e}'))
            logger.error(f"Failed to send health alerts: {e}", exc_info=True)

