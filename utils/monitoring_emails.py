"""
Email notifications for monitoring system.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Q
from datetime import timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def send_daily_digest():
    """
    Send daily digest email to admins.
    Returns True if sent successfully, False otherwise.
    """
    if not getattr(settings, 'ALERT_EMAIL_ENABLED', False):
        logger.info("Email alerts disabled, skipping daily digest")
        return False
    
    recipients = getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
    if not recipients:
        logger.warning("No email recipients configured for daily digest")
        return False
    
    try:
        # Get yesterday's stats
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        stats = _gather_daily_stats(yesterday, today)
        
        # Format email
        subject = f"Halal Korea - Daily Monitoring Digest ({yesterday.strftime('%Y-%m-%d')})"
        message = _format_digest_text(stats, yesterday)
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@halal-korea.com'),
            recipient_list=recipients,
            fail_silently=False
        )
        
        logger.info(f"Daily digest sent to {len(recipients)} recipients")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send daily digest: {e}")
        return False


def send_critical_alert(title: str, message: str, details: Dict[str, Any] = None, link: str = None):
    """
    Send critical alert email to admins.
    
    Args:
        title: Alert title
        message: Alert message
        details: Optional dictionary of additional details
        link: Optional link to relevant page
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not getattr(settings, 'ALERT_EMAIL_ENABLED', False):
        return False
    
    recipients = getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
    if not recipients:
        return False
    
    try:
        subject = f"🚨 CRITICAL ALERT: {title}"
        
        # Format message
        email_body = f"""
CRITICAL ALERT
{'=' * 60}

{message}

"""
        
        if details:
            email_body += "\nDETAILS:\n"
            email_body += "-" * 60 + "\n"
            for key, value in details.items():
                email_body += f"{key}: {value}\n"
        
        if link:
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            full_link = f"{site_url}{link}" if link.startswith('/') else link
            email_body += f"\nView Details: {full_link}\n"
        
        email_body += "\n" + "=" * 60 + "\n"
        email_body += f"Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        email_body += "Halal Korea Monitoring System\n"
        
        send_mail(
            subject=subject,
            message=email_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@halal-korea.com'),
            recipient_list=recipients,
            fail_silently=False
        )
        
        logger.info(f"Critical alert sent: {title}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send critical alert: {e}")
        return False


def _gather_daily_stats(start_time, end_time):
    """
    Gather statistics for a time period (typically one day).
    
    Args:
        start_time: Start of time period
        end_time: End of time period
    
    Returns:
        Dictionary with statistics
    """
    from utils.models import RequestLog, SecurityEvent, AdminAction, ContentModerationLog
    from places.models import HalalPlace, PlaceEditSuggestion, PlaceImageSuggestion
    from reviews.models import Review
    from contact.models import ContactMessage
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Request statistics
    requests = RequestLog.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time
    )
    
    total_requests = requests.count()
    error_requests = requests.filter(status_code__gte=400)
    errors = error_requests.count()
    error_rate = (errors / total_requests * 100) if total_requests > 0 else 0
    
    avg_response_time_result = requests.aggregate(avg=Avg('response_time_ms'))
    avg_response_time = avg_response_time_result['avg'] or 0
    
    # Security events
    security_events = SecurityEvent.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time
    )
    
    security_by_type = {}
    for event in security_events.values('event_type').annotate(count=Count('id')):
        security_by_type[event['event_type']] = event['count']
    
    # Content statistics
    new_places = HalalPlace.objects.filter(
        created_at__gte=start_time,
        created_at__lt=end_time
    ).count()
    
    approved_places = HalalPlace.objects.filter(
        updated_at__gte=start_time,
        updated_at__lt=end_time,
        status='approved'
    ).count()
    
    pending_places = HalalPlace.objects.filter(status='pending').count()
    pending_suggestions = PlaceEditSuggestion.objects.filter(status='pending').count()
    pending_image_suggestions = PlaceImageSuggestion.objects.filter(status='pending').count()
    
    unread_contacts = ContactMessage.objects.filter(
        is_read=False
    ).count()
    
    # Admin actions
    admin_actions = AdminAction.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time
    )
    
    actions_by_type = {}
    for action in admin_actions.values('action_type').annotate(count=Count('id')):
        actions_by_type[action['action_type']] = action['count']
    
    # User statistics
    new_users = User.objects.filter(
        date_joined__gte=start_time,
        date_joined__lt=end_time
    ).count()
    
    active_users = RequestLog.objects.filter(
        timestamp__gte=start_time,
        timestamp__lt=end_time,
        user__isnull=False
    ).values('user').distinct().count()
    
    return {
        'requests': {
            'total': total_requests,
            'errors': errors,
            'error_rate': round(error_rate, 2),
            'avg_response_time': round(avg_response_time, 2)
        },
        'security': {
            'total': security_events.count(),
            'unresolved': security_events.filter(resolved=False).count(),
            'by_type': security_by_type
        },
        'content': {
            'new_places': new_places,
            'approved_places': approved_places,
            'pending_places': pending_places,
            'pending_suggestions': pending_suggestions + pending_image_suggestions,
            'unread_contacts': unread_contacts
        },
        'admin_actions': {
            'total': admin_actions.count(),
            'by_type': actions_by_type
        },
        'users': {
            'new_users': new_users,
            'active_users': active_users
        }
    }


