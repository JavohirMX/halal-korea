"""
Email alert system for monitoring notifications.
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Avg
from utils.models import RequestLog, SecurityEvent, AdminAction
from places.models import HalalPlace, PlaceEditSuggestion
from contact.models import ContactMessage
import logging

logger = logging.getLogger(__name__)


def send_daily_digest():
    """
    Send daily digest email to admins with yesterday's summary.
    Should be run once per day via cron.
    """
    if not getattr(settings, 'ALERT_EMAIL_ENABLED', False):
        logger.info("Email alerts are disabled")
        return False
    
    recipients = getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
    if not recipients:
        logger.warning("No email recipients configured for alerts")
        return False
    
    try:
        # Get yesterday's date range
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timezone.timedelta(days=1)
        
        # Gather statistics
        stats = _gather_daily_stats(yesterday, today)
        
        # Format email
        subject = f"[Halal Korea] Daily Monitoring Digest - {yesterday.strftime('%Y-%m-%d')}"
        
        # Plain text version
        text_content = _format_digest_text(stats, yesterday)
        
        # HTML version (optional, can be enhanced)
        html_content = _format_digest_html(stats, yesterday)
        
        # Send email
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients
        )
        
        if html_content:
            msg.attach_alternative(html_content, "text/html")
        
        msg.send(fail_silently=False)
        
        logger.info(f"Daily digest email sent to {len(recipients)} recipient(s)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send daily digest email: {e}", exc_info=True)
        return False


def send_critical_alert(title, message, details=None, link=None):
    """
    Send immediate critical alert email to admins.
    
    Args:
        title: Alert title
        message: Alert message
        details: Optional dict of additional details
        link: Optional link to relevant admin page
    """
    if not getattr(settings, 'ALERT_EMAIL_ENABLED', False):
        return False
    
    recipients = getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
    if not recipients:
        return False
    
    try:
        subject = f"[Halal Korea ALERT] {title}"
        
        email_body = f"""
CRITICAL ALERT

{title}

{message}
"""
        
        if details:
            email_body += "\n\nDetails:\n"
            for key, value in details.items():
                email_body += f"  • {key}: {value}\n"
        
        if link:
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            email_body += f"\n\nView in admin: {site_url}{link}"
        
        email_body += f"\n\nTime: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        send_mail(
            subject=subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        
        logger.info(f"Critical alert email sent: {title}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send critical alert email: {e}", exc_info=True)
        return False


def _gather_daily_stats(start_time, end_time):
    """Gather statistics for the daily digest."""
    stats = {}
    
    # Request statistics
    total_requests = RequestLog.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time
    ).count()
    
    error_requests = RequestLog.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time,
        status_code__gte=500
    ).count()
    
    avg_response = RequestLog.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time
    ).aggregate(avg=Avg('response_time_ms'))
    
    stats['requests'] = {
        'total': total_requests,
        'errors': error_requests,
        'error_rate': (error_requests / total_requests * 100) if total_requests > 0 else 0,
        'avg_response_time': avg_response['avg'] or 0,
    }
    
    # Security events
    security_events = SecurityEvent.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time
    ).values('event_type').annotate(count=Count('id'))
    
    stats['security'] = {
        'total': sum(e['count'] for e in security_events),
        'by_type': {e['event_type']: e['count'] for e in security_events},
        'unresolved': SecurityEvent.objects.filter(
            timestamp__gte=start_time,
            timestamp__lt=end_time,
            resolved=False
        ).count()
    }
    
    # Content statistics
    stats['content'] = {
        'new_places': HalalPlace.objects.filter(
            created_at__gte=start_time,
            created_at__lt=end_time
        ).count(),
        'approved_places': HalalPlace.objects.filter(
            updated_at__gte=start_time,
            updated_at__lt=end_time,
            status='approved'
        ).count(),
        'pending_places': HalalPlace.objects.filter(status='pending').count(),
        'pending_suggestions': PlaceEditSuggestion.objects.filter(status='pending').count(),
        'unread_contacts': ContactMessage.objects.filter(is_read=False).count(),
    }
    
    # Admin actions
    admin_actions = AdminAction.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time
    ).values('action_type').annotate(count=Count('id'))
    
    stats['admin_actions'] = {
        'total': sum(a['count'] for a in admin_actions),
        'by_type': {a['action_type']: a['count'] for a in admin_actions},
    }
    
    return stats


def _format_digest_text(stats, date):
    """Format daily digest as plain text."""
    text = f"""
HALAL KOREA DAILY MONITORING DIGEST
Date: {date.strftime('%Y-%m-%d')}
=====================================

REQUEST STATISTICS
------------------
Total Requests: {stats['requests']['total']:,}
Errors (5xx): {stats['requests']['errors']} ({stats['requests']['error_rate']:.2f}%)
Avg Response Time: {stats['requests']['avg_response_time']:.0f}ms

SECURITY EVENTS
---------------
Total Events: {stats['security']['total']}
Unresolved: {stats['security']['unresolved']}
"""
    
    if stats['security']['by_type']:
        text += "\nBy Type:\n"
        for event_type, count in stats['security']['by_type'].items():
            text += f"  • {event_type}: {count}\n"
    
    text += f"""
CONTENT STATISTICS
------------------
New Places Submitted: {stats['content']['new_places']}
Places Approved: {stats['content']['approved_places']}
Pending Places: {stats['content']['pending_places']}
Pending Suggestions: {stats['content']['pending_suggestions']}
Unread Contact Messages: {stats['content']['unread_contacts']}

ADMIN ACTIVITY
--------------
Total Actions: {stats['admin_actions']['total']}
"""
    
    if stats['admin_actions']['by_type']:
        text += "\nBy Type:\n"
        for action_type, count in stats['admin_actions']['by_type'].items():
            text += f"  • {action_type}: {count}\n"
    
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    text += f"\n\nView full dashboard: {site_url}/admin/monitoring/\n"
    
    return text


def _format_digest_html(stats, date):
    """Format daily digest as HTML (optional enhancement)."""
    # For now, return None to use plain text only
    # Can be enhanced later with proper HTML templates
    return None


def send_weekly_summary():
    """
    Send weekly summary email with trends and insights.
    Should be run once per week via cron.
    """
    # Placeholder for future implementation
    logger.info("Weekly summary email not yet implemented")
    return False

