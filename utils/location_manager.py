from utils.location import (
    get_client_ip,
    get_ip_location,
    is_bot_or_non_page_request,
    schedule_geo_lookup,
    wait_for_ip_location,
)
import time
import logging

logger = logging.getLogger(__name__)

# Upper bound for the opt-in wait, in seconds. Only endpoints that cannot answer
# without coordinates pass wait_for_lookup=True.
LOCATION_LOOKUP_WAIT_SECONDS = 2.0


def _FALLBACK_LOCATION():
    return {"city": "Unknown", "country": "Unknown", "is_fallback": True}


def is_user_in_korea(location_data):
    """
    Determine if user is currently in Korea based on location data.
    Uses multiple methods: country name, coordinates, and reverse geocoding.
    Returns True if user is in Korea, False if international.
    """
    logger.debug(f"Checking if user is in Korea with data: {location_data}")

    if (
        not location_data
        or location_data.get("error")
        or location_data.get("lookup_failed")
    ):
        logger.debug("No location data or lookup failed, assuming international user")
        return False  # If we can't determine location, assume international

    # Method 1: Check country code first (most reliable)
    country_code = location_data.get("country_code", "").upper()
    if country_code == "KR":
        logger.info(f"User detected in Korea via country code: {country_code}")
        return True
    elif country_code:
        logger.debug(f"User not in Korea, country code: {country_code}")

    # Method 1b: Check country field if available
    country = location_data.get("country", "").lower()
    if country:
        korea_indicators = ["south korea", "korea", "korean", "republic of korea"]
        if any(indicator in country for indicator in korea_indicators):
            logger.info(
                f"User detected in Korea via country name: {location_data.get('country')}"
            )
            return True
        else:
            logger.debug(f"User not in Korea, country: {location_data.get('country')}")

    # Method 2: Check coordinates if country is missing or unclear
    lat = location_data.get("lat")
    lng = location_data.get("lng")

    if lat is not None and lng is not None:
        logger.debug(f"Checking coordinates for Korea location: lat={lat}, lng={lng}")
        coord_result = _is_coordinate_in_korea(float(lat), float(lng))
        if coord_result:
            logger.info(f"User detected in Korea via coordinates: lat={lat}, lng={lng}")
        else:
            logger.debug(f"Coordinates not in Korea: lat={lat}, lng={lng}")
        return coord_result

    # Method 3: If we have city but no clear country, try reverse geocoding
    city = location_data.get("city", "").lower()
    if city and not country:
        logger.debug(f"Checking city name for Korea indicators: {city}")
        city_result = _is_city_in_korea(city)
        if city_result:
            logger.info(
                f"User detected in Korea via city name: {location_data.get('city')}"
            )
        else:
            logger.debug(f"City not recognized as Korean: {location_data.get('city')}")
        return city_result

    logger.debug("Unable to determine Korea location, defaulting to international")
    return False  # Default to international if unclear


def get_user_location_context(request, wait_for_lookup=False):
    """
    Get comprehensive location context including whether user is in Korea.
    Returns a dictionary with location info and user context.

    wait_for_lookup=True lets this call wait up to LOCATION_LOOKUP_WAIT_SECONDS
    for a background lookup to finish. Only endpoints that cannot produce an
    answer without coordinates should set it.
    """
    logger.debug("Getting user location context")
    location = get_user_location(request, wait_for_lookup=wait_for_lookup)
    is_in_korea = is_user_in_korea(location)

    user_type = "local" if is_in_korea else "international"
    logger.info(
        f"User location context determined: user_type={user_type}, is_in_korea={is_in_korea}"
    )

    return {"location": location, "is_in_korea": is_in_korea, "user_type": user_type}


def _promote_cached_location(request, location):
    """Store a usable cached location in the session and return it.

    Returns None when the cached value is a failure marker or has no city.
    """
    if not location or location.get("lookup_failed") or not location.get("city"):
        return None

    location = dict(location)
    location["is_fallback"] = False
    location["timestamp"] = time.time()
    request.session["user_location"] = location
    return location


