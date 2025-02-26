from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.models import User
from places.models import HalalPlace
from .forms import UserProfileForm, UserRegistrationForm

@login_required
def profile(request, username=None):
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user
    
    context = {
        'profile_user': profile_user,
        'reviews': profile_user.reviews.select_related('place').order_by('-created_at'),
        'favorite_places': profile_user.favorite_places.filter(status='approved'),
        'submitted_places': profile_user.submitted_places.all(),
    }
    
    return render(request, 'users/profile.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(
            request.POST, 
            request.FILES, 
            instance=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'users/edit_profile.html', {'form': form})

@login_required
def toggle_favorite(request, place_id):
    place = get_object_or_404(HalalPlace, id=place_id)
    user = request.user
    
    if place in user.favorite_places.all():
        user.favorite_places.remove(place)
        status = 'removed'
    else:
        user.favorite_places.add(place)
        status = 'added'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': status})
    
    return redirect('place_detail', pk=place_id)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('places:home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'users/login.html')

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

