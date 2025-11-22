from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
import logging

from .models import FeedbackResponse
from .rate_limiting import check_feedback_rate_limit, record_feedback_attempt, get_client_ip
from utils.telegram_notifications import send_telegram_notification

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def submit_feedback(request):
    """
    API endpoint for submitting feedback from the floating widget.
    Accepts JSON data and creates a FeedbackResponse object.
    """
    try:
        # Check rate limiting first
        can_submit, error_message = check_feedback_rate_limit(request)
        if not can_submit:
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=429)
        
        # Parse JSON data
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['rating', 'page_url', 'page_type', 'session_id', 
                          'time_on_site', 'time_on_page', 'language', 'device_type']
        
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=400)
        
        # Validate rating is between 1-5
        rating = data.get('rating')
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return JsonResponse({
                'success': False,
                'error': 'Rating must be between 1 and 5'
            }, status=400)
        
        # Create feedback response
        feedback = FeedbackResponse.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_id=data.get('session_id'),
            rating=rating,
            comment=data.get('comment', '').strip()[:500],  # Max 500 chars
            page_url=data.get('page_url')[:500],
            page_type=data.get('page_type'),
            page_title=data.get('page_title', '')[:200],
            time_on_site=data.get('time_on_site', 0),
            time_on_page=data.get('time_on_page', 0),
            pages_visited=data.get('pages_visited', 1),
            scroll_depth=data.get('scroll_depth'),
            language=data.get('language', 'en')[:5],
            device_type=data.get('device_type', 'desktop'),
            browser=data.get('browser', '')[:50],
            screen_resolution=data.get('screen_resolution', '')[:20],
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            referrer=data.get('referrer', '')[:500],
        )
        
        # Record the attempt for rate limiting
        record_feedback_attempt(request)
        
        # Log the feedback submission
        logger.info(
            f"Feedback submitted: {feedback.id} - "
            f"Rating: {feedback.rating}★ - "
            f"Page: {feedback.page_type} - "
            f"User: {feedback.user or f'Anon-{feedback.session_id[:8]}'}"
        )
        
        # Send Telegram notification for low ratings (1-2 stars)
        if rating <= 2:
            try:
                user_str = feedback.user.username if feedback.user else f"Anonymous-{feedback.session_id[:8]}"
                message = (
                    f"⚠️ <b>Low Feedback Rating Alert</b>\n\n"
                    f"<b>Rating:</b> {'⭐' * rating} ({rating}/5)\n"
                    f"<b>User:</b> {user_str}\n"
                    f"<b>Page:</b> {feedback.page_type}\n"
                    f"<b>URL:</b> {feedback.page_url}\n"
                )
                if feedback.comment:
                    message += f"\n<b>Comment:</b>\n{feedback.comment}\n"
                
                message += f"\n<b>Language:</b> {feedback.language} | <b>Device:</b> {feedback.device_type}"
                
                send_telegram_notification(message)
            except Exception as e:
                logger.warning(f"Failed to send Telegram notification for feedback: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for your feedback!'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while submitting feedback'
        }, status=500)

