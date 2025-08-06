from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods
from .models import Review
from places.models import HalalPlace
from users.decorators import email_verification_required
import logging

logger = logging.getLogger(__name__)

@login_required
@email_verification_required
@require_http_methods(["POST"])
def add_review(request, place_id):
    """Add a new review for a place."""
    place = get_object_or_404(HalalPlace, id=place_id, status='approved')
    
    logger.info(f"Review submission attempt by user {request.user.username} for place {place.name}")
    
    # Check if user has already reviewed this place
    if Review.objects.filter(user=request.user, place=place).exists():
        logger.warning(f"Duplicate review attempt by user {request.user.username} for place {place.name}")
        messages.error(request, 'You have already reviewed this place.')
        return redirect('places:place_detail', pk=place_id)
    
    try:
        # Get form data
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()
        
        # Validate rating
        if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
            logger.warning(f"Invalid rating {rating} submitted by user {request.user.username} for place {place.name}")
            raise ValidationError('Please provide a valid rating between 1 and 5.')
        
        # Create review
        review = Review.objects.create(
            user=request.user,
            place=place,
            rating=int(rating),
            comment=comment
        )
        
        logger.info(f"Review created successfully by user {request.user.username} for place {place.name} with rating {rating}")
        messages.success(request, 'Your review has been added successfully!')
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Review added successfully',
                'review': {
                    'rating': review.rating,
                    'content': review.comment,
                    'created_at': review.created_at.strftime('%B %d, %Y'),
                    'user': request.user.username
                }
            })
            
    except ValidationError as e:
        logger.warning(f"Validation error in review submission: {str(e)}")
        messages.error(request, str(e))
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    except Exception as e:
        logger.error(f"Error adding review by user {request.user.username} for place {place.name}: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while submitting your review.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while submitting your review.'
            }, status=500)
    
    return redirect('places:place_detail', pk=place_id)

@login_required
@email_verification_required
def edit_review(request, review_id):
    """Edit an existing review."""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    place_id = review.place.id
    
    if request.method == 'POST':
        try:
            rating = request.POST.get('rating')
            comment = request.POST.get('comment', '').strip()
            
            # Validate rating
            if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
                raise ValidationError('Please provide a valid rating between 1 and 5.')
            
            # Update review
            review.rating = int(rating)
            review.comment = comment
            review.save()
            
            messages.success(request, 'Your review has been updated successfully!')
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Review updated successfully',
                    'review': {
                        'rating': review.rating,
                        'content': review.comment,
                        'created_at': review.created_at.strftime('%B %d, %Y')
                    }
                })
                
        except ValidationError as e:
            messages.error(request, str(e))
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
        except Exception:
            messages.error(request, 'An error occurred while updating your review.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'An error occurred while updating your review.'
                }, status=500)
    
    return redirect('places:place_detail', pk=place_id)

@login_required
@email_verification_required
@require_http_methods(["POST", "DELETE"])
def delete_review(request, review_id):
    """Delete a review."""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    place_id = review.place.id
    
    try:
        review.delete()
        messages.success(request, 'Your review has been deleted successfully!')
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Review deleted successfully'
            })
            
    except Exception:
        messages.error(request, 'An error occurred while deleting your review.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while deleting your review.'
            }, status=500)
    
    return redirect('places:place_detail', pk=place_id)
