from django.shortcuts import render
from .utils import get_prayer_times, get_prayer_times_ll, get_ramadan_prayer_times
from .ramadan_utils import (
    get_active_ramadan_config, is_ramadan_active, get_ramadan_day_number,
    get_ramadan_date_range, is_lailatul_qadr_night, get_ramadan_status,
    strip_timezone_suffix, calculate_fasting_duration,
)
from .ramadan_content import get_dua_for_day, get_tip_for_day
from utils.location_manager import get_user_location_context, get_default_korea_location, update_user_location, get_korea_location_from_coordinates, clear_user_location
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from utils.logging_utils import log_user_action, log_execution
import json
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Create your views here.

@log_execution(level='info', sample=True)  # High-volume endpoint with sampling
def prayer_times(request):
    """Main view for prayer times page"""
    try:
        # Get prayer calculation settings from session
        calculation_method = request.session.get('calculation_method', 3)
        asr_method = request.session.get('asr_method', 1)
        
        # Get location context (includes is_in_korea detection)
        location_context = get_user_location_context(request)
        
        # Log prayer times page access
        log_user_action(
            logger,
            'prayer_times_page_accessed',
            request.user if request.user.is_authenticated else None,
            request,
            extra_data={
                'calculation_method': calculation_method,
                'asr_method': asr_method,
                'is_in_korea': location_context.get('is_in_korea'),
                'user_type': location_context.get('user_type')
            }
        )

        # Ramadan context
        ramadan_status = get_ramadan_status()
        ramadan_context = {'is_ramadan': False, 'is_approaching': False}
        if ramadan_status['status'] == 'during':
            day_num = ramadan_status['day_number']
            ramadan_context = {
                'is_ramadan': True,
                'is_approaching': False,
                'day_number': day_num,
                'total_days': ramadan_status['total_days'],
                'hijri_year': ramadan_status['hijri_year'],
                'is_lailatul_qadr': ramadan_status.get('is_lailatul_qadr', False),
                'dua': get_dua_for_day(day_num),
                'tip': get_tip_for_day(day_num),
            }
        elif ramadan_status['status'] == 'before' and ramadan_status['days_until'] <= 7:
            ramadan_context = {
                'is_ramadan': False,
                'is_approaching': True,
                'days_until': ramadan_status['days_until'],
                'start_date': ramadan_status['start_date'],
                'hijri_year': ramadan_status['hijri_year'],
            }
        
        # Initial context with loading state
        context = {
            'location_context': location_context,
            'prayer_settings': {
                'calculation_method': calculation_method,
                'asr_method': asr_method
            },
            'is_loading': True,
            'ramadan': ramadan_context,
        }
        
        return render(request, 'prayer_times/prayer_times.html', context)
    except Exception as e:
        logger.error(
            "Error in prayer_times view",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e),
                'user': request.user.username if request.user.is_authenticated else None
            },
            exc_info=True
        )
        return render(request, 'prayer_times/error.html', {
            'error': 'Unable to load prayer times',
            'details': str(e)
        })