def get_user_location(request, wait_for_lookup=False):
    """
    Get the user's location. This function makes no network call of its own.

    Resolution order:
      1. Bot or non-page request, or a development override -> immediate return
      2. Session value that is less than 1 hour old
      3. Shared cache lookup for the client IP
      4. Cache miss -> schedule a background lookup and return the fallback

    The fallback is never written to the session, so the next request can pick up
    the real result as soon as the background task has finished.

    wait_for_lookup=True additionally waits for the background task to publish a
    result, up to LOCATION_LOOKUP_WAIT_SECONDS. This keeps the prayer times
    endpoint working for visitors who decline the browser location prompt.
    """
    # Skip lookups entirely for bots and non-page requests. Do not schedule a
    # background task for these either.
    if is_bot_or_non_page_request(request):
        logger.debug("Bot or non-page request detected, using fallback location")
        return _FALLBACK_LOCATION()

    # Development override for testing international users
    if request.GET.get("force_international"):
        return {
            "ip": "8.8.8.8",
            "country": "United States",
            "country_code": "US",
            "region": "Virginia",
            "city": "Ashburn",
            "lat": 39.03,
            "lng": -77.5,
            "is_fallback": False,
            "timestamp": time.time(),
        }

    if request.GET.get("force_korea"):
        return {
            "ip": "175.114.21.96",
            "country": "South Korea",
            "country_code": "KR",
            "region": "Seoul",
            "city": "Mapo-gu",
            "lat": 37.5681,
            "lng": 126.8998,
            "is_fallback": False,
            "timestamp": time.time(),
        }

    # Check session for saved location
    session_loc = request.session.get("user_location")

    if (
        session_loc and time.time() - session_loc.get("timestamp", 0) < 3600
    ):  # Check if not expired (1 hour)
        logger.debug(
            f"Using cached location from session: {session_loc.get('city', 'Unknown')}, {session_loc.get('country', 'Unknown')}"
        )
        return session_loc

    logger.debug("No valid cached location in session, checking shared cache")

    # Cache read only. This call never makes a network request.
    ip = get_client_ip(request)
    logger.debug(f"Detected client IP: {ip}")
    location = get_ip_location(ip)

    # Enhanced fallback logic for international users
    if (
        not location
        or location.get("error")
        or location.get("lookup_failed")
        or not location.get("city")
    ):
        # Cache miss, cached failure, or unusable result. Schedule the lookup for
        # the background and return the fallback now. The visitor does not wait.
        schedule_geo_lookup(ip)
        logger.info(f"No cached location for IP {ip}, returning fallback")

        if wait_for_lookup:
            # This endpoint cannot answer without coordinates, so give the
            # background task a short window to publish a result.
            waited = wait_for_ip_location(ip, LOCATION_LOOKUP_WAIT_SECONDS)
            promoted = _promote_cached_location(request, waited)
            if promoted:
                logger.info(
                    f"Waited for the background lookup: {promoted.get('city')}, {promoted.get('country')}"
                )
                return promoted
            logger.warning(
                f"Waited {LOCATION_LOOKUP_WAIT_SECONDS}s for IP {ip} with no usable result"
            )

        # For development/unknown cases, provide a neutral fallback.
        # This value is deliberately NOT stored in the session. Storing it would
        # hide the real result for the next hour.
        return _FALLBACK_LOCATION()

    # Mark as detected from IP
    promoted = _promote_cached_location(request, location)
    logger.info(
        f"Successfully retrieved location from IP {ip}: {promoted.get('city')}, {promoted.get('country')}"
    )
    logger.debug("Location saved to session")

    return promoted


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
        "is_default_korea": True,
    }


