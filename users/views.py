from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .models import User
from places.models import HalalPlace
from .forms import UserRegistrationForm, UserUpdateForm
from .utils import send_activation_email
from .tokens import email_verification_token
from .rate_limiting import (
    check_email_rate_limit, record_email_attempt,
    check_registration_rate_limit, record_registration_attempt,
    check_login_rate_limit, record_login_attempt
)
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
    """User login view with security logging and rate limiting"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_ip = request.META.get('REMOTE_ADDR')
        
        logger.info(f"Login attempt for username: {username} from IP: {user_ip}")
        
        # Check login rate limiting
        allowed, error_msg = check_login_rate_limit(request)
        if not allowed:
            logger.warning(f"Login rate limited for username: {username} from IP: {user_ip}. {error_msg}")
            return redirect(f"/users/rate-limited/?error={error_msg}")
        
        # Record the login attempt
        record_login_attempt(request)
        
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
    """User registration view with email activation"""
    if request.method == 'POST':
        user_ip = request.META.get('REMOTE_ADDR')
        username = request.POST.get('username', 'unknown')
        
        logger.info(f"Registration attempt for username: {username} from IP: {user_ip}")
        
        # Check rate limiting
        allowed, error_msg = check_registration_rate_limit(request)
        if not allowed:
            logger.warning(f"Registration rate limited for username: {username} from IP: {user_ip}. {error_msg}")
            return redirect(f"/users/rate-limited/?error={error_msg}")
        
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Record the registration attempt
                record_registration_attempt(request)
                
                # Create user as active but not email verified
                user = form.save(commit=False)
                user.is_active = True  # User can log in
                user.email_verified = False  # But email is not verified yet
                user.save()
                
                logger.info(f"User created (active, email unverified): {user.username} from IP: {user_ip}")
                
                # Check email rate limiting before sending
                email_allowed, email_error_msg = check_email_rate_limit(request, user)
                if email_allowed:
                    # Send activation email
                    if send_activation_email(user, request):
                        # Record the email attempt
                        record_email_attempt(request, user)
                        logger.info(f"Activation email sent for user: {user.username}")
                        # Auto-login the user
                        login(request, user)
                        logger.info(f"Auto-login after registration for user: {user.username}")
                        return render(request, 'users/check_email.html', {'email': user.email})
                    else:
                        logger.error(f"Failed to send activation email for user: {user.username}")
                        # Still login the user even if email fails
                        login(request, user)
                        messages.warning(request, 'Account created successfully, but we could not send the verification email. You can request a new one from your profile.')
                        return redirect('places:home')
                else:
                    # Email rate limited - still create account but warn user
                    logger.warning(f"Email rate limited during registration for user: {user.username}. {email_error_msg}")
                    login(request, user)
                    messages.warning(request, f'Account created successfully, but verification email was not sent due to rate limiting: {email_error_msg}')
                    return redirect('places:home')
                    
            except Exception as e:
                logger.error(f"Error during registration for username: {username} from IP: {user_ip}: {str(e)}")
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            logger.warning(f"Invalid registration form for username: {username} from IP: {user_ip}: {form.errors}")
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})


def activate_account(request, uidb64, token):
    """Activate user account with email verification token"""
    try:
        # Decode user ID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        # Check if token is valid and user is not already verified
        if email_verification_token.check_token(user, token):
            if not user.email_verified:
                user.email_verified = True
                user.save()
                
                logger.info(f"Email verified for user: {user.username}")
                messages.success(request, 'Your email has been verified successfully!')
                
                return render(request, 'users/activation_result.html', {'success': True})
            else:
                # User email is already verified
                logger.info(f"Activation attempt for already verified user: {user.username}")
                messages.info(request, 'Your email is already verified.')
                return render(request, 'users/activation_result.html', {'success': True})
        else:
            # Invalid or expired token
            logger.warning(f"Invalid activation token used for user ID: {uid}")
            error_message = 'The activation link is invalid or has expired. Please request a new activation email.'
            return render(request, 'users/activation_result.html', {
                'success': False, 
                'error_message': error_message
            })
            
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        logger.error(f"Error during account activation: {str(e)}")
        error_message = 'Invalid activation link. Please request a new activation email.'
        return render(request, 'users/activation_result.html', {
            'success': False, 
            'error_message': error_message
        })


def resend_activation_email(request):
    """Resend activation email to user"""
    # If user is logged in, handle them automatically
    if request.user.is_authenticated:
        user = request.user
        user_ip = request.META.get('REMOTE_ADDR')
        
        # Check if already verified
        if user.email_verified:
            messages.info(request, 'Your email is already verified!')
            return redirect('places:home')
        
        # For authenticated users, we can resend immediately on GET request
        if request.method == 'GET':
            # Check email rate limiting
            allowed, error_msg = check_email_rate_limit(request, user)
            if not allowed:
                logger.warning(f"Email rate limited for authenticated user {user.username}. {error_msg}")
                return redirect(f"/users/rate-limited/?error={error_msg}")
            
            if send_activation_email(user, request):
                # Record the email attempt
                record_email_attempt(request, user)
                logger.info(f"Activation email resent to authenticated user {user.username} from IP: {user_ip}")
                messages.success(request, 'Activation email has been sent to your email address. Please check your inbox.')
                return render(request, 'users/check_email.html', {'email': user.email})
            else:
                logger.error(f"Failed to resend activation email to authenticated user {user.username}")
                messages.error(request, 'Unable to send activation email. Please try again later.')
                return redirect('places:home')
    
    # For non-authenticated users, show the email form
    if request.method == 'POST':
        email = request.POST.get('email')
        user_ip = request.META.get('REMOTE_ADDR')
        
        # Check email rate limiting first
        allowed, error_msg = check_email_rate_limit(request)
        if not allowed:
            logger.warning(f"Email rate limited for anonymous user from IP: {user_ip}. {error_msg}")
            return redirect(f"/users/rate-limited/?error={error_msg}")
        
        try:
            user = User.objects.get(email=email)
            
            if user.email_verified:
                messages.info(request, 'This email is already verified.')
                return redirect('users:login')
            
            # Send activation email
            if send_activation_email(user, request):
                # Record the email attempt
                record_email_attempt(request, user)
                logger.info(f"Activation email resent to {email} from IP: {user_ip}")
                messages.success(request, 'Activation email has been sent. Please check your inbox.')
                return render(request, 'users/check_email.html', {'email': email})
            else:
                logger.error(f"Failed to resend activation email to {email}")
                messages.error(request, 'Unable to send activation email. Please try again later.')
                
        except User.DoesNotExist:
            logger.warning(f"Resend activation attempt for non-existent email: {email} from IP: {user_ip}")
            messages.error(request, 'No account found with this email address.')
    
    return render(request, 'users/resend_activation.html')


def rate_limited_view(request):
    """View to show when user hits rate limits"""
    error_message = request.GET.get('error', '')
    return render(request, 'users/rate_limited.html', {
        'error_message': error_message
    })