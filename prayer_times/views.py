from django.shortcuts import render
from .utils import get_prayer_times, get_prayer_times_ll
from utils.location import get_client_ip, get_ip_location
from django.http import JsonResponse
import json

# Create your views here.

def prayer_times(request):
    # Get coordinates from query parameters
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    city = request.GET.get('city')
    
    if lat and lon:
        # If coordinates are provided, use them directly
        data = get_prayer_times_ll(float(lat), float(lon))
        location = {
            "city": data.get("data", {}).get("meta", {}).get("timezone", "").split("/")[-1],
            "country": "South Korea",
            "latitude": lat,
            "longitude": lon
        }
    elif city:
        # If city is provided, use it
        location = {
            "city": city,
            "country": "South Korea"
        }
        data = get_prayer_times(location["city"], location["country"])
    else:
        # Otherwise, try to get location from IP
        ip = get_client_ip(request)
        location = get_ip_location(ip)
        
        # If IP location fails, default to Seoul
        if not location or not location.get("city"):
            location = {
                "city": "Seoul",
                "country": "South Korea"
            }
        data = get_prayer_times(location["city"], location["country"])

    context = {
        'data': data["data"],
        'location': location,
    }
    
    return render(request, 'prayer_times/prayer_times.html', context)

def get_location_from_coords(request):
    """API endpoint to get location data from coordinates"""
    try:
        data = json.loads(request.body)
        lat = data.get('latitude')
        lon = data.get('longitude')
        
        if not lat or not lon:
            return JsonResponse({'error': 'Missing coordinates'}, status=400)
            
        # Get prayer times directly using coordinates
        prayer_data = get_prayer_times_ll(float(lat), float(lon))
        
        if prayer_data and prayer_data.get("data"):
            # Extract city name from timezone
            timezone = prayer_data["data"].get("meta", {}).get("timezone", "")
            city = timezone.split("/")[-1] if timezone else None
            
            return JsonResponse({
                'city': city,
                'latitude': lat,
                'longitude': lon
            })
        else:
            return JsonResponse({'error': 'Could not get prayer times for location'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
