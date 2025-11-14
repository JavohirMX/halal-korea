"""
Rate limiting for social authentication endpoints
Extends the existing rate limiting system to cover OAuth flows
"""

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from .rate_limiting import RateLimiter
from django.conf import settings
import logging

logger = logging.getLogger('security')


class SocialAuthRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware to apply rate limiting to social authentication endpoints
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Social auth endpoints that should be rate limited
        self.social_auth_paths = [
            '/accounts/google/login/',
            '/accounts/facebook/login/',
            '/accounts/github/login/',
            # '/accounts/apple/login/',  # Commented out temporarily
            '/accounts/google/login/callback/',
            '/accounts/facebook/login/callback/',
            '/accounts/github/login/callback/',
            # '/accounts/apple/login/callback/',  # Commented out temporarily
        ]
        
        # Rate limiting configuration for social auth
        self.rate_limits = getattr(settings, 'RATE_LIMIT_SETTINGS', {})
        self.social_auth_limit = self.rate_limits.get('SOCIAL_AUTH_PER_IP_LIMIT', 20)  # 20 attempts per hour
        self.social_auth_window = self.rate_limits.get('SOCIAL_AUTH_PER_IP_WINDOW', 60)  # 60 minutes
        
        super().__init__(get_response)
    
    def process_request(self, request):
        """Check rate limits for social auth endpoints"""
        
        # Only apply to social auth endpoints
        if not any(request.path.startswith(path) for path in self.social_auth_paths):
            return None
        
        # Get client IP
        ip = RateLimiter.get_client_ip(request)
        
        # Check rate limit
        is_limited, current_count, reset_time = RateLimiter.is_rate_limited(
            'social_auth_ip', 
            ip, 
            self.social_auth_limit, 
            self.social_auth_window
        )
        
        if is_limited:
            logger.warning(f"Social auth rate limit exceeded for IP {ip}. Path: {request.path}. Attempts: {current_count}")
            
            # Redirect to rate limited page with specific message
            error_msg = f"Too many social authentication attempts from your IP address. Please try again in {reset_time} minutes."
            return HttpResponseRedirect(f"{reverse('users:rate_limited')}?error={error_msg}")
        
        # Record the attempt
        RateLimiter.record_attempt('social_auth_ip', ip, self.social_auth_window)
        
        # Log the social auth attempt
        provider = self._extract_provider_from_path(request.path)
        if provider:
            logger.info(f"Social auth attempt: provider={provider}, ip={ip}, path={request.path}")
        
        return None
    
    def _extract_provider_from_path(self, path):
        """Extract provider name from URL path"""
        for provider in ['google', 'facebook', 'github']:  # 'apple' commented out temporarily
            if f'/{provider}/' in path:
                return provider
        return None


def check_social_auth_rate_limit(request, provider=None):
    """
    Utility function to check social auth rate limits
    Can be used in views or adapters for additional checks
    
    Args:
        request: Django request object
        provider: Optional provider name for specific limits
        
    Returns:
        Tuple of (is_allowed, error_message)
    """
    ip = RateLimiter.get_client_ip(request)
    
    # Get rate limit settings
    rate_limits = getattr(settings, 'RATE_LIMIT_SETTINGS', {})
    limit = rate_limits.get('SOCIAL_AUTH_PER_IP_LIMIT', 20)
    window = rate_limits.get('SOCIAL_AUTH_PER_IP_WINDOW', 60)
    
    # Check general social auth rate limit
    is_limited, current_count, reset_time = RateLimiter.is_rate_limited(
        'social_auth_ip', 
        ip, 
        limit, 
        window
    )
    
    if is_limited:
        logger.warning(f"Social auth rate limit check failed for IP {ip}. Provider: {provider}. Attempts: {current_count}")
        return False, f"Too many social authentication attempts. Please try again in {reset_time} minutes."
    
    # Provider-specific rate limiting (if needed)
    if provider:
        provider_limit = rate_limits.get(f'SOCIAL_AUTH_{provider.upper()}_PER_IP_LIMIT', limit)
        provider_window = rate_limits.get(f'SOCIAL_AUTH_{provider.upper()}_PER_IP_WINDOW', window)
        
        provider_limited, provider_count, provider_reset = RateLimiter.is_rate_limited(
            f'social_auth_{provider}_ip',
            ip,
            provider_limit,
            provider_window
        )
        
        if provider_limited:
            logger.warning(f"Provider-specific rate limit exceeded for {provider} from IP {ip}. Attempts: {provider_count}")
            return False, f"Too many {provider.title()} authentication attempts. Please try again in {provider_reset} minutes."
    
    return True, ""


def record_social_auth_attempt(request, provider=None):
    """
    Record a social authentication attempt
    
    Args:
        request: Django request object
        provider: Provider name (google, facebook, etc.)
    """
    ip = RateLimiter.get_client_ip(request)
    
    # Get rate limit settings
    rate_limits = getattr(settings, 'RATE_LIMIT_SETTINGS', {})
    window = rate_limits.get('SOCIAL_AUTH_PER_IP_WINDOW', 60)
    
    # Record general social auth attempt
    RateLimiter.record_attempt('social_auth_ip', ip, window)
    
    # Record provider-specific attempt
    if provider:
        provider_window = rate_limits.get(f'SOCIAL_AUTH_{provider.upper()}_PER_IP_WINDOW', window)
        RateLimiter.record_attempt(f'social_auth_{provider}_ip', ip, provider_window)
        
        logger.info(f"Recorded social auth attempt: provider={provider}, ip={ip}")
    else:
        logger.info(f"Recorded social auth attempt: ip={ip}")


# Add social auth rate limiting to settings
def get_social_auth_rate_limits():
    """Get social auth rate limiting configuration"""
    return {
        'SOCIAL_AUTH_PER_IP_LIMIT': 20,      # 20 social auth attempts per hour per IP
        'SOCIAL_AUTH_PER_IP_WINDOW': 60,     # 60 minutes window
        
        # Provider-specific limits (optional)
        'SOCIAL_AUTH_GOOGLE_PER_IP_LIMIT': 15,
        'SOCIAL_AUTH_GOOGLE_PER_IP_WINDOW': 60,
        'SOCIAL_AUTH_FACEBOOK_PER_IP_LIMIT': 15,
        'SOCIAL_AUTH_FACEBOOK_PER_IP_WINDOW': 60,
        'SOCIAL_AUTH_GITHUB_PER_IP_LIMIT': 10,
        'SOCIAL_AUTH_GITHUB_PER_IP_WINDOW': 60,
        # 'SOCIAL_AUTH_APPLE_PER_IP_LIMIT': 10,  # Commented out temporarily
        # 'SOCIAL_AUTH_APPLE_PER_IP_WINDOW': 60,  # Commented out temporarily
    }
