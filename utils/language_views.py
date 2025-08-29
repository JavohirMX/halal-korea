"""
Enhanced Language Views for Halal Korea

This module provides enhanced language switching functionality that integrates
with user preferences and provides better analytics.

Author: Halal Korea Development Team
Created: 2025-01-22
"""

import logging
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from utils.language_utils import LanguageManager

logger = logging.getLogger(__name__)

User = get_user_model()

# Session key for language preference
LANGUAGE_SESSION_KEY = 'django_language'


@require_POST
def set_language(request):
    """
    Enhanced language switching view that updates user preferences.
    
    This view replaces Django's default set_language view with enhanced
    functionality for updating authenticated user's language preferences.
    """
    try:
        language = request.POST.get('language')
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
        
        # Validate language
        supported_languages = dict(settings.LANGUAGES)
        if language not in supported_languages:
            logger.warning(f"Invalid language requested: {language}")
            return HttpResponseRedirect(next_url)
        
        # Validate next URL for security
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = '/'
        
        # Activate language for this response
        translation.activate(language)
        
        # Create response
        response = HttpResponseRedirect(next_url)
        
        # Set session language
        if hasattr(request, 'session'):
            request.session[LANGUAGE_SESSION_KEY] = language
        
        # Set language cookie as fallback (with fallback values)
        response.set_cookie(
            getattr(settings, 'LANGUAGE_COOKIE_NAME', 'django_language'),
            language,
            max_age=getattr(settings, 'LANGUAGE_COOKIE_AGE', None),
            path=getattr(settings, 'LANGUAGE_COOKIE_PATH', '/'),
            domain=getattr(settings, 'LANGUAGE_COOKIE_DOMAIN', None),
            secure=getattr(settings, 'LANGUAGE_COOKIE_SECURE', False),
            httponly=getattr(settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
            samesite=getattr(settings, 'LANGUAGE_COOKIE_SAMESITE', 'Lax'),
        )
        
        # Update user preference if authenticated
        if request.user.is_authenticated:
            update_success = _update_user_language_preference(request.user, language)
            if update_success:
                logger.info(
                    f"Language switched to {language} for user {request.user.id}",
                    extra={
                        'user_id': request.user.id,
                        'new_language': language,
                        'source': 'language_switcher_view',
                        'ip_address': _get_client_ip(request)
                    }
                )
        else:
            logger.info(
                f"Language switched to {language} for anonymous user",
                extra={
                    'new_language': language,
                    'source': 'language_switcher_view',
                    'ip_address': _get_client_ip(request)
                }
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in set_language view: {str(e)}", exc_info=True)
        # Fall back to original URL or home page
        fallback_url = request.POST.get('next', '/')
        return HttpResponseRedirect(fallback_url)


@require_POST
@csrf_exempt
def set_language_ajax(request):
    """
    AJAX version of language switching for dynamic interfaces.
    
    Returns JSON response for AJAX requests.
    """
    try:
        language = request.POST.get('language')
        
        # Validate language
        supported_languages = dict(settings.LANGUAGES)
        if language not in supported_languages:
            return JsonResponse({
                'success': False,
                'error': 'Invalid language',
                'supported_languages': list(supported_languages.keys())
            })
        
        # Activate language
        translation.activate(language)
        
        # Update session
        if hasattr(request, 'session'):
            request.session[LANGUAGE_SESSION_KEY] = language
        
        # Update user preference if authenticated
        user_updated = False
        if request.user.is_authenticated:
            user_updated = _update_user_language_preference(request.user, language)
        
        # Get language context for response
        context = LanguageManager.get_user_language_context(request)
        
        response_data = {
            'success': True,
            'language': language,
            'language_name': supported_languages.get(language, language),
            'user_preference_updated': user_updated,
            'context': context
        }
        
        response = JsonResponse(response_data)
        
        # Set language cookie
        response.set_cookie(
            getattr(settings, 'LANGUAGE_COOKIE_NAME', 'django_language'),
            language,
            max_age=getattr(settings, 'LANGUAGE_COOKIE_AGE', None),
            path=getattr(settings, 'LANGUAGE_COOKIE_PATH', '/'),
            domain=getattr(settings, 'LANGUAGE_COOKIE_DOMAIN', None),
            secure=getattr(settings, 'LANGUAGE_COOKIE_SECURE', False),
            httponly=getattr(settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
            samesite=getattr(settings, 'LANGUAGE_COOKIE_SAMESITE', 'Lax'),
        )
        
        logger.info(
            f"AJAX language switch to {language}",
            extra={
                'user_id': request.user.id if request.user.is_authenticated else None,
                'new_language': language,
                'source': 'ajax_language_switcher'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in AJAX set_language view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        })


@login_required
def get_user_language_preferences(request):
    """
    API endpoint to get user's language preferences and recommendations.
    """
    try:
        user = request.user
        current_language = translation.get_language()
        
        # Get user's current preference
        user_preference = getattr(user, 'preferred_language', None)
        
        # Get language recommendations
        recommendations = LanguageManager.get_language_recommendations(request)
        
        # Get full language context
        context = LanguageManager.get_user_language_context(request)
        
        return JsonResponse({
            'success': True,
            'user_preference': user_preference,
            'current_language': current_language,
            'recommendations': recommendations,
            'context': context,
            'supported_languages': dict(settings.LANGUAGES)
        })
        
    except Exception as e:
        logger.error(f"Error getting user language preferences: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Unable to retrieve language preferences'
        })


def _update_user_language_preference(user, language_code):
    """
    Helper function to update user's language preference.
    
    Args:
        user: User instance
        language_code: New language code
        
    Returns:
        bool: True if update was successful
    """
    try:
        if hasattr(user, 'preferred_language'):
            old_preference = getattr(user, 'preferred_language', None)
            
            # Only update if different
            if old_preference != language_code:
                user.preferred_language = language_code
                user.save(update_fields=['preferred_language'])
                
                logger.info(
                    f"Updated user {user.id} language preference: {old_preference} → {language_code}",
                    extra={
                        'user_id': user.id,
                        'old_language': old_preference,
                        'new_language': language_code
                    }
                )
                return True
            else:
                logger.debug(f"User {user.id} language preference unchanged: {language_code}")
                return True
                
    except Exception as e:
        logger.error(
            f"Failed to update language preference for user {user.id}: {str(e)}",
            extra={'user_id': user.id, 'target_language': language_code},
            exc_info=True
        )
    
    return False


def _get_client_ip(request):
    """Get client IP address for logging."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or 'unknown'
