from django.core.cache import cache
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get the client's IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_contact_rate_limit(request):
    """
    Check if user can submit a contact form
    Rate limits:
    - 3 submissions per hour per IP
    - 1 submission per 5 minutes per IP
    - For authenticated users: 5 submissions per hour
    """
    ip = get_client_ip(request)
    user_id = request.user.id if request.user.is_authenticated else None
    
    # Create cache keys
    ip_hour_key = f"contact_rate_limit_ip_hour_{ip}"
    ip_minute_key = f"contact_rate_limit_ip_5min_{ip}"
    user_hour_key = f"contact_rate_limit_user_hour_{user_id}" if user_id else None
    
    # Check IP-based limits
    ip_hour_count = cache.get(ip_hour_key, 0)
    ip_minute_count = cache.get(ip_minute_key, 0)
    
    # Check 5-minute limit (1 submission)
    if ip_minute_count >= 1:
        logger.warning(f"Contact form rate limit hit: IP {ip} - 5 minute limit")
        return False, "Please wait 5 minutes before submitting another message."
    
    # Check hourly IP limit (3 submissions for anonymous, 5 for authenticated)
    ip_limit = 5 if request.user.is_authenticated else 3
    if ip_hour_count >= ip_limit:
        logger.warning(f"Contact form rate limit hit: IP {ip} - hourly limit ({ip_limit})")
        return False, f"You have reached the hourly limit of {ip_limit} contact messages. Please try again later."
    
    # Check authenticated user hourly limit
    if user_id and user_hour_key:
        user_hour_count = cache.get(user_hour_key, 0)
        if user_hour_count >= 5:
            logger.warning(f"Contact form rate limit hit: User {user_id} - hourly limit")
            return False, "You have reached the hourly limit of 5 contact messages. Please try again later."
    
    return True, None


def record_contact_attempt(request):
    """Record a contact form submission attempt"""
    ip = get_client_ip(request)
    user_id = request.user.id if request.user.is_authenticated else None
    
    # Create cache keys
    ip_hour_key = f"contact_rate_limit_ip_hour_{ip}"
    ip_minute_key = f"contact_rate_limit_ip_5min_{ip}"
    user_hour_key = f"contact_rate_limit_user_hour_{user_id}" if user_id else None
    
    # Increment counters
    try:
        # IP-based counters
        cache.set(ip_hour_key, cache.get(ip_hour_key, 0) + 1, 3600)  # 1 hour
        cache.set(ip_minute_key, cache.get(ip_minute_key, 0) + 1, 300)  # 5 minutes
        
        # User-based counter (if authenticated)
        if user_id and user_hour_key:
            cache.set(user_hour_key, cache.get(user_hour_key, 0) + 1, 3600)  # 1 hour
            
        logger.info(f"Contact form attempt recorded: IP {ip}, User {user_id}")
    except Exception as e:
        logger.error(f"Error recording contact attempt: {str(e)}")


def rate_limited_contact_view(request):
    """View to show when contact form is rate limited"""
    error_message = request.GET.get('error', 'You have exceeded the rate limit for contact messages.')
    return render(request, 'contact/rate_limited.html', {
        'error_message': error_message,
        'page_title': 'Rate Limited',
    })