@require_http_methods(["GET"])
@log_execution(level='info', sample=True)  # High-volume API with sampling
def get_prayer_times_data(request):
    """API endpoint to get prayer times data - now supports international users"""
    try:
        calculation_method = request.session.get('calculation_method', 3)
        asr_method = request.session.get('asr_method', 1)
        location_context = get_user_location_context(request)
        location = location_context['location']
        is_in_korea = location_context['is_in_korea']
        
        # Log API request
        log_user_action(
            logger,
            'api_prayer_times_data_requested',
            request.user if request.user.is_authenticated else None,
            request,
            extra_data={
                'calculation_method': calculation_method,
                'asr_method': asr_method,
                'is_in_korea': is_in_korea,
                'has_coordinates': 'lat' in location and 'lng' in location,
                'has_city': bool(location.get('city'))
            }
        )
        
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
        
        if not is_in_korea and primary_data and primary_data.get('code') == 200:
            try:
                korea_location = get_default_korea_location()
                korea_data = get_prayer_times_ll(
                    korea_location['lat'],
                    korea_location['lng'],
                    method=calculation_method,
                    school=asr_method
                )
                # Only include korea_data if it's successful
                if korea_data.get('code') != 200:
                    korea_data = None
                else:
                    korea_location_info = {
                        "city": korea_location['city'],
                        "country": korea_location['country'],
                        "latitude": korea_location['lat'],
                        "longitude": korea_location['lng']
                    }
            except Exception as e:
                logger.warning(f"Failed to get Korea prayer times for international user: {str(e)}")
        
        # If we couldn't get user's location prayer times, fall back
        if not primary_data or primary_data.get('code') != 200:
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
                # International user with no location data - return error
                return JsonResponse({
                    'success': False,
                    'error': 'Unable to determine your location. Please enable location services or set your location manually.',
                    'show_error_ui': True
                }, status=400)
        
        # Check if primary data is an error response
        if primary_data.get('code') != 200:
            return JsonResponse({
                'success': False,
                'error': primary_data.get('error', 'Failed to load prayer times'),
                'show_error_ui': True
            }, status=503)
        
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

        # Add Ramadan info if active
        ramadan_status = get_ramadan_status()
        if ramadan_status['status'] == 'during':
            timings = primary_data.get("data", {}).get("timings", {})
            imsak = strip_timezone_suffix(timings.get("Imsak", ""))
            maghrib = strip_timezone_suffix(timings.get("Maghrib", ""))
            fh, fm = calculate_fasting_duration(imsak, maghrib)
            response_data['ramadan_info'] = {
                'is_ramadan': True,
                'day_number': ramadan_status['day_number'],
                'total_days': ramadan_status['total_days'],
                'hijri_year': ramadan_status['hijri_year'],
                'is_lailatul_qadr': ramadan_status.get('is_lailatul_qadr', False),
                'imsak': imsak,
                'fasting_duration': f"{fh}h {fm}m" if fh is not None else None,
            }
        
        logger.info(
            "Prayer times data retrieved successfully",
            extra={
                'is_in_korea': is_in_korea,
                'has_korea_reference': not is_in_korea and korea_data is not None,
                'location_type': 'coordinates' if primary_location_info and 'latitude' in primary_location_info else 'city'
            }
        )
            
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(
            "Error in get_prayer_times_data",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e),
                'user': request.user.username if request.user.is_authenticated else None
            },
            exc_info=True
        )
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred. Please try again later.',
            'show_error_ui': True
        }, status=500)

