"""
Enhanced Language Detection Middleware for Halal Korea

This middleware implements a smart language detection system with priority order:
1. URL parameter override (e.g., ?lang=ko)
2. User profile preference (for authenticated users)
3. Session language setting
4. Browser Accept-Language header
5. Default language (English)

Author: Halal Korea Development Team
Created: 2025-01-22
"""

import logging
from django.conf import settings
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()

# Session key for language preference
LANGUAGE_SESSION_KEY = 'django_language'

class SmartLanguageMiddleware(MiddlewareMixin):
    """
    Enhanced language detection middleware that intelligently determines
    the best language for each user based on multiple factors.
    
    IMPORTANT: This middleware must be placed AFTER SessionMiddleware 
    and AuthenticationMiddleware in the MIDDLEWARE setting for optimal 
    functionality. It includes graceful fallbacks if user/session data 
    is not available.
    
    Middleware order should be:
    1. SessionMiddleware  
    2. AuthenticationMiddleware
    3. SmartLanguageMiddleware (this)
    4. LocaleMiddleware
    """
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.supported_languages = dict(settings.LANGUAGES)
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Process incoming request to determine optimal language.
        
        Priority order:
        1. URL parameter (?lang=code)
        2. User profile preference (authenticated users)
        3. Session language
        4. Browser Accept-Language header
        5. Default language
        """
        try:
            # Get current language from various sources
            url_lang = self._get_url_language_param(request)
            user_lang = self._get_user_preferred_language(request)
            session_lang = self._get_session_language(request)
            browser_lang = self._get_browser_preferred_language(request)
            
            # Determine final language based on priority
            final_language = self._determine_language(
                url_lang, user_lang, session_lang, browser_lang
            )
            
            # Set the language if it's different from current
            current_language = translation.get_language()
            if final_language != current_language:
                translation.activate(final_language)
                request.LANGUAGE_CODE = final_language
            
                # Always update session when language changes
                try:
                    if hasattr(request, 'session'):
                        request.session[LANGUAGE_SESSION_KEY] = final_language
                    else:
                        logger.debug("Session not available for language storage")
                except Exception as e:
                    logger.debug(f"Error storing language in session: {e}")
                
                # Update user's preferred language if they're authenticated and language changed via URL
                if url_lang and hasattr(request, 'user') and request.user and request.user.is_authenticated:
                    self._update_user_language_preference(request.user, final_language)
                
                # Log language change for analytics
                self._log_language_change(request, current_language, final_language)
                
            # If user has a preference but session doesn't match, update session
            elif user_lang and session_lang != user_lang:
                try:
                    if hasattr(request, 'session'):
                        request.session[LANGUAGE_SESSION_KEY] = user_lang
                        logger.debug(f"Updated session to match user preference: {user_lang}")
                except Exception as e:
                    logger.debug(f"Error updating session to user preference: {e}")
                    
        except Exception as e:
            # If anything goes wrong, fall back to default behavior
            logger.error(f"Error in SmartLanguageMiddleware: {str(e)}", exc_info=True)
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = settings.LANGUAGE_CODE
    
    def _get_url_language_param(self, request):
        """Get language from URL parameter (?lang=code)"""
        lang_param = request.GET.get('lang')
        if lang_param and lang_param in self.supported_languages:
            logger.debug(f"Language from URL param: {lang_param}")
            return lang_param
        return None
    
    def _get_user_preferred_language(self, request):
        """Get language from authenticated user's profile"""
        # Check if user attribute exists (AuthenticationMiddleware must run first)
        if not hasattr(request, 'user'):
            logger.debug("User attribute not available yet (AuthenticationMiddleware not processed)")
            return None
            
        try:
            if request.user.is_authenticated:
                user_lang = getattr(request.user, 'preferred_language', None)
                if user_lang and user_lang in self.supported_languages:
                    logger.debug(f"Language from user profile: {user_lang}")
                    return user_lang
        except (AttributeError, TypeError) as e:
            logger.debug(f"Error getting user language preference: {e}")
            pass
        return None
    
    def _get_session_language(self, request):
        """Get language from session"""
        try:
            # Check if session is available (SessionMiddleware must run first)
            if not hasattr(request, 'session'):
                logger.debug("Session not available yet (SessionMiddleware not processed)")
                return None
                
            session_lang = request.session.get(LANGUAGE_SESSION_KEY)
            if session_lang and session_lang in self.supported_languages:
                logger.debug(f"Language from session: {session_lang}")
                return session_lang
        except (AttributeError, KeyError) as e:
            logger.debug(f"Error getting session language: {e}")
            pass
        return None
    
    def _get_browser_preferred_language(self, request):
        """
        Get preferred language from browser Accept-Language header
        Parse and find best match with supported languages
        """
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if not accept_language:
            return None
            
        try:
            # Parse Accept-Language header
            # Format: "en-US,en;q=0.9,ko;q=0.8,uz;q=0.7"
            languages = []
            for item in accept_language.split(','):
                if ';q=' in item:
                    lang, quality = item.strip().split(';q=')
                    quality = float(quality)
                else:
                    lang, quality = item.strip(), 1.0
                
                # Extract language code (e.g., "en" from "en-US")
                lang_code = lang.split('-')[0].lower()
                if lang_code in self.supported_languages:
                    languages.append((lang_code, quality))
            
            # Sort by quality score and return best match
            if languages:
                best_lang = sorted(languages, key=lambda x: x[1], reverse=True)[0][0]
                logger.debug(f"Language from browser: {best_lang}")
                return best_lang
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing Accept-Language header: {e}")
        
        return None
    
    def _determine_language(self, url_lang, user_lang, session_lang, browser_lang):
        """
        Determine final language based on priority order
        
        Args:
            url_lang: Language from URL parameter
            user_lang: Language from user profile
            session_lang: Language from session
            browser_lang: Language from browser
            
        Returns:
            str: Language code to use
        """
        # Priority 1: URL parameter (immediate override)
        if url_lang:
            logger.info(f"Using URL language: {url_lang}")
            return url_lang
        
        # Priority 2: User profile (for authenticated users)
        if user_lang:
            logger.info(f"Using user preferred language: {user_lang}")
            return user_lang
        
        # Priority 3: Session language (previous choice)
        if session_lang:
            logger.debug(f"Using session language: {session_lang}")
            return session_lang
        
        # Priority 4: Browser preference
        if browser_lang:
            logger.info(f"Using browser language: {browser_lang}")
            return browser_lang
        
        # Priority 5: Default language
        logger.debug(f"Using default language: {settings.LANGUAGE_CODE}")
        return settings.LANGUAGE_CODE
    
    def _log_language_change(self, request, old_lang, new_lang):
        """Log language changes for analytics and debugging"""
        logger.info(
            f"Language changed from {old_lang} to {new_lang}",
            extra={
                'user_id': request.user.id if request.user.is_authenticated else None,
                'old_language': old_lang,
                'new_language': new_lang,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:100]
            }
        )
    
    def _update_user_language_preference(self, user, language_code):
        """
        Update user's preferred language in their profile
        
        Args:
            user: User instance
            language_code: New language code to set
        """
        try:
            if hasattr(user, 'preferred_language'):
                old_preference = getattr(user, 'preferred_language', None)
                
                # Only update if it's actually different
                if old_preference != language_code:
                    user.preferred_language = language_code
                    user.save(update_fields=['preferred_language'])
                    
                    logger.info(
                        f"Updated user {user.id} language preference from {old_preference} to {language_code}",
                        extra={
                            'user_id': user.id,
                            'old_language': old_preference,
                            'new_language': language_code,
                            'source': 'language_switcher'
                        }
                    )
        except Exception as e:
            logger.error(
                f"Error updating user {user.id} language preference: {str(e)}",
                extra={'user_id': user.id, 'target_language': language_code},
                exc_info=True
            )

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def process_response(self, request, response):
        """
        Process response to ensure language context is maintained
        """
        # Add language info to response headers for debugging
        if hasattr(request, 'LANGUAGE_CODE'):
            response['Content-Language'] = request.LANGUAGE_CODE
        
        return response


