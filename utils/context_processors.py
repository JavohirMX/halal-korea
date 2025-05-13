from .location_manager import get_user_location

def user_location(request):
    """
    Context processor that adds user's location to all templates.
    """
    location = get_user_location(request)
    return {
        'user_location': location
    } 