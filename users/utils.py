from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import email_verification_token, password_reset_token
import logging

logger = logging.getLogger(__name__)

def send_activation_email(user, request):
    """
    Send activation email to the user.
    """
    try:
        # Generate activation token
        token = email_verification_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build activation link
        activation_url = reverse('users:activate', kwargs={'uidb64': uid, 'token': token})
        activation_link = request.build_absolute_uri(activation_url)
        
        # Prepare email context
        context = {
            'user': user,
            'activation_link': activation_link,
        }
        
        # Render email templates
        html_message = render_to_string('users/email/activation_email.html', context)
        plain_message = render_to_string('users/email/activation_email.txt', context)
        
        # Send email
        send_mail(
            subject='Activate Your Halal Korea Account',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Activation email sent to {user.email} for user {user.username}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
        return False


def send_password_reset_email(user, request):
    """
    Send password reset email to the user.
    """
    try:
        # Generate password reset token
        token = password_reset_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset link
        reset_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        reset_link = request.build_absolute_uri(reset_url)
        
        # Get client info for security
        user_ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
        
        # Prepare email context
        context = {
            'user': user,
            'reset_link': reset_link,
            'user_ip': user_ip,
            'user_agent': user_agent,
            'site_name': getattr(settings, 'SITE_NAME', 'Halal Korea'),
        }
        
        # Render email templates
        html_message = render_to_string('users/email/password_reset_email.html', context)
        plain_message = render_to_string('users/email/password_reset_email.txt', context)
        
        # Send email
        send_mail(
            subject='Reset Your Halal Korea Password',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent to {user.email} for user {user.username} from IP {user_ip}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False