@require_http_methods(["POST"])
@log_execution(level='info', sample=True)  # API endpoint with sampling
def get_location_from_coords(request):
    """API endpoint to get location data from coordinates"""
    try:
        data = json.loads(request.body)
        lat = data.get('latitude')
        lng = data.get('longitude')
        
        if not lat or not lng:
            logger.warning("Missing coordinates in get_location_from_coords request")
            return JsonResponse({'error': 'Missing coordinates'}, status=400)
        
        log_user_action(
            logger,
            'api_location_from_coords_requested',
            request.user if request.user.is_authenticated else None,
            request,
            extra_data={
                'has_latitude': bool(lat),
                'has_longitude': bool(lng)
            }
        )
            
        # Get prayer times directly using coordinates
        prayer_data = get_prayer_times_ll(float(lat), float(lng))
        
        if prayer_data and prayer_data.get("data"):
            location_info = {}
            
            # Try enhanced reverse geocoding for better location data
            reverse_geo = get_korea_location_from_coordinates(float(lat), float(lng))
            
            if reverse_geo:
                # Use enhanced geocoding data
                location_info = {
                    'lat': lat,
                    'lng': lng,
                    'city': reverse_geo.get('city', 'Unknown'),
                    'country': reverse_geo.get('country', 'Unknown')
                }
                logger.info(
                    "Enhanced location data from reverse geocoding",
                    extra={
                        'city': location_info.get('city'),
                        'country': location_info.get('country'),
                        'has_coordinates': True
                    }
                )
            else:
                # Fallback to timezone-based city extraction
                timezone = prayer_data["data"].get("meta", {}).get("timezone", "")
                city = timezone.split("/")[-1] if timezone else "Unknown"
                location_info = {
                    'lat': lat,
                    'lng': lng,
                    'city': city
                }
                logger.debug(
                    "Fallback location data from timezone",
                    extra={'city': city, 'timezone': timezone}
                )
            
            # Update location in session with enhanced data
            update_user_location(request, location_info)
            
            logger.info(
                "Location from coordinates retrieved successfully",
                extra={
                    'geocoding_used': bool(reverse_geo),
                    'city': location_info.get('city')
                }
            )
            
            return JsonResponse({
                'success': True,
                'city': location_info.get('city', 'Unknown'),
                'country': location_info.get('country', 'Unknown'),
                'latitude': lat,
                'longitude': lng
            })
        else:
            logger.warning("Could not get prayer times for provided coordinates")
            return JsonResponse({
                'success': False,
                'error': 'Could not get prayer times for location'
            }, status=404)
            
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in get_location_from_coords",
            extra={'error': str(e)},
            exc_info=True
        )
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.error(
            "Error in get_location_from_coords",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
@log_execution(level='info')  # User preference change - no sampling
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
        
        log_user_action(
            logger,
            'prayer_settings_updated',
            request.user if request.user.is_authenticated else None,
            request,
            extra_data={
                'calculation_method': calculation_method,
                'asr_method': asr_method
            }
        )
            
        return JsonResponse({'success': True})
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in update_prayer_settings",
            extra={'error': str(e)},
            exc_info=True
        )
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.error(
            "Error in update_prayer_settings",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
@log_execution(level='info', sample=True)  # Location updates with sampling
def update_location(request):
    """API endpoint to update location"""
    try:
        data = json.loads(request.body)
        city = data.get('city')
        country = data.get('country')  # Optional country parameter
        
        if not city:
            logger.warning("Missing city in update_location request")
            return JsonResponse({
                'success': False,
                'error': 'Missing city'
            }, status=400)
            
        # Prepare location data
        location_data = {'city': city}
        if country:
            location_data['country'] = country
        
        log_user_action(
            logger,
            'location_updated_manually',
            request.user if request.user.is_authenticated else None,
            request,
            extra_data={
                'city': city,
                'country': country,
                'method': 'manual'
            }
        )
            
        # Update location in session
        update_user_location(request, location_data)
            
        return JsonResponse({'success': True})
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in update_location",
            extra={'error': str(e)},
            exc_info=True
        )
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.error(
            "Error in update_location",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
@log_execution(level='info')  # Location clearing - no sampling
def clear_location(request):
    """API endpoint to clear user location from session"""
    try:
        clear_user_location(request)
        
        log_user_action(
            logger,
            'location_cleared',
            request.user if request.user.is_authenticated else None,
            request,
            extra_data={'action': 'clear_location'}
        )
        
        logger.info("User location cleared from session")
        return JsonResponse({'success': True, 'message': 'Location cleared successfully'})
    except Exception as e:
        logger.error(
            "Error in clear_location",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ── Ramadan Views ──────────────────────────────────────────────────────

KOREA_CITIES = [
    {"name": "Seoul", "country": "South Korea"},
    {"name": "Busan", "country": "South Korea"},
    {"name": "Incheon", "country": "South Korea"},
    {"name": "Daegu", "country": "South Korea"},
    {"name": "Daejeon", "country": "South Korea"},
    {"name": "Gwangju", "country": "South Korea"},
    {"name": "Ulsan", "country": "South Korea"},
    {"name": "Suwon", "country": "South Korea"},
    {"name": "Sejong", "country": "South Korea"},
    {"name": "Jeju", "country": "South Korea"},
]


@log_execution(level='info', sample=True)
def ramadan_timetable(request):
    """Ramadan timetable page"""
    try:
        config = get_active_ramadan_config()
        ramadan_status = get_ramadan_status()
        calculation_method = request.session.get('calculation_method', 3)
        asr_method = request.session.get('asr_method', 1)
        location_context = get_user_location_context(request)

        today_dua = None
        today_tip = None
        if ramadan_status['status'] == 'during':
            day_num = ramadan_status['day_number']
            today_dua = get_dua_for_day(day_num)
            today_tip = get_tip_for_day(day_num)

        user_location = location_context.get('location', {})
        detected_city = user_location.get('city', 'Seoul')
        korea_city_names = [c['name'] for c in KOREA_CITIES]
        if detected_city not in korea_city_names:
            detected_city = 'Seoul'

        context = {
            'ramadan_config': config,
            'ramadan_status': ramadan_status,
            'korea_cities': KOREA_CITIES,
            'detected_city': detected_city,
            'today_dua': today_dua,
            'today_tip': today_tip,
            'prayer_settings': {
                'calculation_method': calculation_method,
                'asr_method': asr_method,
            },
        }
        return render(request, 'prayer_times/ramadan_timetable.html', context)
    except Exception as e:
        logger.error("Error in ramadan_timetable view", exc_info=True)
        return render(request, 'prayer_times/error.html', {
            'error': 'Unable to load Ramadan timetable',
            'details': str(e),
        })


@require_http_methods(["GET"])
@log_execution(level='info', sample=True)
def get_ramadan_calendar_data(request):
    """API endpoint returning the full Ramadan calendar JSON for a given city."""
    try:
        config = get_active_ramadan_config()
        if not config:
            return JsonResponse({'success': False, 'error': 'Ramadan is not configured.'}, status=404)

        city = request.GET.get('city', 'Seoul')
        country = request.GET.get('country', 'South Korea')
        calculation_method = request.session.get('calculation_method', 3)
        asr_method = request.session.get('asr_method', 1)

        date_range = get_ramadan_date_range()
        if not date_range:
            return JsonResponse({'success': False, 'error': 'No Ramadan dates configured.'}, status=404)

        calendar_data = get_ramadan_prayer_times(
            city, country, date_range,
            method=calculation_method, school=asr_method,
        )

        days = []
        for day in calendar_data:
            entry = {
                'day_number': day['day_number'],
                'date': day['date'].isoformat(),
                'date_str': day['date_str'],
                'weekday': day['weekday'],
                'is_lailatul_qadr': is_lailatul_qadr_night(day['day_number']),
            }
            if day.get('timings'):
                t = day['timings']
                hours, mins = calculate_fasting_duration(t.get('Imsak', ''), t.get('Maghrib', ''))
                entry['timings'] = {
                    'Imsak': t.get('Imsak', ''),
                    'Fajr': t.get('Fajr', ''),
                    'Sunrise': t.get('Sunrise', ''),
                    'Dhuhr': t.get('Dhuhr', ''),
                    'Asr': t.get('Asr', ''),
                    'Maghrib': t.get('Maghrib', ''),
                    'Isha': t.get('Isha', ''),
                }
                entry['fasting_duration'] = f"{hours}h {mins}m" if hours is not None else None
            else:
                entry['error'] = True
            days.append(entry)

        today = date.today()
        ramadan_status = get_ramadan_status()

        return JsonResponse({
            'success': True,
            'config': {
                'hijri_year': config.hijri_year,
                'start_date': config.start_date.isoformat(),
                'end_date': config.end_date.isoformat(),
                'total_days': config.total_days,
            },
            'city': city,
            'country': country,
            'today': today.isoformat(),
            'ramadan_status': ramadan_status.get('status'),
            'current_day': ramadan_status.get('day_number'),
            'days': days,
        })
    except Exception as e:
        logger.error("Error in get_ramadan_calendar_data", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@log_execution(level='info')
def download_ramadan_image(request):
    """Generate and return a branded PNG of the full Ramadan timetable."""
    try:
        config = get_active_ramadan_config()
        if not config:
            return JsonResponse({'error': 'Ramadan is not configured.'}, status=404)

        city = request.GET.get('city', 'Seoul')
        country = request.GET.get('country', 'South Korea')
        calculation_method = request.session.get('calculation_method', 3)
        asr_method = request.session.get('asr_method', 1)

        from django.utils.translation import get_language
        language = get_language() or 'en'

        from django.core.cache import cache
        cache_key = f"ramadan_img_{city}_{calculation_method}_{asr_method}_{language}".replace(' ', '_')
        cached_img = cache.get(cache_key)
        if cached_img:
            response = HttpResponse(cached_img, content_type='image/png')
            response['Content-Disposition'] = f'attachment; filename="ramadan-timetable-{city.lower()}-{config.year}.png"'
            return response

        date_range = get_ramadan_date_range()
        calendar_data = get_ramadan_prayer_times(
            city, country, date_range,
            method=calculation_method, school=asr_method,
        )

        from .ramadan_image import generate_ramadan_timetable_image
        img_bytes = generate_ramadan_timetable_image(config, city, country, calendar_data, language=language)

        cache.set(cache_key, img_bytes, 3600)

        response = HttpResponse(img_bytes, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="ramadan-timetable-{city.lower()}-{config.year}.png"'
        return response
    except Exception as e:
        logger.error("Error generating Ramadan image", exc_info=True)
        return JsonResponse({'error': 'Failed to generate image.'}, status=503)
