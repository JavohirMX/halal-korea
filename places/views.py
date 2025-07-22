from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Q
from django.contrib.auth import get_user_model
from .models import HalalPlace
from reviews.models import Review
from .forms import HalalPlaceForm
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
from django.db.models.functions import Round
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.http import JsonResponse
from utils.location_manager import get_user_location_context, update_user_location
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string
import json
import logging
from utils.telegram_notifications import send_new_place_notification

User = get_user_model()
logger = logging.getLogger(__name__)

def home(request):
    """Main home page view showing featured places with international user support"""
    try:
        logger.info(f"Home page accessed by user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
        
        # Get user location context (includes international user detection)
        location_context = get_user_location_context(request)
        location = location_context['location']
        is_in_korea = location_context['is_in_korea']
        user_location = None
        
        if 'lat' in location and 'lng' in location and not location.get('is_fallback'):
            user_location = Point(location['lng'], location['lat'], srid=4326)
            logger.debug(f"User location determined: lat={location['lat']}, lng={location['lng']}")

        # Get featured places with different logic for Korea vs international users
        featured_places = HalalPlace.objects.filter(
            status='approved'
        ).annotate(
            average_rating=Round(Avg('reviews__rating'), 1)
        )

        # Different sorting logic based on user location
        if is_in_korea and user_location:
            # For Korea users: distance-based recommendations
            featured_places = featured_places.annotate(
                distance=Distance('location', user_location)
            ).order_by('distance')[:6]
            logger.debug("Featured places ordered by distance for Korea user")
        else:
            # For international users: popular/highly-rated places
            featured_places = featured_places.order_by('-average_rating', '-created_at')[:6]
            logger.debug("Featured places ordered by rating for international user")
        
        logger.info(f"Home page rendered with {featured_places.count()} featured places")
        return render(request, 'places/home.html', {
            'featured_places': featured_places,
            'location_context': location_context,
        })
    except Exception as e:
        logger.error(f"Error in home view: {str(e)}", exc_info=True)
        return render(request, 'places/error.html', {
            'error': 'Unable to load home page',
            'details': str(e)
        })

def explore(request):
    # Get filter parameters
    category = request.GET.get('category')
    search_query = request.GET.get('q', '')
    city_filter = request.GET.get('city', '')  # New city filter
    sort = request.GET.get('sort', 'distance')  # Default to distance sorting
    page = request.GET.get('page', 1)
    
    # Get user location context
    location_context = get_user_location_context(request)
    location = location_context['location']
    is_in_korea = location_context['is_in_korea']
    user_location = None
    
    if 'lat' in location and 'lng' in location and not location.get('is_fallback'):
        user_location = Point(location['lng'], location['lat'], srid=4326)

    # Base queryset
    places = HalalPlace.objects.filter(status='approved')
    
    # Apply filters
    if category:
        # Treat mosque and prayer_room as the same category for filtering
        if category == 'mosque' or category == 'prayer_room':
            places = places.filter(Q(category='mosque') | Q(category='prayer_room'))
        else:
            places = places.filter(category=category)
    
    # City filtering (for trip planning)
    if city_filter:
        places = places.filter(address__icontains=city_filter)
    
    if search_query:
        places = places.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    # Annotate with average rating
    places = places.annotate(
        average_rating=Round(Avg('reviews__rating'), 1)
    )
    
    # Enhanced sorting logic for international users
    if is_in_korea and user_location:
        # Korea users get distance-based sorting
        places = places.annotate(distance=Distance('location', user_location))
        if sort == 'rating':
            places = places.order_by('-average_rating', 'name')
        else:  # Default to distance sorting for Korea users
            places = places.order_by('distance')
    else:
        # International users get rating-based sorting by default
        if sort == 'distance' and user_location:
            # Still allow distance sorting if they have location
            places = places.annotate(distance=Distance('location', user_location))
            places = places.order_by('distance')
        else:  # Default to rating for international users
            places = places.order_by('-average_rating', 'name')
    
    # Pagination
    paginator = Paginator(places, 20)  # Show 20 places per page
    
    try:
        paginated_places = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        paginated_places = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        paginated_places = paginator.page(paginator.num_pages)
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        places_html = render_to_string('places/partials/place_list.html', {
            'places': paginated_places,
            'user_location': user_location,
            'location_context': location_context,
        })
        
        # Return JSON response with HTML and pagination info
        response = JsonResponse({
            'html': places_html,
            'has_next': paginated_places.has_next(),
            'next_page': int(page) + 1 if paginated_places.has_next() else None,
            'total_pages': paginator.num_pages,
        })
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    return render(request, 'places/explore.html', {
        'places': paginated_places,
        'current_filters': {
            'category': category,
            'search_query': search_query,
            'city': city_filter,  # Include city filter in current filters
            'sort': sort,
        },
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'user_location': user_location,
        'location_context': location_context,
    })

def get_places_json(request):
    """API endpoint to get places as JSON for map and dynamic loading"""
    # Get filter parameters
    category = request.GET.get('category')
    search_query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'distance')  # Default to distance sorting
    page = request.GET.get('page', 1)
    
    # Get user location
    location = get_user_location_context(request)['location']
    user_location = None
    
    if 'lat' in location and 'lng' in location and not location.get('is_fallback'):
        user_location = Point(location['lng'], location['lat'], srid=4326)

    # Base queryset
    places = HalalPlace.objects.filter(status='approved')
    
    # Apply filters
    if category:
        # Treat mosque and prayer_room as the same category for filtering
        if category == 'mosque' or category == 'prayer_room':
            places = places.filter(Q(category='mosque') | Q(category='prayer_room'))
        else:
            places = places.filter(category=category)
    
    if search_query:
        places = places.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    # Annotate with average rating
    places = places.annotate(
        average_rating=Round(Avg('reviews__rating'), 1)
    )
    
    # Location-based sorting
    if user_location:
        places = places.annotate(distance=Distance('location', user_location))
        if sort == 'rating':
            places = places.order_by('-average_rating', 'name')
        else:  # Default to distance sorting
            places = places.order_by('distance')
    else:
        if sort == 'rating':
            places = places.order_by('-average_rating', 'name')
        else:  # Default to rating if no location
            places = places.order_by('-average_rating', 'name')
    
    # Pagination
    paginator = Paginator(places, 20)
    
    try:
        paginated_places = paginator.page(page)
    except PageNotAnInteger:
        paginated_places = paginator.page(1)
    except EmptyPage:
        paginated_places = paginator.page(paginator.num_pages)
    
    # Prepare places data for JSON response
    places_data = []
    for place in paginated_places:
        place_data = {
            'id': place.id,
            'name': place.name,
            'category': place.category,
            'address': place.address,
            'description': place.description,
            'average_rating': float(place.average_rating) if place.average_rating else None,
            'photo_url': place.photo_urls[0] if place.photo_urls else None,
            'location': {
                'lat': place.location.y,
                'lng': place.location.x
            },
            'detail_url': request.build_absolute_uri(f'/places/{place.id}/'),
            'google_map_link': place.google_map_link,
            'naver_map_link': place.naver_map_link,
            'kakao_map_link': place.kakao_map_link,
        }
        
        if hasattr(place, 'distance'):
            place_data['distance'] = {
                'm': float(place.distance.m),
                'km': float(place.distance.km)
            }
            
        places_data.append(place_data)
    
    # Return JSON response
    response = JsonResponse({
        'places': places_data,
        'has_next': paginated_places.has_next(),
        'next_page': int(page) + 1 if paginated_places.has_next() else None,
        'total_pages': paginator.num_pages,
        'current_page': paginated_places.number,
    })
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

