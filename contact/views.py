from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.template.loader import render_to_string
import logging

from .forms import ContactForm
from .rate_limiting import check_contact_rate_limit, record_contact_attempt, get_client_ip
from utils.telegram_notifications import send_contact_message_notification

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def submit_contact_form(request):
    """Handle contact form submission via AJAX"""
    try:
        # Check rate limiting
        can_submit, error_message = check_contact_rate_limit(request)
        if not can_submit:
            return JsonResponse({
                'success': False,
                'error': error_message,
                'field_errors': {}
            }, status=429)
        
        # Process the form
        form = ContactForm(request.POST, user=request.user)
        
        if form.is_valid():
            # Create the contact message
            contact_message = form.save(commit=False)
            
            # Add metadata
            contact_message.ip_address = get_client_ip(request)
            contact_message.user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Link to user if authenticated (but use form data for name/email)
            if request.user.is_authenticated:
                contact_message.user = request.user
                # Use the form data (user can edit their name/email if needed)
            
            contact_message.save()
            
            # Record the attempt for rate limiting
            record_contact_attempt(request)
            
            # Send Telegram notification
            try:
                notification_data = {
                    'name': contact_message.name,
                    'email': contact_message.email,
                    'subject': contact_message.subject,
                    'message': contact_message.message,
                    'user_type': 'Registered User' if request.user.is_authenticated else 'Anonymous',
                    'user_id': request.user.id if request.user.is_authenticated else None,
                }
                send_contact_message_notification(notification_data)
                logger.info(f"Contact message submitted by {contact_message.name} ({contact_message.email})")
            except Exception as e:
                logger.error(f"Failed to send Telegram notification for contact message: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'message': _('Thank you for your message! We\'ll get back to you soon.')
            })
        
        else:
            # Form has validation errors
            field_errors = {}
            for field, errors in form.errors.items():
                field_errors[field] = [str(error) for error in errors]
            
            return JsonResponse({
                'success': False,
                'error': _('Please check the form for errors.'),
                'field_errors': field_errors
            }, status=400)
    
    except Exception as e:
        logger.error(f"Error in contact form submission: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': _('An unexpected error occurred. Please try again later.')
        }, status=500)


def get_contact_form_html(request):
    """Return the contact form HTML for AJAX loading"""
    form = ContactForm(user=request.user)
    html = render_to_string('contact/form.html', {
        'form': form,
        'user': request.user
    }, request=request)
    
    return JsonResponse({
        'html': html
    })


def rate_limited_view(request):
    """View to show when contact form is rate limited"""
    error_message = request.GET.get('error', _('You have exceeded the rate limit for contact messages.'))
    return render(request, 'contact/rate_limited.html', {
        'error_message': error_message,
        'page_title': _('Rate Limited'),
    })
