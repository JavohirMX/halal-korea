"""
Management command to check monitoring system health.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from utils.models import RequestLog, SecurityEvent, SystemMetric, AlertRule
from utils.monitoring_emails import send_critical_alert
from utils.telegram_notifications import send_telegram_notification


# Default thresholds from settings (can be overridden via AlertRules)
DEFAULT_THRESHOLDS = {
    'health_min_requests': getattr(settings, 'MONITORING_HEALTH_MIN_REQUESTS', 10),
    'health_error_rate_warning': getattr(settings, 'MONITORING_HEALTH_ERROR_RATE_WARNING', 5.0),
    'health_error_rate_critical': getattr(settings, 'MONITORING_HEALTH_ERROR_RATE_CRITICAL', 10.0),
    'health_response_time_warning': getattr(settings, 'MONITORING_HEALTH_RESPONSE_TIME_WARNING', 2000),
    'health_security_events_warning': getattr(settings, 'MONITORING_HEALTH_SECURITY_EVENTS_WARNING', 5),
}


def get_health_threshold(condition):
    """
    Get threshold value from AlertRule if configured, otherwise use settings default.
    Health thresholds can be configured in AlertRule or settings.py.
    """
    try:
        rule = AlertRule.objects.filter(condition=condition, enabled=True).first()
        if rule:
            return rule.threshold
    except Exception:
        pass
    return DEFAULT_THRESHOLDS.get(condition, 0)


class Command(BaseCommand):
    help = 'Check monitoring system health and detect issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--alert',
            action='store_true',
            help='Send alerts if issues are detected',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Hours to look back for health check (default: 1)',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        alert_on_issues = options['alert']
        hours = options['hours']
        
        self.stdout.write(self.style.WARNING(f'Checking monitoring system health (last {hours} hour(s))...'))
        self.stdout.write('')
        
        issues = []
        warnings = []
        
        # Check 1: Recent request logs
        recent_logs_check = self._check_recent_logs(hours)
        if recent_logs_check['status'] == 'error':
            issues.append(recent_logs_check['message'])
        elif recent_logs_check['status'] == 'warning':
            warnings.append(recent_logs_check['message'])
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ {recent_logs_check['message']}"))
        
        # Check 2: Error rate
        error_rate_check = self._check_error_rate(hours)
        if error_rate_check['status'] == 'error':
            issues.append(error_rate_check['message'])
        elif error_rate_check['status'] == 'warning':
            warnings.append(error_rate_check['message'])
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ {error_rate_check['message']}"))
        
        # Check 3: Unresolved security events
        security_check = self._check_security_events()
        if security_check['status'] == 'warning':
            warnings.append(security_check['message'])
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ {security_check['message']}"))
        
        # Check 4: System metrics freshness
        metrics_check = self._check_metrics_freshness(hours)
        if metrics_check['status'] == 'warning':
            warnings.append(metrics_check['message'])
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ {metrics_check['message']}"))
        
        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 70)
        
        if issues:
            self.stdout.write(self.style.ERROR(f'❌ CRITICAL ISSUES DETECTED: {len(issues)}'))
            for issue in issues:
                self.stdout.write(self.style.ERROR(f'  - {issue}'))
            
            if alert_on_issues:
                self._send_health_alert('critical', issues)
        
        if warnings:
            self.stdout.write(self.style.WARNING(f'⚠️  WARNINGS: {len(warnings)}'))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f'  - {warning}'))
            
            if alert_on_issues:
                self._send_health_alert('warning', warnings)
        
        if not issues and not warnings:
            self.stdout.write(self.style.SUCCESS('✓ All health checks passed - System healthy'))
        
        self.stdout.write('=' * 70)
    
    def _check_recent_logs(self, hours):
        """Check if there are recent request logs."""
        cutoff = timezone.now() - timedelta(hours=hours)
        recent_count = RequestLog.objects.filter(timestamp__gte=cutoff).count()
        
        min_logs = int(get_health_threshold('health_min_requests'))
        
        if recent_count == 0:
            return {
                'status': 'error',
                'message': f'No request logs in the last {hours} hour(s) - Monitoring may be disabled'
            }
        elif recent_count < min_logs:
            return {
                'status': 'warning',
                'message': f'Very few request logs ({recent_count}) in the last {hours} hour(s)'
            }
        else:
            return {
                'status': 'ok',
                'message': f'Request logging active ({recent_count:,} logs in last {hours} hour(s))'
            }
    
    def _check_error_rate(self, hours):
        """Check error rate in recent requests."""
        cutoff = timezone.now() - timedelta(hours=hours)
        recent_logs = RequestLog.objects.filter(timestamp__gte=cutoff)
        
        total = recent_logs.count()
        if total == 0:
            return {'status': 'ok', 'message': 'No requests to check error rate'}
        
        errors = recent_logs.filter(status_code__gte=500).count()
        error_rate = (errors / total) * 100
        
        critical_threshold = get_health_threshold('health_error_rate_critical')
        warning_threshold = get_health_threshold('health_error_rate_warning')
        
        if error_rate > critical_threshold:
            return {
                'status': 'error',
                'message': f'High error rate: {error_rate:.1f}% ({errors}/{total} requests)'
            }
        elif error_rate > warning_threshold:
            return {
                'status': 'warning',
                'message': f'Elevated error rate: {error_rate:.1f}% ({errors}/{total} requests)'
            }
        else:
            return {
                'status': 'ok',
                'message': f'Error rate normal: {error_rate:.1f}% ({errors}/{total} requests)'
            }
    
    def _check_security_events(self):
        """Check for unresolved security events."""
        unresolved = SecurityEvent.objects.filter(resolved=False)
        critical_unresolved = unresolved.filter(severity='critical').count()
        high_unresolved = unresolved.filter(severity='high').count()
        
        high_events_threshold = int(get_health_threshold('health_security_events_warning'))
        
        if critical_unresolved > 0:
            return {
                'status': 'error',
                'message': f'{critical_unresolved} critical security event(s) unresolved'
            }
        elif high_unresolved > high_events_threshold:
            return {
                'status': 'warning',
                'message': f'{high_unresolved} high-severity security event(s) unresolved'
            }
        else:
            total_unresolved = unresolved.count()
            return {
                'status': 'ok',
                'message': f'Security events: {total_unresolved} unresolved (none critical)'
            }
    
    def _check_metrics_freshness(self, hours):
        """Check if metrics are being aggregated regularly."""
        cutoff = timezone.now() - timedelta(hours=hours * 2)  # Check last 2x hours
        recent_metrics = SystemMetric.objects.filter(timestamp__gte=cutoff).count()
        
        if recent_metrics == 0:
            return {
                'status': 'warning',
                'message': 'No recent system metrics - Run aggregate_metrics command'
            }
        else:
            return {
                'status': 'ok',
                'message': f'System metrics up to date ({recent_metrics} recent metrics)'
            }
    
    def _send_health_alert(self, severity, messages):
        """Send health alert via configured channels."""
        if severity == 'critical':
            title = 'Monitoring System Health: CRITICAL ISSUES'
            emoji = '🚨'
        else:
            title = 'Monitoring System Health: Warnings'
            emoji = '⚠️'
        
        message_text = f"{emoji} {title}\n\n" + "\n".join(f"• {msg}" for msg in messages)
        
        # Send email if enabled
        if getattr(settings, 'ALERT_EMAIL_ENABLED', False):
            try:
                send_critical_alert(
                    title=title,
                    message="\n".join(messages),
                    link='/admin/monitoring/'
                )
                self.stdout.write('  → Alert email sent')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  → Failed to send email: {e}'))
        
        # Send Telegram if enabled
        if getattr(settings, 'ALERT_TELEGRAM_ENABLED', False):
            try:
                send_telegram_notification(message_text)
                self.stdout.write('  → Alert sent to Telegram')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  → Failed to send Telegram: {e}'))
