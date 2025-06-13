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
import logging

logger = logging.getLogger(__name__)

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
    """User login view with security logging"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_ip = request.META.get('REMOTE_ADDR')
        
        logger.info(f"Login attempt for username: {username} from IP: {user_ip}")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                logger.info(f"Successful login for user: {username} from IP: {user_ip}")
                
                # Get the next URL from either POST data or GET parameters
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    logger.debug(f"Redirecting user {username} to: {next_url}")
                    return redirect(next_url)
                return redirect('places:home')
            else:
                logger.warning(f"Login attempt for inactive user: {username} from IP: {user_ip}")
                messages.error(request, 'Your account is inactive. Please contact support.')
        else:
            logger.warning(f"Failed login attempt for username: {username} from IP: {user_ip}")
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'users/login.html', {
        'next': request.GET.get('next', '')  # Pass the next parameter to the template
    })

def logout_view(request):
    """User logout view with logging"""
    if request.user.is_authenticated:
        username = request.user.username
        user_ip = request.META.get('REMOTE_ADDR')
        logger.info(f"User logout: {username} from IP: {user_ip}")
    
    logout(request)
    return redirect('places:home')

def register_view(request):
    """User registration view with logging"""
    if request.method == 'POST':
        user_ip = request.META.get('REMOTE_ADDR')
        username = request.POST.get('username', 'unknown')
        
        logger.info(f"Registration attempt for username: {username} from IP: {user_ip}")
        
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                logger.info(f"Successful registration for user: {user.username} from IP: {user_ip}")
                
                login(request, user)
                logger.info(f"Auto-login after registration for user: {user.username}")
                
                messages.success(request, 'Welcome! Your account has been created successfully.')
                return redirect('places:home')
            except Exception as e:
                logger.error(f"Error during registration for username: {username} from IP: {user_ip}: {str(e)}")
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            logger.warning(f"Invalid registration form for username: {username} from IP: {user_ip}: {form.errors}")
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})

