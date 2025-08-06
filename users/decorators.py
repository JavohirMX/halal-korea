from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.utils.translation import gettext as _

def email_verification_required(view_func):
    """
    Decorator that requires email verification for a view.
    Redirects to email verification notice if user's email is not verified.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.email_verified:
            messages.warning(
                request, 
                _('Please verify your email address to access this feature. Check your inbox for the verification email.')
            )
            return redirect('users:resend_activation')
        return view_func(request, *args, **kwargs)
    return wrapper
