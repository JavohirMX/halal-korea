from .location_manager import get_user_location
from config import static_info
from datetime import datetime
from django.utils.translation import gettext as _
from django.conf import settings

def user_location(request):
    """
    Context processor that adds user's location to all templates.
    """
    location = get_user_location(request)
    return {
        'user_location': location
    } 
    
def static_info_context(request):
    """
    Context processor that adds static info to all templates.
    Also handles dynamic values like the current year for copyright notices.
    """
    # Create a copy of the static info to avoid modifying the original
    info = dict(static_info.INFO)
    
    # Add translatable texts
    info['company_name'] = _('Halal Korea')
    info['site_name'] = _('Halal Korea')
    info['site_tagline'] = _('Find halal food and services across South Korea')
    info['meta_description'] = _('Find halal food and services across South Korea. Join our community and discover verified halal places.')
    
    # Handle copyright text with year formatting
    copyright_text = _('© {year} Halal Korea. All rights reserved.')
    info['copyright_text'] = copyright_text.format(year=datetime.now().year)
    
    # Add Google Maps ID
    info['google_maps_id'] = settings.GOOGLE_MAPS_ID
    
    # Ensure all social media keys exist (even if None) to prevent KeyError in templates
    # This allows templates to safely check if STATIC_INFO.facebook, etc. exist
    social_keys = ['facebook', 'twitter', 'instagram']
    for key in social_keys:
        if key not in info:
            info[key] = None
    
    return {'STATIC_INFO': info}