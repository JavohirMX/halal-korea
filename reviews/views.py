from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Review
from places.models import HalalPlace
from .forms import ReviewForm

@login_required
def add_review(request, place_id):
    place = get_object_or_404(HalalPlace, id=place_id)
    
    # Check if user has already reviewed
    if Review.objects.filter(user=request.user, place=place).exists():
        messages.error(request, 'You have already reviewed this place.')
        return redirect('places:place_detail', pk=place_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.place = place
            review.save()
            messages.success(request, 'Review added successfully!')
            return redirect('places:place_detail', pk=place_id)
    else:
        form = ReviewForm()
    
    return render(request, 'reviews/add_review.html', {
        'form': form,
        'place': place
    })

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Review updated successfully!')
            return redirect('places:place_detail', pk=review.place.id)
    else:
        form = ReviewForm(instance=review)
    
    return render(request, 'reviews/edit_review.html', {
        'form': form,
        'review': review
    })

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    place_id = review.place.id
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Review deleted successfully!')
        return redirect('places:place_detail', pk=place_id)
    
    return render(request, 'reviews/delete_review.html', {
        'review': review
    })
