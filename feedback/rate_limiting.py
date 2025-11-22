from django.core.cache import cache
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


def check_feedback_rate_limit(request):
    """
    Check if user can submit feedback
    Rate limits:
    - 5 submissions per day per IP (more generous than contact form)
    - 1 submission per 10 minutes per IP (prevent rapid spam)
    - For authenticated users: 10 submissions per day
    
    Feedback is less strict because we want to encourage user input
    """
    ip = get_client_ip(request)
    user_id = request.user.id if request.user.is_authenticated else None
    
    # Create cache keys
    ip_day_key = f"feedback_rate_limit_ip_day_{ip}"
    ip_minute_key = f"feedback_rate_limit_ip_10min_{ip}"
    user_day_key = f"feedback_rate_limit_user_day_{user_id}" if user_id else None
    
    # Check IP-based limits
    ip_day_count = cache.get(ip_day_key, 0)
    ip_minute_count = cache.get(ip_minute_key, 0)
    
    # Check 10-minute limit (1 submission)
    if ip_minute_count >= 1:
        logger.warning(f"Feedback rate limit hit: IP {ip} - 10 minute limit")
        return False, "Please wait 10 minutes before submitting another feedback."
    
    # Check daily IP limit (5 for anonymous, 10 for authenticated)
    ip_limit = 10 if request.user.is_authenticated else 5
    if ip_day_count >= ip_limit:
        logger.warning(f"Feedback rate limit hit: IP {ip} - daily limit ({ip_limit})")
        return False, f"You have reached the daily limit of {ip_limit} feedback submissions. Please try again tomorrow."
    
    # Check authenticated user daily limit
    if user_id and user_day_key:
        user_day_count = cache.get(user_day_key, 0)
        if user_day_count >= 10:
            logger.warning(f"Feedback rate limit hit: User {user_id} - daily limit")
            return False, "You have reached the daily limit of 10 feedback submissions. Please try again tomorrow."
    
    return True, None


def record_feedback_attempt(request):
    """Record a feedback submission attempt"""
    ip = get_client_ip(request)
    user_id = request.user.id if request.user.is_authenticated else None
    
    # Create cache keys
    ip_day_key = f"feedback_rate_limit_ip_day_{ip}"
    ip_minute_key = f"feedback_rate_limit_ip_10min_{ip}"
    user_day_key = f"feedback_rate_limit_user_day_{user_id}" if user_id else None
    
    # Increment counters
    try:
        # IP-based counters
        cache.set(ip_day_key, cache.get(ip_day_key, 0) + 1, 86400)  # 24 hours
        cache.set(ip_minute_key, cache.get(ip_minute_key, 0) + 1, 600)  # 10 minutes
        
        # User-based counter (if authenticated)
        if user_id and user_day_key:
            cache.set(user_day_key, cache.get(user_day_key, 0) + 1, 86400)  # 24 hours
            
        logger.info(f"Feedback attempt recorded: IP {ip}, User {user_id}")
    except Exception as e:
        logger.error(f"Error recording feedback attempt: {str(e)}")
