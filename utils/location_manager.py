from utils.location import get_client_ip, get_ip_location
import time

def is_user_in_korea(location_data):
    """
    Determine if user is currently in Korea based on location data.
    Uses multiple methods: country name, coordinates, and reverse geocoding.
    Returns True if user is in Korea, False if international.
    """
    if not location_data or location_data.get("error"):
        return False  # If we can't determine location, assume international
    
    # Method 1: Check country code first (most reliable)
    country_code = location_data.get("country_code", "").upper()
    if country_code == "KR":
        return True
    
    # Method 1b: Check country field if available
    country = location_data.get("country", "").lower()
    if country:
        korea_indicators = ["south korea", "korea", "korean", "republic of korea"]
        if any(indicator in country for indicator in korea_indicators):
            return True
    
    # Method 2: Check coordinates if country is missing or unclear
    lat = location_data.get("lat")
    lng = location_data.get("lng")
    
    if lat is not None and lng is not None:
        return _is_coordinate_in_korea(float(lat), float(lng))
    
    # Method 3: If we have city but no clear country, try reverse geocoding
    city = location_data.get("city", "").lower()
    if city and not country:
        return _is_city_in_korea(city)
    
    return False  # Default to international if unclear

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
    Enhanced to fill in missing country information for coordinates.
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
        
        # If country is missing but we have coordinates, try to determine it
        if 'country' not in location_data or not location_data['country']:
            if _is_coordinate_in_korea(float(location_data['lat']), float(location_data['lng'])):
                # Try reverse geocoding to get proper location info
                reverse_geo = get_korea_location_from_coordinates(
                    float(location_data['lat']), 
                    float(location_data['lng'])
                )
                if reverse_geo:
                    location.update(reverse_geo)
                else:
                    # Fallback to basic Korea info
                    location['country'] = 'South Korea'
                    if 'city' not in location_data:
                        location['city'] = 'Unknown City'
    
    if 'city' in location_data:
        location['city'] = location_data['city']
        
    if 'country' in location_data:
        location['country'] = location_data['country']
    
    request.session['user_location'] = location
    return location

def _is_coordinate_in_korea(lat, lng):
    """
    Check if given coordinates fall within South Korea's boundaries.
    Uses approximate bounding box for South Korea.
    """
    # South Korea approximate boundaries
    # These coordinates cover mainland South Korea including Jeju Island
    KOREA_BOUNDS = {
        'north': 38.612,   # Northern border with North Korea
        'south': 33.0,     # Southern tip including Jeju Island
        'east': 131.87,    # Eastern coast
        'west': 124.5      # Western coast
    }
    
    return (KOREA_BOUNDS['south'] <= lat <= KOREA_BOUNDS['north'] and 
            KOREA_BOUNDS['west'] <= lng <= KOREA_BOUNDS['east'])

def _is_city_in_korea(city):
    """
    Check if a city name suggests it's in Korea.
    This is a basic fallback for when we have city but no country.
    """
    korean_city_indicators = [
        'seoul', 'busan', 'incheon', 'daegu', 'daejeon', 'gwangju',
        'ulsan', 'sejong', 'suwon', 'goyang', 'yongin', 'changwon',
        'jeju', 'cheongju', 'cheonan', 'jeonju', 'ansan', 'pohang',
        'gimhae', 'pyeongtaek', 'siheung', 'bucheon', 'anyang'
    ]
    
    return any(korean_city in city for korean_city in korean_city_indicators)

def get_korea_location_from_coordinates(lat, lng):
    """
    Enhanced reverse geocoding for coordinates in Korea.
    Returns location data with Korea country information.
    """
    try:
        import requests
        from django.core.cache import cache
        
        # Check cache first
        cache_key = f'reverse_geocode_{lat}_{lng}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Use a free reverse geocoding service
        response = requests.get(
            'https://api.bigdatacloud.net/data/reverse-geocode-client',
            params={'latitude': lat, 'longitude': lng, 'localityLanguage': 'en'},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            result = {
                'country': data.get('countryName', 'South Korea'),
                'city': data.get('city', data.get('locality', 'Unknown')),
                'lat': lat,
                'lng': lng,
                'is_reverse_geocoded': True
            }
            
            # Cache for 24 hours since coordinates don't change
            cache.set(cache_key, result, timeout=86400)
            return result
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'Reverse geocoding failed for {lat}, {lng}: {str(e)}')
    
    # Fallback: if coordinates are in Korea, assume Korea
    if _is_coordinate_in_korea(lat, lng):
        return {
            'country': 'South Korea',
            'city': 'Unknown City',
            'lat': lat,
            'lng': lng,
            'is_fallback': True
        }
    
    return None

def clear_user_location(request):
    """Clear user's location from session."""
    if 'user_location' in request.session:
        del request.session['user_location'] 