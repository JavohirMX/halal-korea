from django.shortcuts import render
from .utils import get_prayer_times, get_prayer_times_ll, get_fallback_prayer_times
from utils.location_manager import get_user_location_context, get_default_korea_location, update_user_location
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
        
        # Get location context (includes is_in_korea detection)
        location_context = get_user_location_context(request)
        
        # Initial context with loading state
        context = {
            'location_context': location_context,
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
    """API endpoint to get prayer times data - now supports international users"""
    try:
        calculation_method = request.session.get('calculation_method', 3)
        asr_method = request.session.get('asr_method', 1)
        location_context = get_user_location_context(request)
        location = location_context['location']
        is_in_korea = location_context['is_in_korea']
        
        # Primary prayer times - user's actual location
        primary_data = None
        primary_location_info = None
        
        if 'lat' in location and 'lng' in location and not location.get('is_fallback'):
            # Use coordinates for accurate prayer times
            primary_data = get_prayer_times_ll(
                float(location['lat']), 
                float(location['lng']), 
                method=calculation_method, 
                school=asr_method
            )
            primary_location_info = {
                "city": location.get('city', 'Your Location'),
                "country": location.get('country', 'Unknown'),
                "latitude": location['lat'],
                "longitude": location['lng']
            }
        elif location.get('city') and location.get('city') != 'Unknown':
            # Use city-based lookup
            primary_data = get_prayer_times(
                location['city'], 
                location.get('country', 'Unknown'), 
                method=calculation_method, 
                school=asr_method
            )
            primary_location_info = {
                "city": location['city'],
                "country": location.get('country', 'Unknown')
            }
        
        # For international users, also provide Korea prayer times
        korea_data = None
        korea_location_info = None
        
        if not is_in_korea and primary_data:
            try:
                korea_location = get_default_korea_location()
                korea_data = get_prayer_times_ll(
                    korea_location['lat'],
                    korea_location['lng'],
                    method=calculation_method,
                    school=asr_method
                )
                korea_location_info = {
                    "city": korea_location['city'],
                    "country": korea_location['country'],
                    "latitude": korea_location['lat'],
                    "longitude": korea_location['lng']
                }
            except Exception as e:
                logger.warning(f"Failed to get Korea prayer times for international user: {str(e)}")
        
        # If we couldn't get user's location prayer times, fall back
        if not primary_data:
            if is_in_korea:
                # User is in Korea but we couldn't get specific location
                korea_location = get_default_korea_location()
                primary_data = get_prayer_times_ll(
                    korea_location['lat'],
                    korea_location['lng'],
                    method=calculation_method,
                    school=asr_method
                )
                primary_location_info = {
                    "city": korea_location['city'],
                    "country": korea_location['country']
                }
            else:
                # International user with no location data
                primary_data = get_fallback_prayer_times()
                primary_location_info = {
                    "city": "Unknown Location",
                    "country": "Unknown"
                }
        
        response_data = {
            'success': True,
            'data': primary_data["data"],
            'location': primary_location_info,
            'is_in_korea': is_in_korea,
            'user_type': location_context['user_type']
        }
        
        # Add Korea reference data for international users
        if not is_in_korea and korea_data:
            response_data['korea_reference'] = {
                'data': korea_data["data"],
                'location': korea_location_info
            }
            
        return JsonResponse(response_data)
        
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
