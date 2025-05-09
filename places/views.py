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
import time

User = get_user_model()

def home(request):
    featured_places = HalalPlace.objects.filter(
        status='approved'
    ).annotate(
        average_rating=Round(Avg('reviews__rating'), 1)
    ).order_by('-average_rating')[:6]
    
    return render(request, 'places/home.html', {
        'featured_places': featured_places,
    })

def explore(request):
    # Get filter parameters
    category = request.GET.get('category')
    search_query = request.GET.get('q')
    sort = request.GET.get('sort', 'distance')
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    user_location = None
    # Check session if no lat/lng in GET
    session_loc = request.session.get('user_location')
    if not (lat and lng) and session_loc:
        # Check if not expired (1 hour = 3600 seconds)
        if time.time() - session_loc['timestamp'] < 3600:
            lat = session_loc['lat']
            lng = session_loc['lng']
    # Start with all approved places
    places = HalalPlace.objects.filter(status='approved')
    # Apply filters
    if category:
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
    if lat and lng:
        try:
            user_location = Point(float(lng), float(lat), srid=4326)
            places = places.annotate(distance=Distance('location', user_location))
            if sort == 'distance':
                places = places.order_by('distance')
            else:
                places = places.order_by('-average_rating', 'name')
        except (ValueError, TypeError):
            user_location = None
            # fallback to default ordering
            places = places.order_by('-average_rating', 'name')
    else:
        places = places.order_by('-average_rating', 'name')
    return render(request, 'places/explore.html', {
        'places': places,
        'current_filters': {
            'category': category,
            'search_query': search_query,
            'sort': sort,
        },
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'user_location': user_location,
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
    if request.method == 'POST':
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        if lat and lng:
            request.session['user_location'] = {
                'lat': float(lat),
                'lng': float(lng),
                'timestamp': time.time()
            }
            return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)
