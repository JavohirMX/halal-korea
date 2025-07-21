from utils.location import get_client_ip, get_ip_location
import time

def is_user_in_korea(location_data):
    """
    Determine if user is currently in Korea based on location data.
    Returns True if user is in Korea, False if international.
    """
    if not location_data or location_data.get("error"):
        return False  # If we can't determine location, assume international
    
    country = location_data.get("country", "").lower()
    # Check for various forms of "South Korea" or "Korea"
    korea_indicators = ["south korea", "korea", "korean", "republic of korea"]
    return any(indicator in country for indicator in korea_indicators)

def get_user_location_context(request):
    """
    Get comprehensive location context including whether user is in Korea.
    Returns a dictionary with location info and user context.
    """
    location = get_user_location(request)
    is_in_korea = is_user_in_korea(location)
    
    return {
        'location': location,
        'is_in_korea': is_in_korea,
        'user_type': 'local' if is_in_korea else 'international'
    }

def get_user_location(request):
    """
    Get user's location from session or fallback to IP-based location.
    Returns a dictionary with location information.
    Enhanced to better handle international users.
    """
    # Check session for saved location
    session_loc = request.session.get('user_location')
    
    if session_loc and time.time() - session_loc['timestamp'] < 3600:  # Check if not expired (1 hour)
        return session_loc
    
    # If no valid session location, try to get location from IP
    ip = get_client_ip(request)
    location = get_ip_location(ip)
    
    # Enhanced fallback logic for international users
    if not location or location.get("error") or not location.get("city"):
        # For development/unknown cases, provide a neutral fallback
        location = {
            "city": "Unknown",
            "country": "Unknown",
            "is_fallback": True
        }
    else:
        # Mark as detected from IP
        location["is_fallback"] = False
    
    # Add timestamp to location data
    location['timestamp'] = time.time()
    
    # Save to session
    request.session['user_location'] = location
    
    return location

def get_default_korea_location():
    """
    Get default Korea location for trip planning context.
    Used when international users need Korea reference point.
    """
    return {
        "city": "Seoul",
        "country": "South Korea",
        "lat": 37.5665,
        "lng": 126.9780,
        "is_default_korea": True
    }

def update_user_location(request, location_data):
    """
    Update user's location in session.
    location_data should be a dictionary containing at least 'city' or both 'lat' and 'lng'.
    """
    location = {
        'timestamp': time.time()
    }
    
    if 'lat' in location_data and 'lng' in location_data:
        location.update({
            'lat': location_data['lat'],
            'lng': location_data['lng']
        })
    
    if 'city' in location_data:
        location['city'] = location_data['city']
        
    if 'country' in location_data:
        location['country'] = location_data['country']
    
    request.session['user_location'] = location
    return location

def clear_user_location(request):
    """Clear user's location from session."""
    if 'user_location' in request.session:
        del request.session['user_location'] 