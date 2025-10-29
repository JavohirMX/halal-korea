"""
Django signals for user authentication events
Integrates social authentication with existing security logging system
"""

import logging
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from allauth.socialaccount.signals import (
    pre_social_login, 
    social_account_added, 
    social_account_removed,
    social_account_updated
)
from allauth.account.signals import user_signed_up

logger = logging.getLogger('security')

@receiver(pre_social_login)
def log_social_login_attempt(sender, request, sociallogin, **kwargs):
    """Log social login attempts"""
    provider = sociallogin.account.provider
    user_ip = request.META.get('REMOTE_ADDR', 'unknown')
    uid = sociallogin.account.uid
    email = getattr(sociallogin.user, 'email', 'unknown')
    
    logger.info(f"Social login attempt: provider={provider}, uid={uid}, email={email}, ip={user_ip}")

@receiver(user_signed_up)
def log_social_signup(sender, request, user, **kwargs):
    """Log social account signups"""
    if hasattr(request, 'sociallogin'):
        # This is a social signup
        sociallogin = request.sociallogin
        provider = sociallogin.account.provider
        user_ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        logger.info(f"Social signup completed: user={user.username}, provider={provider}, email={user.email}, ip={user_ip}")

@receiver(social_account_added)
def log_social_account_connected(sender, request, sociallogin, **kwargs):
    """Log when a social account is connected to an existing user"""
    provider = sociallogin.account.provider
    user = sociallogin.user
    user_ip = request.META.get('REMOTE_ADDR', 'unknown')
    
    logger.info(f"Social account connected: user={user.username}, provider={provider}, ip={user_ip}")

@receiver(social_account_removed)
def log_social_account_disconnected(sender, request, socialaccount, **kwargs):
    """Log when a social account is disconnected"""
    provider = socialaccount.provider
    user = socialaccount.user
    user_ip = request.META.get('REMOTE_ADDR', 'unknown')
    
    logger.info(f"Social account disconnected: user={user.username}, provider={provider}, ip={user_ip}")

@receiver(social_account_updated)
def log_social_account_updated(sender, request, sociallogin, **kwargs):
    """Log when social account data is updated"""
    provider = sociallogin.account.provider
    user = sociallogin.user
    user_ip = request.META.get('REMOTE_ADDR', 'unknown')
    
    logger.info(f"Social account updated: user={user.username}, provider={provider}, ip={user_ip}")

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Enhanced login logging that detects social logins"""
    user_ip = request.META.get('REMOTE_ADDR', 'unknown')
    
    # Check if this is a social login
    if hasattr(request, 'sociallogin'):
        sociallogin = request.sociallogin
        provider = sociallogin.account.provider
        logger.info(f"Social login successful: user={user.username}, provider={provider}, ip={user_ip}")
    else:
        # This is handled by the existing login view logging
        pass

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout (already handled in views but adding for completeness)"""
    if user:
        user_ip = request.META.get('REMOTE_ADDR', 'unknown')
        logger.info(f"User logout: user={user.username}, ip={user_ip}")
