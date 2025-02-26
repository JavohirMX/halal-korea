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

User = get_user_model()

def home(request):
    featured_places = HalalPlace.objects.filter(
        status='approved'
    ).annotate(
        avg_rating=Round(Avg('reviews__rating'), 1)
    ).order_by('-avg_rating')[:6]
    
    return render(request, 'places/home.html', {
        'featured_places': featured_places,
    })

def explore(request):
    # Get filter parameters
    category = request.GET.get('category')
    search_query = request.GET.get('q')
    min_rating = request.GET.get('rating')
    
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
    
    # Apply rating filter
    if min_rating:
        places = places.filter(average_rating__gte=float(min_rating))
    
    # Order by rating and name
    places = places.order_by('-average_rating', 'name')
    
    return render(request, 'places/explore.html', {
        'places': places,
        'current_filters': {
            'category': category,
            'search_query': search_query,
            'min_rating': min_rating,
        }
    })

def place_detail(request, pk):
    place = get_object_or_404(HalalPlace, pk=pk, status='approved')
    reviews = place.reviews.all().select_related('user').order_by('-created_at')
    
    # Check if user has already reviewed
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = reviews.filter(user=request.user).exists()
    
    return render(request, 'places/place_detail.html', {
        'place': place,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
    })

def upload_photo(photo):
    # Generate unique filename
    file_ext = photo.name.split('.')[-1]
    filename = f'places/photos/{uuid.uuid4()}.{file_ext}'
    
    # Save file and return path
    path = default_storage.save(filename, ContentFile(photo.read()))
    return default_storage.url(path)

@login_required
def submit_place(request):
    if request.method == 'POST':
        form = HalalPlaceForm(request.POST, request.FILES)
        if form.is_valid():
            place = form.save(commit=False)
            place.status = 'pending'
            place.submitted_by = request.user
            
            # Handle multiple photos
            photos = request.FILES.getlist('photos')
            if photos:
                photo_urls = []
                for photo in photos:
                    photo_url = upload_photo(photo)
                    photo_urls.append(photo_url)
                place.photo_urls = photo_urls
            
            place.save()
            messages.success(request, 'Place submitted successfully! It will be reviewed by our team.')
            return redirect('places:explore')
    else:
        form = HalalPlaceForm()
    
    return render(request, 'places/submit_place.html', {
        'form': form,
    })

def about(request):
    stats = {
        'total_places': HalalPlace.objects.filter(status='approved').count(),
        'total_reviews': Review.objects.count(),
        'total_users': User.objects.count(),
    }
    return render(request, 'places/about.html', stats)
