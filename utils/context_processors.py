from .location_manager import get_user_location
from config import static_info
from datetime import datetime

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
    
    # Replace placeholders with actual values
    if 'copyright_text' in info:
        info['copyright_text'] = info['copyright_text'].format(year=datetime.now().year)
    
    return {'STATIC_INFO': info}