import requests
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Extracts the client's IP address from the request."""
    logger.debug("Extracting client IP address from request")
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP if there are multiple (proxy chain)
        ip = x_forwarded_for.split(',')[0].strip()
        logger.debug(f"Client IP extracted from X-Forwarded-For header: {ip}")
    else:
        ip = request.META.get('REMOTE_ADDR')
        logger.debug(f"Client IP extracted from REMOTE_ADDR: {ip}")

    # If running locally, get public IP for testing
    if ip in ["127.0.0.1", "localhost", None]:
        logger.debug("Local or null IP detected, attempting to fetch public IP for development")
        try:
            response = requests.get("https://api64.ipify.org?format=json", timeout=5)
            public_ip = response.json().get("ip")
            if public_ip:
                logger.info(f"Public IP fetched for development: {public_ip} (original: {ip})")
                ip = public_ip
            else:
                logger.warning("Failed to get public IP from ipify service")
                ip = "UNKNOWN"
        except requests.RequestException as e:
            logger.error(f"Failed to fetch public IP: {str(e)}")
            ip = "UNKNOWN"
        except Exception as e:
            logger.error(f"Unexpected error fetching public IP: {str(e)}")
            ip = "UNKNOWN"

    logger.debug(f"Final client IP determined: {ip}")
    return ip

def get_ip_location(ip):
    """Fetches location details for the given IP address using an external API, with caching."""
    
    # Check if IP location is already cached
    cached_location = cache.get(f'ip_location_{ip}')
    if cached_location:
        logger.debug(f"IP location cache hit for IP: {ip} -> {cached_location.get('city', 'Unknown')}, {cached_location.get('country', 'Unknown')}")
        return cached_location  # Return cached result
    
    logger.info(f"Fetching location for IP: {ip} (cache miss)")
    
    try:
        logger.debug(f"Making API call to ip-api.com for IP: {ip}")
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=10)
        data = response.json()
        
        logger.debug(f"IP API response status: {data.get('status')} for IP: {ip}")
        
        if data["status"] == "success":
            location_data = {
                "ip": ip,
                "country": data.get("country"),
                "country_code": data.get("countryCode"),  # Add ISO country code
                "region": data.get("regionName"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lng": data.get("lon"),
                "isp": data.get("isp"),
            }
            
            # Cache the result for 1 hour (3600 seconds)
            cache.set(f'ip_location_{ip}', location_data, timeout=3600)
            
            logger.info(f"Location data fetched successfully for IP {ip}: {location_data['city']}, {location_data['country']} ({location_data.get('country_code', 'N/A')})")
            logger.debug(f"Full location data for IP {ip}: lat={location_data.get('lat')}, lng={location_data.get('lng')}, region={location_data.get('region')}, isp={location_data.get('isp')}")
            
            return location_data
        else:
            error_msg = data.get('message', 'Unknown error')
            logger.warning(f"IP location API returned error for IP {ip}: {error_msg}")
            return {"error": f"API error: {error_msg}"}
    except requests.RequestException as e:
        logger.error(f"Network error while fetching location for IP {ip}: {str(e)}")
        return {"error": "Could not retrieve location data"}
    except Exception as e:
        logger.error(f"Unexpected error while processing location for IP {ip}: {str(e)}")
        return {"error": "Processing error"}
    
    logger.warning(f"Failed to get valid location data for IP: {ip}")
    return {"error": "Invalid IP or failed lookup"}


if __name__ == '__main__':
    ip = '175.114.21.96'
    location = get_ip_location(ip)
    
    print(location)