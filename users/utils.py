from concurrent.futures import ThreadPoolExecutor
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.utils.html import escape, linebreaks
from django.utils.safestring import mark_safe
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import email_verification_token, password_reset_token
import logging
import time

logger = logging.getLogger(__name__)

_email_executor = ThreadPoolExecutor(max_workers=4)

# Admin compose sender and wording. Omitted helper kwargs keep these defaults
# so activation, password reset, and older callers stay on today's copy.
FROM_CHOICE_NOREPLY = 'noreply'
FROM_CHOICE_CONTACT = 'contact'
FROM_CHOICE_CUSTOM = 'custom'

GREETING_HI = 'hi'
GREETING_HELLO = 'hello'
GREETING_SALAM = 'salam'
GREETING_NONE = 'none'
GREETING_CUSTOM = 'custom'

DEFAULT_GREETING_TEMPLATE = 'Hi {name},'
DEFAULT_SIGNOFF = 'Best regards,\nThe Halal Korea Team'

GREETING_TEMPLATES = {
    GREETING_HI: 'Hi {name},',
    GREETING_HELLO: 'Hello {name},',
    GREETING_SALAM: 'Assalamu alaikum {name},',
}


def resolve_from_email(from_choice, custom_email=''):
    """Map a compose From choice to the address passed to the mail backend."""
    if from_choice == FROM_CHOICE_CONTACT:
        return getattr(
            settings,
            'CONTACT_FROM_EMAIL',
            'Halal Korea <contact@halal-korea.com>',
        )
    if from_choice == FROM_CHOICE_CUSTOM:
        address = (custom_email or '').strip()
        return f'Halal Korea <{address}>'
    return settings.DEFAULT_FROM_EMAIL


def validate_custom_from_address(custom_email):
    """Return an error message, or '' when the custom sender is one valid address."""
    address = (custom_email or '').strip()
    if not address:
        return 'Enter an email address for the custom sender.'
    try:
        validate_email(address)
    except ValidationError:
        return 'Enter one valid email address.'
    return ''


def resolve_greeting_template(greeting_choice, custom_greeting=None):
    """Return the greeting template. '' omits the heading."""
    choice = greeting_choice or GREETING_HI
    if choice == GREETING_NONE:
        return ''
    if choice == GREETING_CUSTOM:
        if custom_greeting is None:
            return DEFAULT_GREETING_TEMPLATE
        return custom_greeting
    return GREETING_TEMPLATES.get(choice, DEFAULT_GREETING_TEMPLATE)


def sender_kwargs_from_mapping(mapping):
    """
    from_email, greeting_template, and signoff for a compose payload.

    Missing keys keep today's defaults. A present empty signoff or a "no
    greeting" choice is intentional and is not replaced with the default.
    """
    mapping = mapping or {}
    has_custom_greeting = 'custom_greeting' in mapping
    has_signoff = 'signoff' in mapping
    return {
        'from_email': resolve_from_email(
            mapping.get('from_choice') or FROM_CHOICE_NOREPLY,
            mapping.get('custom_from_email') or '',
        ),
        'greeting_template': resolve_greeting_template(
            mapping.get('greeting_choice') or GREETING_HI,
            mapping.get('custom_greeting') if has_custom_greeting else None,
        ),
        'signoff': mapping.get('signoff') if has_signoff else None,
    }


def _greeting_text(greeting_template, display_name):
    """Substitute {name}. None keeps the default line; a blank template omits it."""
    name = (display_name or '').strip() or 'there'
    if greeting_template is None:
        greeting_template = DEFAULT_GREETING_TEMPLATE
    template = str(greeting_template).strip()
    if not template:
        return ''
    return template.replace('{name}', name)


def _signoff_text(signoff):
    """None keeps the default closing. A blank closing is omitted."""
    if signoff is None:
        signoff = DEFAULT_SIGNOFF
    return str(signoff).replace('\r\n', '\n').replace('\r', '\n').strip()


def _signoff_html(signoff_text):
    """Escaped plain-text closing. The last line of a multi-line closing stays emphasized."""
    if not signoff_text:
        return ''
    lines = signoff_text.split('\n')
    last = len(lines) - 1
    parts = []
    for index, line in enumerate(lines):
        escaped = escape(line)
        if index == last and last > 0:
            parts.append(f'<strong style="color: #22c55e;">{escaped}</strong>')
        else:
            parts.append(f'{escaped}')
    return mark_safe('<br>'.join(parts))