def place_detail(request, pk):
    place = get_object_or_404(HalalPlace, pk=pk, status='approved')
    reviews = place.reviews.all().select_related('user').order_by('-created_at')
    
    # Check if user has already reviewed
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = reviews.filter(user=request.user).exists()
        
    # Annotate with average rating
    place = HalalPlace.objects.annotate(
        average_rating=Round(Avg('reviews__rating'), 1)
    ).get(pk=place.pk)
    
    # Get user location context for proper map link styling
    location_context = get_user_location_context(request)
    
    return render(request, 'places/place_detail.html', {
        'place': place,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'location_context': location_context,
    })

def upload_photo(photo):
    # Generate unique filename
    file_ext = photo.name.split('.')[-1]
    filename = f'places/photos/{uuid.uuid4()}.{file_ext}'
    
    # Save file and return path
    path = default_storage.save(filename, ContentFile(photo.read()))
    return path  # Return just the path, not the full URL

@login_required
def submit_place(request):
    """Handle place submission by authenticated users"""
    try:
        if request.method == 'POST':
            logger.info(f"Place submission attempt by user: {request.user.username}")
            form = HalalPlaceForm(request.POST, request.FILES)
            if form.is_valid():
                place = form.save(commit=False)
                place.status = 'pending'
                place.submitted_by = request.user
                
                # Handle location from latitude and longitude
                latitude = form.cleaned_data.get('latitude')
                longitude = form.cleaned_data.get('longitude')
                if latitude is not None and longitude is not None:
                    place.location = Point(longitude, latitude)
                    logger.debug(f"Place location set: lat={latitude}, lng={longitude}")
                
                # Handle multiple photos
                photos = request.FILES.getlist('photos')
                if photos:
                    logger.debug(f"Processing {len(photos)} photos for place submission")
                    photo_urls = []
                    for photo in photos:
                        try:
                            # Update the photo URL to include MEDIA_URL
                            photo_url = upload_photo(photo)
                            if not photo_url.startswith(('http://', 'https://')):
                                photo_url = settings.MEDIA_URL + photo_url
                            photo_urls.append(photo_url)
                        except Exception as e:
                            logger.error(f"Error uploading photo: {str(e)}")
                            messages.error(request, f'Error uploading photo: {photo.name}')
                    place.photo_urls = photo_urls
                
                place.save()
                logger.info(f"Place '{place.name}' submitted successfully by user {request.user.username}")
                
                # Send Telegram notification about the new submission
                try:
                    notification_data = {
                        'place_id': place.id,
                        'name': place.name,
                        'category': place.category,
                        'address': place.address,
                        'description': place.description,
                        'submitted_by_username': request.user.username,
                        'website': place.website or '',
                        'phone_number': place.phone_number or '',
                        'photos_count': len(place.photo_urls) if place.photo_urls else 0,
                    }
                    
                    notification_sent = send_new_place_notification(notification_data)
                    if notification_sent:
                        logger.info(f"Telegram notification sent for place submission: {place.name}")
                    else:
                        logger.debug(f"Telegram notification not sent for place submission: {place.name}")
                        
                except Exception as e:
                    # Don't fail the submission if notification fails
                    logger.error(f"Error sending Telegram notification for place '{place.name}': {str(e)}")
                
                messages.success(request, 'Place submitted successfully! It will be reviewed by our team.')
                return redirect('places:explore')
            else:
                logger.warning(f"Invalid place submission form by user {request.user.username}: {form.errors}")
                messages.error(request, 'Please correct the errors below.')
        else:
            form = HalalPlaceForm()
        
        return render(request, 'places/submit_place.html', {
            'form': form,
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        })
    except Exception as e:
        logger.error(f"Error in submit_place view: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while submitting the place. Please try again.')
        return redirect('places:home')

def about(request):
    stats = {
        'total_places': HalalPlace.objects.filter(status='approved').count(),
        'total_reviews': Review.objects.count(),
        'total_users': User.objects.count(),
    }
    return render(request, 'places/about.html', stats)

def donate(request):
    return render(request, 'places/donate.html')

def legal(request):
    """Combined legal page with Privacy Policy, Terms of Service, and Cookie Policy"""
    return render(request, 'places/legal.html')

def set_location(request):
    """API endpoint to set user location"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        lat = data.get('latitude')
        lng = data.get('longitude')
        city = data.get('city')
        country = data.get('country')
        
        if not (lat and lng) and not city:
            return JsonResponse({'error': 'Missing location data'}, status=400)
            
        # Prepare location data
        location_data = {}
        if lat and lng:
            location_data['lat'] = lat
            location_data['lng'] = lng
        if city:
            location_data['city'] = city
        if country:
            location_data['country'] = country
            
        # Update location in session
        location = update_user_location(request, location_data)  # noqa: F841
            
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def handler404(request, exception):
    try:
        return render(request, 'places/404.html', status=404)
    except Exception as e:
        print(e)
        # Fallback to a simple 404 response if template rendering fails
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound('<h1>Page not found 404</h1>')
