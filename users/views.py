from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import User
from places.models import HalalPlace
from .forms import UserRegistrationForm, UserUpdateForm
from reviews.models import Review
from django.views.decorators.http import require_POST
from django.db.models import Avg
from django.db.models.functions import Round

@login_required
def profile(request, username=None):
    if username:
        user = get_object_or_404(User, username=username)
    else:
        user = request.user
        
    reviews = Review.objects.filter(user=user).select_related('place')
    favorite_places = user.favorite_places.filter(status='approved')
    submitted_places = HalalPlace.objects.filter(submitted_by=user).order_by('-created_at')
    # Annotate with average rating
    favorite_places = favorite_places.annotate(
        average_rating=Round(Avg('reviews__rating'), 1)
    )
    context = {
        'user': user,
        'reviews': reviews,
        'favorite_places': favorite_places,
        'submitted_places': submitted_places,
        'is_own_profile': user == request.user,
    }
    return render(request, 'users/profile.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'users/edit_profile.html', {'form': form})

@login_required
@require_POST
def toggle_favorite(request, place_id):
    place = get_object_or_404(HalalPlace, id=place_id)
    user = request.user
    
    if place in user.favorite_places.all():
        user.favorite_places.remove(place)
        status = 'removed'
    else:
        user.favorite_places.add(place)
        status = 'added'
    
    return JsonResponse({'status': status})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Get the next URL from either POST data or GET parameters
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('places:home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'users/login.html', {
        'next': request.GET.get('next', '')  # Pass the next parameter to the template
    })

def logout_view(request):
    logout(request)
    return redirect('places:home')

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('places:home')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})

