from django.shortcuts import render
from .utils import get_prayer_times, get_prayer_times_ll
from utils.location_manager import get_user_location, update_user_location
from django.http import JsonResponse
import json

# Create your views here.

def prayer_times(request):
    # Get prayer calculation settings from session
    calculation_method = request.session.get('calculation_method', 3)  # Default to Muslim World League
    asr_method = request.session.get('asr_method', 1)  # Default to Hanafi
    
    # Get location from session or IP
    location = get_user_location(request)
    
    # Get prayer times based on location type
    if 'lat' in location and 'lng' in location:
        data = get_prayer_times_ll(float(location['lat']), float(location['lng']), method=calculation_method, school=asr_method)
        location_info = {
            "city": data.get("data", {}).get("meta", {}).get("timezone", "").split("/")[-1],
            "country": "South Korea",
            "latitude": location['lat'],
            "longitude": location['lng']
        }
    else:
        location_info = {
            "city": location['city'],
            "country": "South Korea"
        }
        data = get_prayer_times(location_info["city"], location_info["country"], method=calculation_method, school=asr_method)

    context = {
        'data': data["data"],
        'location': location_info,
        'prayer_settings': {
            'calculation_method': calculation_method,
            'asr_method': asr_method
        }
    }
    
    return render(request, 'prayer_times/prayer_times.html', context)

def get_location_from_coords(request):
    """API endpoint to get location data from coordinates"""
    try:
        data = json.loads(request.body)
        lat = data.get('latitude')
        lng = data.get('longitude')
        
        if not lat or not lng:
            return JsonResponse({'error': 'Missing coordinates'}, status=400)
            
        # Get prayer times directly using coordinates
        prayer_data = get_prayer_times_ll(float(lat), float(lng))
        
        if prayer_data and prayer_data.get("data"):
            # Extract city name from timezone
            timezone = prayer_data["data"].get("meta", {}).get("timezone", "")
            city = timezone.split("/")[-1] if timezone else None
            
            # Update location in session
            location = update_user_location(request, {  # noqa: F841
                'lat': lat,
                'lng': lng,
                'city': city
            })
            
            return JsonResponse({
                'city': city,
                'latitude': lat,
                'longitude': lng
            })
        else:
            return JsonResponse({'error': 'Could not get prayer times for location'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def update_prayer_settings(request):
    """API endpoint to update prayer calculation settings"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        calculation_method = data.get('calculation_method')
        asr_method = data.get('asr_method')
        
        if calculation_method is not None:
            request.session['calculation_method'] = int(calculation_method)
        if asr_method is not None:
            request.session['asr_method'] = int(asr_method)
            
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def update_location(request):
    """API endpoint to update location"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        city = data.get('city')
        
        if not city:
            return JsonResponse({'error': 'Missing city'}, status=400)
            
        # Update location in session
        location = update_user_location(request, {'city': city})  # noqa: F841
            
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