class LanguageDetectionUtils:
    """
    Utility functions for language detection and management
    """
    
    @staticmethod
    def get_user_language_context(request):
        """
        Get comprehensive language context for templates
        
        Returns:
            dict: Language context information
        """
        current_lang = translation.get_language()
        supported_langs = dict(settings.LANGUAGES)
        
        context = {
            'current_language': current_lang,
            'current_language_name': supported_langs.get(current_lang, 'Unknown'),
            'supported_languages': supported_langs,
            'is_rtl': current_lang in getattr(settings, 'RTL_LANGUAGES', []),
            'language_detection_source': getattr(request, '_language_source', 'default')
        }
        
        return context
    
    @staticmethod
    def set_user_language_preference(user, language_code):
        """
        Set user's language preference and update session
        
        Args:
            user: User instance
            language_code: Language code to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if language_code in dict(settings.LANGUAGES):
                user.preferred_language = language_code
                user.save(update_fields=['preferred_language'])
                logger.info(f"Updated user {user.id} language preference to {language_code}")
                return True
        except Exception as e:
            logger.error(f"Error setting user language preference: {e}")
        
        return False
    
    @staticmethod
    def get_language_recommendations(request):
        """
        Get language recommendations based on user location and preferences
        
        Args:
            request: Django request object
            
        Returns:
            list: Recommended language codes in order of relevance
        """
        recommendations = []
        
        # Check if we have location context
        if hasattr(request, 'location_context'):
            location = getattr(request, 'location_context', {})
            country = location.get('country', '')
            
            # Recommend Korean for users in Korea
            if country == 'KR':
                recommendations.append('ko')
            
            # Add other location-based recommendations as needed
        
        # Add browser language if supported
        middleware = SmartLanguageMiddleware()
        browser_lang = middleware._get_browser_preferred_language(request)
        if browser_lang and browser_lang not in recommendations:
            recommendations.append(browser_lang)
        
        # Add English as fallback if not already included
        if 'en' not in recommendations:
            recommendations.append('en')
        
        return recommendations
