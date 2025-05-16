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
from utils.location_manager import get_user_location, update_user_location
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string
import json

User = get_user_model()

def home(request):
    # Get user location from session or IP
    location = get_user_location(request)
    user_location = None
    
    if 'lat' in location and 'lng' in location:
        user_location = Point(location['lng'], location['lat'], srid=4326)

    # Get nearest places
    featured_places = HalalPlace.objects.filter(
        status='approved'
    ).annotate(
        average_rating=Round(Avg('reviews__rating'), 1)
    )

    # Add distance annotation only if user_location exists
    if user_location:
        featured_places = featured_places.annotate(
            distance=Distance('location', user_location)
        ).order_by('distance')[:6]
    else:
        featured_places = featured_places.order_by('-average_rating')[:6]
    
    return render(request, 'places/home.html', {
        'featured_places': featured_places,
    })

def explore(request):
    # Get filter parameters
    category = request.GET.get('category')
    search_query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'distance')  # Default to distance sorting
    page = request.GET.get('page', 1)
    
    # Get user location
    location = get_user_location(request)
    user_location = None
    
    if 'lat' in location and 'lng' in location:
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
        })
        
        # Return JSON response with HTML and pagination info
        return JsonResponse({
            'html': places_html,
            'has_next': paginated_places.has_next(),
            'next_page': int(page) + 1 if paginated_places.has_next() else None,
            'total_pages': paginator.num_pages,
        })
        
    return render(request, 'places/explore.html', {
        'places': paginated_places,
        'current_filters': {
            'category': category,
            'search_query': search_query,
            'sort': sort,
        },
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'user_location': user_location,
    })

def get_places_json(request):
    """API endpoint to get places as JSON for map and dynamic loading"""
    # Get filter parameters
    category = request.GET.get('category')
    search_query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'distance')  # Default to distance sorting
    page = request.GET.get('page', 1)
    
    # Get user location
    location = get_user_location(request)
    user_location = None
    
    if 'lat' in location and 'lng' in location:
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
    return JsonResponse({
        'places': places_data,
        'has_next': paginated_places.has_next(),
        'next_page': int(page) + 1 if paginated_places.has_next() else None,
        'total_pages': paginator.num_pages,
        'current_page': paginated_places.number,
    })

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
    
    return render(request, 'places/place_detail.html', {
        'place': place,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
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
    if request.method == 'POST':
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
            
            # Handle multiple photos
            photos = request.FILES.getlist('photos')
            if photos:
                photo_urls = []
                for photo in photos:
                    # Update the photo URL to include MEDIA_URL
                    photo_url = upload_photo(photo)
                    if not photo_url.startswith(('http://', 'https://')):
                        photo_url = settings.MEDIA_URL + photo_url
                    photo_urls.append(photo_url)
                place.photo_urls = photo_urls
            
            place.save()
            messages.success(request, 'Place submitted successfully! It will be reviewed by our team.')
            return redirect('places:explore')
    else:
        form = HalalPlaceForm()
    
    return render(request, 'places/submit_place.html', {
        'form': form,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    })

def about(request):
    stats = {
        'total_places': HalalPlace.objects.filter(status='approved').count(),
        'total_reviews': Review.objects.count(),
        'total_users': User.objects.count(),
    }
    return render(request, 'places/about.html', stats)

def donate(request):
    return render(request, 'places/donate.html')

def set_location(request):
    """API endpoint to set user location"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        lat = data.get('latitude')
        lng = data.get('longitude')
        city = data.get('city')
        
        if not (lat and lng) and not city:
            return JsonResponse({'error': 'Missing location data'}, status=400)
            
        # Update location in session
        location = update_user_location(request, {  # noqa: F841
            'lat': lat,
            'lng': lng,
            'city': city
        })
            
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