def _format_digest_text(stats: Dict[str, Any], date):
    """
    Format statistics into readable email text.
    
    Args:
        stats: Statistics dictionary from _gather_daily_stats
        date: Date for the report
    
    Returns:
        Formatted email text
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"HALAL KOREA - DAILY MONITORING DIGEST")
    lines.append(f"Date: {date.strftime('%A, %B %d, %Y')}")
    lines.append("=" * 70)
    lines.append("")
    
    # Request Statistics
    lines.append("📊 REQUEST STATISTICS")
    lines.append("-" * 70)
    lines.append(f"Total Requests:      {stats['requests']['total']:,}")
    lines.append(f"Errors:              {stats['requests']['errors']:,}")
    lines.append(f"Error Rate:          {stats['requests']['error_rate']}%")
    lines.append(f"Avg Response Time:   {stats['requests']['avg_response_time']:.2f} ms")
    lines.append("")
    
    # Security Events
    lines.append("🔒 SECURITY EVENTS")
    lines.append("-" * 70)
    lines.append(f"Total Events:        {stats['security']['total']}")
    lines.append(f"Unresolved:          {stats['security']['unresolved']}")
    
    if stats['security']['by_type']:
        lines.append("\nBy Type:")
        for event_type, count in sorted(stats['security']['by_type'].items()):
            lines.append(f"  - {event_type}: {count}")
    else:
        lines.append("  (No security events)")
    lines.append("")
    
    # Content Statistics
    lines.append("📝 CONTENT STATISTICS")
    lines.append("-" * 70)
    lines.append(f"New Places:          {stats['content']['new_places']}")
    lines.append(f"Approved Places:     {stats['content']['approved_places']}")
    lines.append(f"Pending Places:      {stats['content']['pending_places']}")
    lines.append(f"Pending Suggestions: {stats['content']['pending_suggestions']}")
    lines.append(f"Unread Contacts:     {stats['content']['unread_contacts']}")
    lines.append("")
    
    # Admin Activity
    lines.append("👤 ADMIN ACTIVITY")
    lines.append("-" * 70)
    lines.append(f"Total Actions:       {stats['admin_actions']['total']}")
    
    if stats['admin_actions']['by_type']:
        lines.append("\nBy Type:")
        for action_type, count in sorted(stats['admin_actions']['by_type'].items()):
            lines.append(f"  - {action_type}: {count}")
    else:
        lines.append("  (No admin actions)")
    lines.append("")
    
    # User Statistics
    lines.append("👥 USER STATISTICS")
    lines.append("-" * 70)
    lines.append(f"New Users:           {stats['users']['new_users']}")
    lines.append(f"Active Users:        {stats['users']['active_users']}")
    lines.append("")
    
    # Footer
    lines.append("=" * 70)
    lines.append("This is an automated daily digest from Halal Korea Monitoring System")
    lines.append(f"Generated at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append("=" * 70)
    
    return "\n".join(lines)
