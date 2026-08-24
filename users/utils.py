from concurrent.futures import ThreadPoolExecutor
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import email_verification_token, password_reset_token
import logging

logger = logging.getLogger(__name__)

_email_executor = ThreadPoolExecutor(max_workers=4)


def _deliver_email(subject, plain_message, html_message, recipient, success_log, error_log):
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(success_log)
    except Exception:
        logger.exception(error_log)


def send_activation_email(user, request):
    """
    Queue activation email for delivery without blocking the request thread.
    Returns True when the email was submitted for sending, False on validation failure.
    """
    try:
        if not user.email:
            logger.error("Cannot send activation email: user has no email address")
            return False

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
        
        # Render email templates synchronously before handing off to the worker thread
        html_message = render_to_string('users/email/activation_email.html', context)
        plain_message = render_to_string('users/email/activation_email.txt', context)

        _email_executor.submit(
            _deliver_email,
            subject='Activate Your Halal Korea Account',
            plain_message=plain_message,
            html_message=html_message,
            recipient=user.email,
            success_log=f"Activation email sent to {user.email} for user {user.username}",
            error_log=f"Failed to send activation email to {user.email}",
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to queue activation email to {user.email}: {str(e)}")
        return False


def send_password_reset_email(user, request):
    """
    Queue password reset email for delivery without blocking the request thread.
    Returns True when the email was submitted for sending, False on validation failure.
    """
    try:
        if not user.email:
            logger.error("Cannot send password reset email: user has no email address")
            return False

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
        
        # Render email templates synchronously before handing off to the worker thread
        html_message = render_to_string('users/email/password_reset_email.html', context)
        plain_message = render_to_string('users/email/password_reset_email.txt', context)

        _email_executor.submit(
            _deliver_email,
            subject='Reset Your Halal Korea Password',
            plain_message=plain_message,
            html_message=html_message,
            recipient=user.email,
            success_log=f"Password reset email sent to {user.email} for user {user.username} from IP {user_ip}",
            error_log=f"Failed to send password reset email to {user.email}",
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to queue password reset email to {user.email}: {str(e)}")
        return False