def _render_admin_email(
    subject,
    body_plain,
    *,
    body_html=None,
    display_name=None,
    recipient_email=None,
    from_email=None,
    greeting_template=None,
    signoff=None,
):
    """Render branded admin message templates. Returns (plain_message, html_message)."""
    greeting_name = (display_name or '').strip() or 'there'
    greeting_text = _greeting_text(greeting_template, greeting_name)
    signoff_text = _signoff_text(signoff)
    if body_html:
        message_html = body_html
    else:
        message_html = linebreaks(escape(body_plain))

    context = {
        'subject': subject,
        'greeting_name': greeting_name,
        'greeting_text': greeting_text,
        # Escaped before the HTML template so a custom line cannot inject markup.
        'greeting_html': mark_safe(escape(greeting_text)) if greeting_text else '',
        'signoff_text': signoff_text,
        'signoff_html': _signoff_html(signoff_text),
        'from_email': from_email or '',
        'message': body_plain,
        'message_html': message_html,
        'recipient_email': recipient_email or '',
        'site_name': getattr(settings, 'SITE_NAME', 'Halal Korea'),
    }
    plain_message = render_to_string('users/email/admin_message.txt', context)
    html_message = render_to_string('users/email/admin_message.html', context)
    return plain_message, html_message


def send_admin_email_to_address(
    email,
    subject,
    body_plain,
    *,
    body_html=None,
    display_name=None,
    from_email=None,
    greeting_template=None,
    signoff=None,
):
    """
    Validate an address, render the branded admin template, and queue delivery.
    Returns True when queued, False on validation or queue failure.
    """
    if not email or not str(email).strip():
        logger.error("Cannot send admin email: empty address")
        return False

    email = str(email).strip()
    try:
        validate_email(email)
    except ValidationError:
        logger.error("Cannot send admin email: invalid address %s", email)
        return False

    try:
        plain_message, html_message = _render_admin_email(
            subject,
            body_plain,
            body_html=body_html,
            display_name=display_name,
            recipient_email=email,
            from_email=from_email,
            greeting_template=greeting_template,
            signoff=signoff,
        )
        _email_executor.submit(
            _deliver_email,
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient=email,
            success_log=f"Admin email sent to {email}",
            error_log=f"Failed to send admin email to {email}",
            from_email=from_email,
        )
        return True
    except Exception as e:
        logger.error("Failed to queue admin email to %s: %s", email, e)
        return False


def send_admin_email(user, subject, body_plain, *, body_html=None):
    """Queue a branded admin email to a User. Uses user.email and user.full_name."""
    if not user or not getattr(user, 'email', None):
        logger.error("Cannot send admin email: user has no email address")
        return False
    display_name = getattr(user, 'full_name', None) or getattr(user, 'username', None)
    return send_admin_email_to_address(
        user.email,
        subject,
        body_plain,
        body_html=body_html,
        display_name=display_name,
    )


def queue_admin_emails(
    recipients,
    subject,
    body_plain,
    *,
    body_html=None,
    from_email=None,
    greeting_template=None,
    signoff=None,
):
    """
    Queue branded admin emails to a list of {email, name?} dicts.
    De-duplicates by lowercased email. Skips blank addresses.
    Returns {sent, skipped, failed}.
    """
    sent = 0
    skipped = 0
    failed = 0
    seen = set()

    for recipient in recipients or []:
        email = (recipient.get('email') or '').strip() if isinstance(recipient, dict) else ''
        if not email:
            skipped += 1
            continue

        key = email.lower()
        if key in seen:
            skipped += 1
            continue
        seen.add(key)

        name = None
        if isinstance(recipient, dict):
            name = recipient.get('name') or recipient.get('display_name')

        if send_admin_email_to_address(
            email,
            subject,
            body_plain,
            body_html=body_html,
            display_name=name,
            from_email=from_email,
            greeting_template=greeting_template,
            signoff=signoff,
        ):
            sent += 1
        else:
            failed += 1

    return {'sent': sent, 'skipped': skipped, 'failed': failed}


def _deliver_email(
    subject,
    plain_message,
    html_message,
    recipient,
    success_log,
    error_log,
    max_retries=2,
    from_email=None,
):
    attempts = max_retries + 1
    sender = from_email or settings.DEFAULT_FROM_EMAIL
    for attempt in range(1, attempts + 1):
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=sender,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(success_log)
            return
        except Exception as e:
            if attempt < attempts:
                wait_secs = attempt * 1.5
                logger.warning(
                    "Email send attempt %d/%d failed for %s (%s). Retrying in %.1fs...",
                    attempt,
                    attempts,
                    recipient,
                    e,
                    wait_secs,
                )
                time.sleep(wait_secs)
            else:
                logger.exception("%s (after %d attempts)", error_log, attempts)


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