def update_user_location(request, location_data):
    """
    Update user's location in session.
    Enhanced to fill in missing country information for coordinates.
    location_data should be a dictionary containing at least 'city' or both 'lat' and 'lng'.
    """
    # Skip reverse geocoding and session writes for bots and non-page requests
    if is_bot_or_non_page_request(request):
        logger.debug("Bot or non-page request detected, skipping location update")
        return {"is_fallback": True}

    logger.info(f"Updating user location with data: {location_data}")

    location = {"timestamp": time.time()}

    if "lat" in location_data and "lng" in location_data:
        location.update({"lat": location_data["lat"], "lng": location_data["lng"]})

        logger.debug(
            f"Processing coordinates: lat={location_data['lat']}, lng={location_data['lng']}"
        )

        # If country is missing but we have coordinates, try to determine it
        if "country" not in location_data or not location_data["country"]:
            logger.debug(
                "Country information missing, checking if coordinates are in Korea"
            )

            if _is_coordinate_in_korea(
                float(location_data["lat"]), float(location_data["lng"])
            ):
                logger.debug(
                    "Coordinates detected in Korea, attempting reverse geocoding"
                )

                # Try reverse geocoding to get proper location info
                reverse_geo = get_korea_location_from_coordinates(
                    float(location_data["lat"]), float(location_data["lng"])
                )
                if reverse_geo:
                    logger.info(
                        f"Enhanced location data with reverse geocoding: {reverse_geo['city']}, {reverse_geo['country']}"
                    )
                    location.update(reverse_geo)
                else:
                    # Fallback to basic Korea info
                    logger.debug("Reverse geocoding failed, using basic Korea fallback")
                    location["country"] = "South Korea"
                    if "city" not in location_data:
                        location["city"] = "Unknown City"
            else:
                logger.debug("Coordinates not detected in Korea")

    if "city" in location_data:
        location["city"] = location_data["city"]

    if "country" in location_data:
        location["country"] = location_data["country"]
    elif "city" in location_data and location_data["city"]:
        # Auto-detect country for Korean cities if country is missing
        city_name = location_data["city"].lower()
        if _is_city_in_korea(city_name):
            logger.debug(
                f"Auto-detected Korean city: {location_data['city']}, setting country to South Korea"
            )
            location["country"] = "South Korea"

    request.session["user_location"] = location
    logger.info(
        f"User location updated successfully: {location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    )

    return location


def _is_coordinate_in_korea(lat, lng):
    """
    Check if given coordinates fall within South Korea's boundaries.
    Uses approximate bounding box for South Korea.
    """
    logger.debug(f"Checking if coordinates ({lat}, {lng}) are within Korea bounds")

    # South Korea approximate boundaries
    # These coordinates cover mainland South Korea including Jeju Island
    KOREA_BOUNDS = {
        "north": 38.612,  # Northern border with North Korea
        "south": 33.0,  # Southern tip including Jeju Island
        "east": 131.87,  # Eastern coast
        "west": 124.5,  # Western coast
    }

    in_korea = (
        KOREA_BOUNDS["south"] <= lat <= KOREA_BOUNDS["north"]
        and KOREA_BOUNDS["west"] <= lng <= KOREA_BOUNDS["east"]
    )

    if in_korea:
        logger.debug(f"Coordinates ({lat}, {lng}) are within Korea bounds")
    else:
        logger.debug(f"Coordinates ({lat}, {lng}) are outside Korea bounds")

    return in_korea


def _is_city_in_korea(city):
    """
    Check if a city name suggests it's in Korea.
    This is a basic fallback for when we have city but no country.
    """
    logger.debug(f"Checking if city '{city}' is a Korean city")

    korean_city_indicators = [
        "seoul",
        "busan",
        "incheon",
        "daegu",
        "daejeon",
        "gwangju",
        "ulsan",
        "sejong",
        "suwon",
        "goyang",
        "yongin",
        "changwon",
        "jeju",
        "cheongju",
        "cheonan",
        "jeonju",
        "ansan",
        "pohang",
        "gimhae",
        "pyeongtaek",
        "siheung",
        "bucheon",
        "anyang",
    ]

    is_korean_city = any(korean_city in city for korean_city in korean_city_indicators)

    if is_korean_city:
        logger.debug(f"City '{city}' recognized as Korean city")
    else:
        logger.debug(f"City '{city}' not recognized as Korean city")

    return is_korean_city


def get_korea_location_from_coordinates(lat, lng):
    """
    Enhanced reverse geocoding for coordinates in Korea.
    Returns location data with Korea country information.
    """
    logger.debug(f"Attempting reverse geocoding for coordinates: {lat}, {lng}")

    try:
        import requests
        from django.core.cache import cache

        # Check cache first
        cache_key = f"reverse_geocode_{lat}_{lng}"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(f"Found cached reverse geocoding result for {lat}, {lng}")
            return cached_result

        logger.debug(f"Making reverse geocoding API call for {lat}, {lng}")

        # Use a free reverse geocoding service
        response = requests.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client",
            params={"latitude": lat, "longitude": lng, "localityLanguage": "en"},
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            result = {
                "country": data.get("countryName", "South Korea"),
                "city": data.get("city", data.get("locality", "Unknown")),
                "lat": lat,
                "lng": lng,
                "is_reverse_geocoded": True,
            }

            logger.info(
                f"Reverse geocoding successful for {lat}, {lng}: {result['city']}, {result['country']}"
            )

            # Cache for 24 hours since coordinates don't change
            cache.set(cache_key, result, timeout=86400)
            return result
        else:
            logger.warning(
                f"Reverse geocoding API returned status {response.status_code} for {lat}, {lng}"
            )

    except Exception as e:
        logger.warning(f"Reverse geocoding failed for {lat}, {lng}: {str(e)}")

    # Fallback: if coordinates are in Korea, assume Korea
    if _is_coordinate_in_korea(lat, lng):
        logger.debug(f"Using coordinate fallback for Korea location: {lat}, {lng}")
        return {
            "country": "South Korea",
            "city": "Unknown City",
            "lat": lat,
            "lng": lng,
            "is_fallback": True,
        }

    logger.debug(f"No reverse geocoding result available for {lat}, {lng}")
    return None


def clear_user_location(request):
    """Clear user's location from session."""
    if "user_location" in request.session:
        del request.session["user_location"]
