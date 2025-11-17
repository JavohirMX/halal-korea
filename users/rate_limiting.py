"""
Rate limiting utilities for user actions
"""
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# Rate limiting configurations from settings
def get_rate_limits():
    """Get rate limiting configuration from Django settings"""
    return {
        'email_send': {
            'per_ip': {
                'limit': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('EMAIL_SEND_PER_IP_LIMIT', 5),
                'window_minutes': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('EMAIL_SEND_PER_IP_WINDOW', 60)
            },
            'per_user': {
                'limit': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('EMAIL_SEND_PER_USER_LIMIT', 3),
                'window_minutes': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('EMAIL_SEND_PER_USER_WINDOW', 30)
            },
        },
        'registration': {
            'per_ip': {
                'limit': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('REGISTRATION_PER_IP_LIMIT', 3),
                'window_minutes': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('REGISTRATION_PER_IP_WINDOW', 60)
            },
        },
        'login_attempts': {
            'per_ip': {
                'limit': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('LOGIN_ATTEMPTS_PER_IP_LIMIT', 10),
                'window_minutes': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('LOGIN_ATTEMPTS_PER_IP_WINDOW', 30)
            },
        },
    }


RATE_LIMITS = get_rate_limits()


class RateLimiter:
    """
    Rate limiter using Django cache backend
    """
    
    @staticmethod
    def get_client_ip(request) -> str:
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'
    
    @staticmethod
    def get_cache_key(action: str, identifier: str) -> str:
        """Generate cache key for rate limiting"""
        return f"rate_limit:{action}:{identifier}"
    
    @staticmethod
    def is_rate_limited(action: str, identifier: str, limit: int, window_minutes: int) -> Tuple[bool, int, int]:
        """
        Check if action is rate limited
        
        Args:
            action: Type of action (e.g., 'email_send', 'registration')
            identifier: IP address or user ID
            limit: Maximum attempts allowed
            window_minutes: Time window in minutes
            
        Returns:
            Tuple of (is_limited, current_attempts, time_until_reset)
        """
        cache_key = RateLimiter.get_cache_key(action, identifier)
        
        # Get current attempts data
        attempts_data = cache.get(cache_key, {'count': 0, 'first_attempt': None})
        
        now = timezone.now()
        window_delta = timedelta(minutes=window_minutes)
        
        # Reset if window has expired
        if (attempts_data['first_attempt'] and 
            now - attempts_data['first_attempt'] > window_delta):
            attempts_data = {'count': 0, 'first_attempt': None}
        
        current_count = attempts_data['count']
        is_limited = current_count >= limit
        
        # Calculate time until reset
        time_until_reset = 0
        if attempts_data['first_attempt']:
            reset_time = attempts_data['first_attempt'] + window_delta
            if now < reset_time:
                time_until_reset = int((reset_time - now).total_seconds() / 60)
        
        return is_limited, current_count, time_until_reset
    
    @staticmethod
    def record_attempt(action: str, identifier: str, window_minutes: int) -> int:
        """
        Record an attempt for the given action and identifier
        
        Returns:
            Current attempt count after recording
        """
        cache_key = RateLimiter.get_cache_key(action, identifier)
        
        # Get current attempts data
        attempts_data = cache.get(cache_key, {'count': 0, 'first_attempt': None})
        
        now = timezone.now()
        window_delta = timedelta(minutes=window_minutes)
        
        # Reset if window has expired
        if (attempts_data['first_attempt'] and 
            now - attempts_data['first_attempt'] > window_delta):
            attempts_data = {'count': 0, 'first_attempt': None}
        
        # Record this attempt
        if attempts_data['first_attempt'] is None:
            attempts_data['first_attempt'] = now
        
        attempts_data['count'] += 1
        
        # Cache for the window duration
        cache.set(cache_key, attempts_data, window_minutes * 60)
        
        logger.info(f"Recorded attempt for {action}:{identifier}. Count: {attempts_data['count']}")
        return attempts_data['count']


