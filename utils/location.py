import requests
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Extracts the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
        logger.debug(f"Client IP extracted from X-Forwarded-For: {ip}")
    else:
        ip = request.META.get('REMOTE_ADDR')
        logger.debug(f"Client IP extracted from REMOTE_ADDR: {ip}")

    # If running locally, get public IP
    if ip in ["127.0.0.1", "localhost"]:
        try:
            logger.debug("Local IP detected, fetching public IP")
            ip = requests.get("https://api64.ipify.org?format=json").json().get("ip")
            logger.debug(f"Public IP fetched: {ip}")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch public IP: {str(e)}")
            ip = "UNKNOWN"

    return ip

def get_ip_location(ip):
    """Fetches location details for the given IP address using an external API, with caching."""
    
    # Check if IP location is already cached
    cached_location = cache.get(f'ip_location_{ip}')
    if cached_location:
        logger.debug(f"IP location cache hit for IP: {ip}")
        return cached_location  # Return cached result
    
    logger.info(f"Fetching location for IP: {ip}")
    
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=10)
        data = response.json()
        if data["status"] == "success":
            location_data = {
                "ip": ip,
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lng": data.get("lon"),
                "isp": data.get("isp"),
            }
            
            # Cache the result for 1 hour (3600 seconds)
            cache.set(f'ip_location_{ip}', location_data, timeout=3600)
            
            logger.info(f"Location data fetched successfully for IP {ip}: {location_data['city']}, {location_data['country']}")
            return location_data
        else:
            logger.warning(f"IP location API returned error for IP {ip}: {data.get('message', 'Unknown error')}")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch location for IP {ip}: {str(e)}")
        return {"error": "Could not retrieve location data"}
    
    logger.warning(f"Failed to get valid location data for IP: {ip}")
    return {"error": "Invalid IP or failed lookup"}


if __name__ == '__main__':
    ip = '175.114.21.96'
    location = get_ip_location(ip)
    
    print(location)