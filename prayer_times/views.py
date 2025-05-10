from django.shortcuts import render
from .utils import get_prayer_times, get_prayer_times_ll, get_fallback_prayer_times
from utils.location_manager import get_user_location, update_user_location
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import logging

logger = logging.getLogger(__name__)

# Create your views here.

def prayer_times(request):
    """Main view for prayer times page"""
    try:
        # Get prayer calculation settings from session
        calculation_method = request.session.get('calculation_method', 3)
        asr_method = request.session.get('asr_method', 1)
        
        # Get location from session or IP
        location = get_user_location(request)
        
        # Initial context with loading state
        context = {
            'location': location,
            'prayer_settings': {
                'calculation_method': calculation_method,
                'asr_method': asr_method
            },
            'is_loading': True
        }
        
        return render(request, 'prayer_times/prayer_times.html', context)
    except Exception as e:
        logger.error(f"Error in prayer_times view: {str(e)}")
        return render(request, 'prayer_times/error.html', {
            'error': 'Unable to load prayer times',
            'details': str(e)
        })

@require_http_methods(["GET"])
def get_prayer_times_data(request):
    """API endpoint to get prayer times data"""
    try:
        calculation_method = request.session.get('calculation_method', 3)
        asr_method = request.session.get('asr_method', 1)
        location = get_user_location(request)
        
        if 'lat' in location and 'lng' in location:
            data = get_prayer_times_ll(
                float(location['lat']), 
                float(location['lng']), 
                method=calculation_method, 
                school=asr_method
            )
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
            data = get_prayer_times(
                location_info["city"], 
                location_info["country"], 
                method=calculation_method, 
                school=asr_method
            )
            
        return JsonResponse({
            'success': True,
            'data': data["data"],
            'location': location_info
        })
    except Exception as e:
        logger.error(f"Error in get_prayer_times_data: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load prayer times',
            'fallback_data': get_fallback_prayer_times()["data"]
        }, status=500)

@require_http_methods(["POST"])
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
            update_user_location(request, {
                'lat': lat,
                'lng': lng,
                'city': city
            })
            
            return JsonResponse({
                'success': True,
                'city': city,
                'latitude': lat,
                'longitude': lng
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Could not get prayer times for location'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Error in get_location_from_coords: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
def update_prayer_settings(request):
    """API endpoint to update prayer calculation settings"""
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
        logger.error(f"Error in update_prayer_settings: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
def update_location(request):
    """API endpoint to update location"""
    try:
        data = json.loads(request.body)
        city = data.get('city')
        
        if not city:
            return JsonResponse({
                'success': False,
                'error': 'Missing city'
            }, status=400)
            
        # Update location in session
        update_user_location(request, {'city': city})
            
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error in update_location: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