def check_email_rate_limit(request, user=None) -> Tuple[bool, str]:
    """
    Check if email sending is rate limited
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    ip = RateLimiter.get_client_ip(request)
    
    # Check IP-based rate limit
    ip_config = RATE_LIMITS['email_send']['per_ip']
    ip_limited, ip_count, ip_reset_time = RateLimiter.is_rate_limited(
        'email_send_ip', ip, ip_config['limit'], ip_config['window_minutes']
    )
    
    if ip_limited:
        logger.warning(f"Email rate limit exceeded for IP {ip}. Attempts: {ip_count}")
        return False, f"Too many email requests from your IP address. Please try again in {ip_reset_time} minutes."
    
    # Check user-based rate limit (if user provided)
    if user and user.is_authenticated:
        user_config = RATE_LIMITS['email_send']['per_user']
        user_limited, user_count, user_reset_time = RateLimiter.is_rate_limited(
            'email_send_user', str(user.id), user_config['limit'], user_config['window_minutes']
        )
        
        if user_limited:
            logger.warning(f"Email rate limit exceeded for user {user.username} (ID: {user.id}). Attempts: {user_count}")
            return False, f"Too many email requests for your account. Please try again in {user_reset_time} minutes."
    
    return True, ""


def record_email_attempt(request, user=None):
    """Record an email sending attempt"""
    ip = RateLimiter.get_client_ip(request)
    
    # Record IP-based attempt
    ip_config = RATE_LIMITS['email_send']['per_ip']
    RateLimiter.record_attempt('email_send_ip', ip, ip_config['window_minutes'])
    
    # Record user-based attempt (if user provided)
    if user and user.is_authenticated:
        user_config = RATE_LIMITS['email_send']['per_user']
        RateLimiter.record_attempt('email_send_user', str(user.id), user_config['window_minutes'])


def check_registration_rate_limit(request) -> Tuple[bool, str]:
    """
    Check if registration is rate limited
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    ip = RateLimiter.get_client_ip(request)
    
    # Check IP-based rate limit
    ip_config = RATE_LIMITS['registration']['per_ip']
    ip_limited, ip_count, ip_reset_time = RateLimiter.is_rate_limited(
        'registration_ip', ip, ip_config['limit'], ip_config['window_minutes']
    )
    
    if ip_limited:
        logger.warning(f"Registration rate limit exceeded for IP {ip}. Attempts: {ip_count}")
        return False, f"Too many registration attempts from your IP address. Please try again in {ip_reset_time} minutes."
    
    return True, ""


def record_registration_attempt(request):
    """Record a registration attempt"""
    ip = RateLimiter.get_client_ip(request)
    
    # Record IP-based attempt
    ip_config = RATE_LIMITS['registration']['per_ip']
    RateLimiter.record_attempt('registration_ip', ip, ip_config['window_minutes'])


def check_login_rate_limit(request) -> Tuple[bool, str]:
    """
    Check if login attempts are rate limited
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    ip = RateLimiter.get_client_ip(request)
    
    # Check IP-based rate limit
    ip_config = RATE_LIMITS['login_attempts']['per_ip']
    ip_limited, ip_count, ip_reset_time = RateLimiter.is_rate_limited(
        'login_ip', ip, ip_config['limit'], ip_config['window_minutes']
    )
    
    if ip_limited:
        logger.warning(f"Login rate limit exceeded for IP {ip}. Attempts: {ip_count}")
        return False, f"Too many login attempts from your IP address. Please try again in {ip_reset_time} minutes."
    
    return True, ""


def record_login_attempt(request):
    """Record a login attempt"""
    ip = RateLimiter.get_client_ip(request)
    
    # Record IP-based attempt
    ip_config = RATE_LIMITS['login_attempts']['per_ip']
    RateLimiter.record_attempt('login_ip', ip, ip_config['window_minutes'])


def check_password_reset_rate_limit(request, email=None) -> Tuple[bool, str]:
    """
    Check if password reset requests are rate limited
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    ip = RateLimiter.get_client_ip(request)
    
    # Check IP-based rate limit
    ip_config = {
        'limit': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('PASSWORD_RESET_PER_IP_LIMIT', 3),
        'window_minutes': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('PASSWORD_RESET_PER_IP_WINDOW', 60)
    }
    
    ip_limited, ip_count, ip_reset_time = RateLimiter.is_rate_limited(
        'password_reset_ip', ip, ip_config['limit'], ip_config['window_minutes']
    )
    
    if ip_limited:
        logger.warning(f"Password reset rate limit exceeded for IP {ip}. Attempts: {ip_count}")
        return False, f"Too many password reset requests from your IP address. Please try again in {ip_reset_time} minutes."
    
    # Check email-based rate limit (if email provided)
    if email:
        email_config = {
            'limit': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('PASSWORD_RESET_PER_EMAIL_LIMIT', 2),
            'window_minutes': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('PASSWORD_RESET_PER_EMAIL_WINDOW', 60)
        }
        
        email_limited, email_count, email_reset_time = RateLimiter.is_rate_limited(
            'password_reset_email', email.lower(), email_config['limit'], email_config['window_minutes']
        )
        
        if email_limited:
            logger.warning(f"Password reset rate limit exceeded for email {email}. Attempts: {email_count}")
            return False, f"Too many password reset requests for this email address. Please try again in {email_reset_time} minutes."
    
    return True, ""


def record_password_reset_attempt(request, email=None):
    """Record a password reset attempt"""
    ip = RateLimiter.get_client_ip(request)
    
    # Record IP-based attempt
    ip_config = {
        'window_minutes': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('PASSWORD_RESET_PER_IP_WINDOW', 60)
    }
    RateLimiter.record_attempt('password_reset_ip', ip, ip_config['window_minutes'])
    
    # Record email-based attempt (if email provided)
    if email:
        email_config = {
            'window_minutes': getattr(settings, 'RATE_LIMIT_SETTINGS', {}).get('PASSWORD_RESET_PER_EMAIL_WINDOW', 60)
        }
        RateLimiter.record_attempt('password_reset_email', email.lower(), email_config['window_minutes'])
