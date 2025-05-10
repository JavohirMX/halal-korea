from utils.location import get_client_ip, get_ip_location
import time

def get_user_location(request):
    """
    Get user's location from session or fallback to IP-based location.
    Returns a dictionary with location information.
    """
    # Check session for saved location
    session_loc = request.session.get('user_location')
    
    if session_loc and time.time() - session_loc['timestamp'] < 3600:  # Check if not expired (1 hour)
        return session_loc
    
    # If no valid session location, try to get location from IP
    ip = get_client_ip(request)
    location = get_ip_location(ip)
    
    # If IP location fails, default to Seoul
    if not location or not location.get("city"):
        location = {
            "city": "Seoul",
            "country": "South Korea"
        }
    
    # Add timestamp to location data
    location['timestamp'] = time.time()
    
    # Save to session
    request.session['user_location'] = location
    
    return location

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
    
    request.session['user_location'] = location
    return location

def clear_user_location(request):
    """Clear user's location from session."""
    if 'user_location' in request.session:
        del request.session['user_location'] 