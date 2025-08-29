"""
Language Detection and Management Utilities for Halal Korea

This module provides utility functions for enhanced language detection,
user preference management, and language-aware content handling.

Author: Halal Korea Development Team
Created: 2025-01-22
"""

import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import translation
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

User = get_user_model()


class LanguageManager:
    """
    Central manager for language-related operations
    """
    
    @staticmethod
    def get_user_language_context(request) -> Dict:
        """
        Get comprehensive language context for templates and views.
        
        Args:
            request: Django request object
            
        Returns:
            dict: Complete language context including current language,
                  available languages, and user preferences
        """
        current_lang = translation.get_language()
        supported_langs = dict(settings.LANGUAGES)
        
        # Get language detection source information
        detection_source = getattr(request, '_language_detection_source', 'default')
        
        # Get user's preferred language if authenticated
        user_preferred = None
        if request.user.is_authenticated:
            try:
                user_preferred = request.user.preferred_language
            except AttributeError:
                pass
        
        # Check if current language matches user preference
        matches_user_preference = (
            user_preferred and current_lang == user_preferred
        )
        
        context = {
            'current_language': current_lang,
            'current_language_name': supported_langs.get(current_lang, 'Unknown'),
            'supported_languages': supported_langs,
            'available_languages': list(supported_langs.keys()),
            'user_preferred_language': user_preferred,
            'matches_user_preference': matches_user_preference,
            'detection_source': detection_source,
            'is_rtl': current_lang in getattr(settings, 'RTL_LANGUAGES', []),
            'language_switch_url': request.build_absolute_uri(),
        }
        
        return context
    
    @staticmethod
    def set_user_language_preference(user, language_code: str) -> bool:
        """
        Set user's preferred language and validate it.
        
        Args:
            user: User instance
            language_code: ISO language code (e.g., 'ko', 'en', 'uz')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate language code
            supported_langs = dict(settings.LANGUAGES)
            if language_code not in supported_langs:
                logger.warning(f"Invalid language code: {language_code}")
                return False
            
            # Update user preference
            user.preferred_language = language_code
            user.save(update_fields=['preferred_language'])
            
            logger.info(
                f"Updated language preference for user {user.id} to {language_code}",
                extra={
                    'user_id': user.id,
                    'new_language': language_code,
                    'previous_language': getattr(user, '_previous_language', None)
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Error setting language preference for user {user.id}: {str(e)}",
                extra={'user_id': user.id, 'language_code': language_code},
                exc_info=True
            )
            return False
    
    @staticmethod
    def get_language_recommendations(request) -> List[str]:
        """
        Get intelligent language recommendations based on user context.
        
        Args:
            request: Django request object
            
        Returns:
            list: Language codes in order of relevance
        """
        recommendations = []
        
        # Priority 1: User's saved preference
        if request.user.is_authenticated:
            try:
                user_lang = request.user.preferred_language
                if user_lang:
                    recommendations.append(user_lang)
            except AttributeError:
                pass
        
        # Priority 2: Location-based recommendations
        location_recommendations = LanguageManager._get_location_based_recommendations(request)
        for lang in location_recommendations:
            if lang not in recommendations:
                recommendations.append(lang)
        
        # Priority 3: Browser language
        browser_lang = LanguageManager._extract_browser_language(request)
        if browser_lang and browser_lang not in recommendations:
            recommendations.append(browser_lang)
        
        # Priority 4: Add remaining supported languages
        for lang_code in settings.LANGUAGES:
            if lang_code[0] not in recommendations:
                recommendations.append(lang_code[0])
        
        return recommendations[:3]  # Return top 3 recommendations
    
    @staticmethod
    def _get_location_based_recommendations(request) -> List[str]:
        """
        Get language recommendations based on user's location.
        
        Args:
            request: Django request object
            
        Returns:
            list: Language codes based on location
        """
        recommendations = []
        
        # Check if location context is available
        if hasattr(request, 'location_context'):
            location = request.location_context
            country = location.get('country', '')
            
            # Recommend Korean for users in Korea
            if country == 'KR':
                recommendations.append('ko')
            
            # Add more location-based logic as needed
            # Example: Recommend Uzbek for users from Uzbekistan
            elif country == 'UZ':
                recommendations.append('uz')
        
        return recommendations
    
    @staticmethod
    def _extract_browser_language(request) -> Optional[str]:
        """
        Extract preferred language from browser Accept-Language header.
        
        Args:
            request: Django request object
            
        Returns:
            str or None: Best matching language code
        """
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if not accept_language:
            return None
        
        try:
            supported_langs = dict(settings.LANGUAGES)
            
            # Parse Accept-Language header
            languages = []
            for item in accept_language.split(','):
                if ';q=' in item:
                    lang, quality = item.strip().split(';q=')
                    quality = float(quality)
                else:
                    lang, quality = item.strip(), 1.0
                
                # Extract language code (e.g., "en" from "en-US")
                lang_code = lang.split('-')[0].lower()
                if lang_code in supported_langs:
                    languages.append((lang_code, quality))
            
            # Return highest quality match
            if languages:
                return sorted(languages, key=lambda x: x[1], reverse=True)[0][0]
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing Accept-Language header: {e}")
        
        return None


class LanguageContentManager:
    """
    Manager for handling language-specific content
    """
    
    @staticmethod
    def get_localized_field(obj, field_name: str, language_code: str = None) -> str:
        """
        Get localized version of a field if available.
        
        Args:
            obj: Model instance
            field_name: Base field name (e.g., 'name', 'description')
            language_code: Target language code (uses current if None)
            
        Returns:
            str: Localized content or fallback to default
        """
        if not language_code:
            language_code = translation.get_language()
        
        # Try to get localized field (e.g., name_ko, description_uz)
        localized_field = f"{field_name}_{language_code}"
        
        if hasattr(obj, localized_field):
            localized_value = getattr(obj, localized_field)
            if localized_value:  # Return if not empty
                return localized_value
        
        # Fallback to default field
        if hasattr(obj, field_name):
            return getattr(obj, field_name)
        
        return ''
    
    @staticmethod
    def cache_language_content(cache_key: str, content: Dict, timeout: int = 3600) -> None:
        """
        Cache language-specific content.
        
        Args:
            cache_key: Unique cache key
            content: Content dictionary by language code
            timeout: Cache timeout in seconds
        """
        try:
            cache.set(cache_key, content, timeout)
            logger.debug(f"Cached language content with key: {cache_key}")
        except Exception as e:
            logger.error(f"Error caching language content: {e}")
    
    @staticmethod
    def get_cached_language_content(cache_key: str) -> Optional[Dict]:
        """
        Retrieve cached language-specific content.
        
        Args:
            cache_key: Cache key to retrieve
            
        Returns:
            dict or None: Cached content or None if not found
        """
        try:
            content = cache.get(cache_key)
            if content:
                logger.debug(f"Retrieved cached language content: {cache_key}")
            return content
        except Exception as e:
            logger.error(f"Error retrieving cached content: {e}")
            return None


class LanguageAnalytics:
    """
    Analytics and insights for language usage
    """
    
    @staticmethod
    def track_language_usage(request, language_code: str, source: str) -> None:
        """
        Track language usage for analytics.
        
        Args:
            request: Django request object
            language_code: Language being used
            source: Source of language detection (user, browser, etc.)
        """
        try:
            # Create analytics entry (could be stored in database or external service)
            analytics_data = {
                'language': language_code,
                'source': source,
                'user_id': request.user.id if request.user.is_authenticated else None,
                'ip_address': LanguageAnalytics._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:100],
                'timestamp': timezone.now(),
                'path': request.path,
            }
            
            # Log for now (could be sent to analytics service)
            logger.info(
                f"Language usage tracked: {language_code} from {source}",
                extra=analytics_data
            )
            
        except Exception as e:
            logger.error(f"Error tracking language usage: {e}")
    
    @staticmethod
    def _get_client_ip(request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'
    
    @staticmethod
    def get_language_statistics() -> Dict:
        """
        Get language usage statistics.
        
        Returns:
            dict: Language usage statistics
        """
        # This would typically query a database or analytics service
        # For now, return basic info
        supported_langs = dict(settings.LANGUAGES)
        
        return {
            'supported_languages': supported_langs,
            'total_languages': len(supported_langs),
            'default_language': settings.LANGUAGE_CODE,
            # Add more statistics as needed
        }


def language_context_processor(request):
    """
    Context processor to add language information to all templates.
    
    Args:
        request: Django request object
        
    Returns:
        dict: Language context for templates
    """
    try:
        current_language = translation.get_language()
        
        context = LanguageManager.get_user_language_context(request)
        
        # Add language recommendations
        context['language_recommendations'] = LanguageManager.get_language_recommendations(request)
        
        # Add language statistics
        context['language_stats'] = LanguageAnalytics.get_language_statistics()
        
        # Add language-specific context for templates
        language_context = {
            'language_context': context,
            'LANGUAGE_CODE': current_language,
            'LANGUAGE_BIDI': current_language in getattr(settings, 'LANGUAGES_BIDI', []),
            'CURRENT_LANGUAGE_NAME': dict(settings.LANGUAGES).get(current_language, current_language),
        }
        
        return language_context
        
    except Exception as e:
        logger.error(f"Error in language context processor: {e}")
        return {
            'language_context': {},
            'LANGUAGE_CODE': getattr(settings, 'LANGUAGE_CODE', 'en'),
            'LANGUAGE_BIDI': False,
            'CURRENT_LANGUAGE_NAME': 'English',
        }


# Convenience functions for common operations
def get_user_language(request) -> str:
    """Get current user's language code."""
    return translation.get_language()


def set_language_for_request(request, language_code: str) -> bool:
    """
    Set language for current request.
    
    Args:
        request: Django request object
        language_code: Language code to set
        
    Returns:
        bool: True if successful
    """
    try:
        if language_code in dict(settings.LANGUAGES):
            translation.activate(language_code)
            request.LANGUAGE_CODE = language_code
            return True
    except Exception as e:
        logger.error(f"Error setting language for request: {e}")
    
    return False


def is_rtl_language(language_code: str = None) -> bool:
    """
    Check if language is right-to-left.
    
    Args:
        language_code: Language code to check (uses current if None)
        
    Returns:
        bool: True if RTL language
    """
    if not language_code:
        language_code = translation.get_language()
    
    rtl_languages = getattr(settings, 'RTL_LANGUAGES', [])
    return language_code in rtl_languages
