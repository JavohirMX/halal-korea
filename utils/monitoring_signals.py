"""
Signal handlers for monitoring content moderation and security events.
"""
from django.db.models.signals import post_save, pre_save
from django.contrib.auth.signals import user_logged_in, user_login_failed, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from utils.models import (
    ContentModerationLog, SecurityEvent, SystemMetric, 
    AdminNotification, hash_ip
)
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Content Moderation Signals
# ============================================================================

@receiver(post_save, sender='places.HalalPlace')
def track_place_moderation(sender, instance, created, **kwargs):
    """Track place approval/rejection for moderation metrics."""
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    # Only log status changes (not creation)
    if not created and hasattr(instance, '_previous_status'):
        previous_status = instance._previous_status
        current_status = instance.status
        
        if previous_status != current_status and current_status in ['approved', 'rejected', 'archived']:
            try:
                # Calculate time in queue
                time_in_queue_hours = None
                if instance.created_at:
                    delta = timezone.now() - instance.created_at
                    time_in_queue_hours = delta.total_seconds() / 3600
                
                # Get moderator from request context (if available)
                moderator = getattr(instance, '_moderator', None)
                if not moderator and hasattr(instance, 'submitted_by'):
                    # Fallback: use a staff user if available
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    moderator = User.objects.filter(is_staff=True).first()
                
                if moderator:
                    ContentModerationLog.objects.create(
                        moderator=moderator,
                        content_type='place',
                        object_id=instance.pk,
                        action=current_status,
                        time_in_queue_hours=time_in_queue_hours
                    )
                    
                    # Update system metrics
                    SystemMetric.objects.create(
                        timestamp=timezone.now(),
                        metric_type='request_count',
                        metric_name='place_moderation',
                        value=1,
                        metadata={'action': current_status}
                    )
            except Exception as e:
                logger.error(f"Failed to log place moderation: {e}", exc_info=True)


@receiver(pre_save, sender='places.HalalPlace')
def store_previous_place_status(sender, instance, **kwargs):
    """Store previous status before save to detect changes."""
    if instance.pk:
        try:
            previous = sender.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except sender.DoesNotExist:
            instance._previous_status = None


@receiver(post_save, sender='places.PlaceEditSuggestion')
def track_suggestion_moderation(sender, instance, created, **kwargs):
    """Track edit suggestion approval/rejection."""
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    if not created and hasattr(instance, '_previous_status'):
        previous_status = instance._previous_status
        current_status = instance.status
        
        if previous_status != current_status and current_status in ['approved', 'rejected']:
            try:
                time_in_queue_hours = None
                if instance.created_at:
                    delta = timezone.now() - instance.created_at
                    time_in_queue_hours = delta.total_seconds() / 3600
                
                if instance.reviewed_by:
                    ContentModerationLog.objects.create(
                        moderator=instance.reviewed_by,
                        content_type='suggestion',
                        object_id=instance.pk,
                        action=current_status,
                        time_in_queue_hours=time_in_queue_hours
                    )
            except Exception as e:
                logger.error(f"Failed to log suggestion moderation: {e}", exc_info=True)


@receiver(pre_save, sender='places.PlaceEditSuggestion')
def store_previous_suggestion_status(sender, instance, **kwargs):
    """Store previous status before save."""
    if instance.pk:
        try:
            previous = sender.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except sender.DoesNotExist:
            instance._previous_status = None


@receiver(post_save, sender='blog.BlogPost')
def track_blog_moderation(sender, instance, created, **kwargs):
    """Track blog post publication."""
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    if not created and hasattr(instance, '_previous_status'):
        previous_status = instance._previous_status
        current_status = instance.status
        
        if previous_status != current_status and current_status in ['published', 'archived']:
            try:
                time_in_queue_hours = None
                if instance.created_at:
                    delta = timezone.now() - instance.created_at
                    time_in_queue_hours = delta.total_seconds() / 3600
                
                if instance.author and instance.author.is_staff:
                    ContentModerationLog.objects.create(
                        moderator=instance.author,
                        content_type='blog',
                        object_id=instance.pk,
                        action=current_status,
                        time_in_queue_hours=time_in_queue_hours
                    )
            except Exception as e:
                logger.error(f"Failed to log blog moderation: {e}", exc_info=True)


@receiver(pre_save, sender='blog.BlogPost')
def store_previous_blog_status(sender, instance, **kwargs):
    """Store previous status before save."""
    if instance.pk:
        try:
            previous = sender.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except sender.DoesNotExist:
            instance._previous_status = None


