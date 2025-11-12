"""
Alert rules engine and AlertManager for monitoring system.
"""
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.conf import settings
from utils.models import (
    AlertRule, RequestLog, SecurityEvent, AdminNotification,
    SystemMetric
)
from places.models import HalalPlace, PlaceEditSuggestion, PlaceImageSuggestion
from contact.models import ContactMessage
import logging

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manages alert rules evaluation and notification triggering.
    """
    
    def __init__(self):
        self.alert_handlers = {
            'error_rate_above': self._check_error_rate,
            'response_time_above': self._check_response_time,
            'queue_age_above': self._check_queue_age,
            'failed_login_spike': self._check_failed_login_spike,
            'db_slow_queries': self._check_slow_queries,
            'cache_hit_rate_below': self._check_cache_hit_rate,
            'api_failure': self._check_api_failure,
        }
    
    def check_all_rules(self):
        """
        Check all enabled alert rules and trigger alerts as needed.
        Returns count of triggered alerts.
        """
        triggered_count = 0
        
        # Get all enabled rules
        rules = AlertRule.objects.filter(enabled=True)
        
        logger.info(f"Checking {rules.count()} enabled alert rules...")
        
        for rule in rules:
            try:
                if self._evaluate_rule(rule):
                    triggered_count += 1
            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.name}': {e}", exc_info=True)
        
        logger.info(f"Alert check complete. {triggered_count} alert(s) triggered.")
        return triggered_count
    
    def _evaluate_rule(self, rule):
        """
        Evaluate a single alert rule.
        Returns True if alert was triggered.
        """
        # Check if rule can trigger (cooldown period)
        if not rule.can_trigger():
            logger.debug(f"Rule '{rule.name}' is in cooldown period")
            return False
        
        # Get the appropriate handler for this condition
        handler = self.alert_handlers.get(rule.condition)
        if not handler:
            logger.warning(f"No handler found for condition: {rule.condition}")
            return False
        
        # Evaluate the condition
        is_triggered, context = handler(rule)
        
        if is_triggered:
            logger.warning(f"Alert triggered: {rule.name}")
            self._trigger_alert(rule, context)
            rule.record_trigger()
            return True
        
        return False
    
    def _trigger_alert(self, rule, context):
        """
        Send alert notifications through configured channels.
        """
        channels = rule.alert_channels if isinstance(rule.alert_channels, list) else []
        
        # Format alert message
        message = self._format_alert_message(rule, context)
        
        # Send through each channel
        for channel in channels:
            try:
                if channel == 'telegram':
                    self._send_telegram_alert(rule, message, context)
                elif channel == 'email':
                    self._send_email_alert(rule, message, context)
                elif channel == 'in_app':
                    self._send_in_app_alert(rule, message, context)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}", exc_info=True)
    
    def _format_alert_message(self, rule, context):
        """Format alert message with context data."""
        message = f"**{rule.name}**\n\n"
        message += f"Condition: {rule.get_condition_display()}\n"
        message += f"Threshold: {rule.threshold}\n\n"
        
        if context:
            message += "Details:\n"
            for key, value in context.items():
                message += f"• {key}: {value}\n"
        
        return message
    
    def _send_telegram_alert(self, rule, message, context):
        """Send alert via Telegram."""
        if not getattr(settings, 'ALERT_TELEGRAM_ENABLED', False):
            return
        
        try:
            from utils.telegram_notifications import send_telegram_message
            
            # Add severity emoji
            severity_emoji = {
                'low': 'ℹ️',
                'medium': '⚠️',
                'high': '🔴',
                'critical': '🚨'
            }
            emoji = severity_emoji.get(context.get('severity', 'medium'), '⚠️')
            
            telegram_message = f"{emoji} *ALERT*\n\n{message}"
            send_telegram_message(telegram_message)
            logger.info(f"Telegram alert sent for rule: {rule.name}")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}", exc_info=True)
    
    def _send_email_alert(self, rule, message, context):
        """Send alert via email."""
        if not getattr(settings, 'ALERT_EMAIL_ENABLED', False):
            return
        
        try:
            from django.core.mail import send_mail
            
            recipients = getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
            if not recipients:
                logger.warning("No email recipients configured for alerts")
                return
            
            subject = f"[Halal Korea Alert] {rule.name}"
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
            logger.info(f"Email alert sent for rule: {rule.name}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}", exc_info=True)
    
    def _send_in_app_alert(self, rule, message, context):
        """Send in-app notification to admins."""
        try:
            severity = context.get('severity', 'warning')
            link = context.get('link', '/admin/monitoring/')
            
            AdminNotification.objects.create(
                recipient=None,  # All admins
                title=f"🚨 {rule.name}",
                message=message,
                severity=severity,
                link=link
            )
            logger.info(f"In-app notification created for rule: {rule.name}")
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {e}", exc_info=True)
    
    # ========================================================================
    # Alert Condition Handlers
    # ========================================================================
    
    def _check_error_rate(self, rule):
        """Check if error rate exceeds threshold."""
        window_start = timezone.now() - timezone.timedelta(minutes=rule.window_minutes)
        
        total_requests = RequestLog.objects.filter(timestamp__gte=window_start).count()
        error_requests = RequestLog.objects.filter(
            timestamp__gte=window_start,
            status_code__gte=500
        ).count()
        
        if total_requests == 0:
            return False, {}
        
        error_rate = (error_requests / total_requests) * 100
        
        if error_rate > rule.threshold:
            context = {
                'error_rate': f"{error_rate:.2f}%",
                'error_count': error_requests,
                'total_requests': total_requests,
                'window_minutes': rule.window_minutes,
                'severity': 'critical' if error_rate > rule.threshold * 2 else 'high',
                'link': '/admin/utils/requestlog/?status_code__gte=500'
            }
            return True, context
        
        return False, {}
    
    def _check_response_time(self, rule):
        """Check if average response time exceeds threshold."""
        window_start = timezone.now() - timezone.timedelta(minutes=rule.window_minutes)
        
        avg_response = RequestLog.objects.filter(
            timestamp__gte=window_start
        ).aggregate(avg_time=Avg('response_time_ms'))
        
        avg_time = avg_response['avg_time']
        
        if avg_time and avg_time > rule.threshold:
            context = {
                'avg_response_time': f"{avg_time:.0f}ms",
                'threshold': f"{rule.threshold}ms",
                'window_minutes': rule.window_minutes,
                'severity': 'high' if avg_time > rule.threshold * 1.5 else 'medium',
                'link': '/admin/monitoring/performance/'
            }
            return True, context
        
        return False, {}
    
    def _check_queue_age(self, rule):
        """Check if oldest pending item exceeds age threshold (in hours)."""
        threshold_hours = rule.threshold
        cutoff_time = timezone.now() - timezone.timedelta(hours=threshold_hours)
        
        # Check various pending queues
        old_places = HalalPlace.objects.filter(
            status='pending',
            created_at__lt=cutoff_time
        ).count()
        
        old_suggestions = PlaceEditSuggestion.objects.filter(
            status='pending',
            created_at__lt=cutoff_time
        ).count()
        
        old_images = PlaceImageSuggestion.objects.filter(
            status='pending',
            created_at__lt=cutoff_time
        ).count()
        
        old_contacts = ContactMessage.objects.filter(
            is_read=False,
            created_at__lt=cutoff_time
        ).count()
        
        total_old = old_places + old_suggestions + old_images + old_contacts
        
        if total_old > 0:
            context = {
                'old_items': total_old,
                'places': old_places,
                'suggestions': old_suggestions,
                'images': old_images,
                'contacts': old_contacts,
                'threshold_hours': threshold_hours,
                'severity': 'medium',
                'link': '/admin/monitoring/content/'
            }
            return True, context
        
        return False, {}
    
    def _check_failed_login_spike(self, rule):
        """Check for spike in failed login attempts."""
        window_start = timezone.now() - timezone.timedelta(minutes=rule.window_minutes)
        
        failed_logins = SecurityEvent.objects.filter(
            event_type='failed_login',
            timestamp__gte=window_start
        ).count()
        
        if failed_logins > rule.threshold:
            context = {
                'failed_attempts': failed_logins,
                'threshold': int(rule.threshold),
                'window_minutes': rule.window_minutes,
                'severity': 'high',
                'link': '/admin/monitoring/security/'
            }
            return True, context
        
        return False, {}
    
    def _check_slow_queries(self, rule):
        """Check if average database queries per request exceeds threshold."""
        window_start = timezone.now() - timezone.timedelta(minutes=rule.window_minutes)
        
        avg_queries = RequestLog.objects.filter(
            timestamp__gte=window_start
        ).aggregate(avg=Avg('db_query_count'))
        
        avg_count = avg_queries['avg']
        
        if avg_count and avg_count > rule.threshold:
            context = {
                'avg_queries': f"{avg_count:.1f}",
                'threshold': int(rule.threshold),
                'window_minutes': rule.window_minutes,
                'severity': 'medium',
                'link': '/admin/monitoring/performance/'
            }
            return True, context
        
        return False, {}
    
    def _check_cache_hit_rate(self, rule):
        """Check if cache hit rate falls below threshold."""
        window_start = timezone.now() - timezone.timedelta(minutes=rule.window_minutes)
        
        cache_data = RequestLog.objects.filter(
            timestamp__gte=window_start
        ).aggregate(
            total_hits=Count('id', filter=Q(cache_hits__gt=0)),
            total_misses=Count('id', filter=Q(cache_misses__gt=0))
        )
        
        total_ops = cache_data['total_hits'] + cache_data['total_misses']
        
        if total_ops == 0:
            return False, {}
        
        hit_rate = (cache_data['total_hits'] / total_ops) * 100
        
        if hit_rate < rule.threshold:
            context = {
                'hit_rate': f"{hit_rate:.1f}%",
                'threshold': f"{rule.threshold}%",
                'hits': cache_data['total_hits'],
                'misses': cache_data['total_misses'],
                'severity': 'low',
                'link': '/admin/monitoring/performance/'
            }
            return True, context
        
        return False, {}
    
    def _check_api_failure(self, rule):
        """Check for external API failures."""
        window_start = timezone.now() - timezone.timedelta(minutes=rule.window_minutes)
        
        # Check for API-related errors in request logs
        api_errors = RequestLog.objects.filter(
            timestamp__gte=window_start,
            error_type__icontains='api'
        ).count()
        
        if api_errors > rule.threshold:
            context = {
                'api_errors': api_errors,
                'threshold': int(rule.threshold),
                'window_minutes': rule.window_minutes,
                'severity': 'high',
                'link': '/admin/utils/requestlog/'
            }
            return True, context
        
        return False, {}


# Convenience function for manual alert checking
def check_alerts():
    """
    Check all alert rules and trigger notifications.
    Can be called from management command or scheduled task.
    """
    manager = AlertManager()
    return manager.check_all_rules()