@receiver(post_save, sender='contact.ContactMessage')
def track_contact_message(sender, instance, created, **kwargs):
    """Track new contact messages for admin notification."""
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    if created:
        try:
            # Create admin notification for new contact messages
            AdminNotification.objects.create(
                recipient=None,  # All admins
                title='New Contact Message',
                message=f'New message from {instance.name}: {instance.subject or "No subject"}',
                severity='info',
                link=f'/admin/contact/contactmessage/{instance.pk}/change/'
            )
            
            # Update metrics
            SystemMetric.objects.create(
                timestamp=timezone.now(),
                metric_type='request_count',
                metric_name='contact_message',
                value=1,
                metadata={'email': instance.email}
            )
        except Exception as e:
            logger.error(f"Failed to log contact message: {e}", exc_info=True)


# ============================================================================
# Security Event Signals
# ============================================================================

@receiver(user_logged_in)
def track_successful_login(sender, request, user, **kwargs):
    """Track successful login events."""
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    try:
        ip_address = _get_client_ip(request)
        
        # Log as system metric
        SystemMetric.objects.create(
            timestamp=timezone.now(),
            metric_type='active_users',
            metric_name='user_login',
            value=1,
            metadata={
                'user_id': user.pk,
                'username': user.username,
                'is_staff': user.is_staff
            }
        )
        
        # Clear any failed login attempts for this user
        SecurityEvent.objects.filter(
            event_type='failed_login',
            user=user,
            resolved=False
        ).update(resolved=True, resolved_at=timezone.now())
        
    except Exception as e:
        logger.error(f"Failed to log successful login: {e}", exc_info=True)


@receiver(user_login_failed)
def track_failed_login(sender, credentials, request, **kwargs):
    """Track failed login attempts and detect suspicious activity."""
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    try:
        ip_address = _get_client_ip(request)
        ip_hash_value = hash_ip(ip_address)
        username = credentials.get('username', '')
        
        # Log security event
        SecurityEvent.objects.create(
            event_type='failed_login',
            severity='medium',
            user=None,
            ip_hash=ip_hash_value,
            details={
                'username_attempted': username,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Check for multiple failed attempts from same IP
        recent_failures = SecurityEvent.objects.filter(
            event_type='failed_login',
            ip_hash=ip_hash_value,
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=10)
        ).count()
        
        if recent_failures >= 5:
            # Create high-severity alert
            SecurityEvent.objects.create(
                event_type='suspicious_activity',
                severity='high',
                user=None,
                ip_hash=ip_hash_value,
                details={
                    'reason': 'Multiple failed login attempts',
                    'count': recent_failures,
                    'username_attempted': username
                }
            )
            
            # Create admin notification
            AdminNotification.objects.create(
                recipient=None,
                title='⚠️ Multiple Failed Login Attempts',
                message=f'{recent_failures} failed login attempts detected from same IP in last 10 minutes',
                severity='warning',
                link='/admin/monitoring/securityevent/'
            )
        
    except Exception as e:
        logger.error(f"Failed to log failed login: {e}", exc_info=True)


@receiver(user_logged_out)
def track_logout(sender, request, user, **kwargs):
    """Track user logout events."""
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    try:
        if user:
            SystemMetric.objects.create(
                timestamp=timezone.now(),
                metric_type='active_users',
                metric_name='user_logout',
                value=1,
                metadata={
                    'user_id': user.pk,
                    'username': user.username
                }
            )
    except Exception as e:
        logger.error(f"Failed to log logout: {e}", exc_info=True)


# ============================================================================
# Helper Functions
# ============================================================================

def _get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def log_rate_limit_hit(request, limit_type, details=None):
    """
    Helper function to log rate limit violations.
    Can be called from rate limiting middleware/decorators.
    """
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    try:
        ip_address = _get_client_ip(request)
        ip_hash_value = hash_ip(ip_address)
        user = request.user if request.user.is_authenticated else None
        
        SecurityEvent.objects.create(
            event_type='rate_limit_hit',
            severity='medium',
            user=user,
            ip_hash=ip_hash_value,
            details={
                'limit_type': limit_type,
                'path': request.path,
                'method': request.method,
                **(details or {})
            }
        )
    except Exception as e:
        logger.error(f"Failed to log rate limit hit: {e}", exc_info=True)


def log_permission_denied(request, reason=''):
    """
    Helper function to log permission denied events.
    Can be called from views or middleware.
    """
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return
    
    try:
        ip_address = _get_client_ip(request)
        ip_hash_value = hash_ip(ip_address)
        user = request.user if request.user.is_authenticated else None
        
        SecurityEvent.objects.create(
            event_type='permission_denied',
            severity='low',
            user=user,
            ip_hash=ip_hash_value,
            details={
                'path': request.path,
                'method': request.method,
                'reason': reason
            }
        )
    except Exception as e:
        logger.error(f"Failed to log permission denied: {e}", exc_info=True)

