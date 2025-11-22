from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class FeedbackResponse(models.Model):
    """
    Model to store user feedback from the floating feedback widget.
    Tracks both authenticated and anonymous user feedback with context.
    """
    
    # User identification (flexible for both auth and anon users)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Authenticated user (if logged in)"
    )
    session_id = models.CharField(
        max_length=100,
        help_text="Session ID for anonymous user tracking"
    )
    
    # Feedback content
    rating = models.IntegerField(
        choices=[(i, f"{i} stars") for i in range(1, 6)],
        help_text="User rating from 1-5 stars"
    )
    comment = models.TextField(
        blank=True,
        max_length=500,
        help_text="Optional detailed feedback comment"
    )
    
    # Page context
    page_url = models.CharField(max_length=500)
    page_type = models.CharField(
        max_length=50,
        choices=[
            ('home', 'Homepage'),
            ('explore', 'Explore Page'),
            ('place_detail', 'Place Detail'),
            ('prayer_times', 'Prayer Times'),
            ('blog', 'Blog'),
            ('submit', 'Submit Place'),
            ('other', 'Other'),
        ]
    )
    page_title = models.CharField(max_length=200, blank=True)
    
    # User behavior metrics
    time_on_site = models.IntegerField(
        help_text="Seconds spent on site before feedback"
    )
    time_on_page = models.IntegerField(
        help_text="Seconds on current page"
    )
    pages_visited = models.IntegerField(default=1)
    scroll_depth = models.IntegerField(
        help_text="Percentage of page scrolled (0-100)",
        null=True,
        blank=True
    )
    
    # Technical context
    language = models.CharField(max_length=5)  # en, ko, uz
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('mobile', 'Mobile'),
            ('tablet', 'Tablet'),
            ('desktop', 'Desktop'),
        ]
    )
    browser = models.CharField(max_length=50, blank=True)
    screen_resolution = models.CharField(max_length=20, blank=True)
    
    # Standard metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Optional admin categorization
    admin_category = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('ui_ux', 'UI/UX'),
            ('content', 'Content Quality'),
            ('bug', 'Bug Report'),
            ('feature', 'Feature Request'),
            ('positive', 'Positive Feedback'),
            ('negative', 'Complaint'),
        ]
    )
    admin_notes = models.TextField(blank=True)
    is_reviewed = models.BooleanField(default=False)
    is_actionable = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback Response'
        verbose_name_plural = 'Feedback Responses'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['rating']),
            models.Index(fields=['page_type']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else f"Anon-{self.session_id[:8]}"
        return f"{user_str} - {self.rating}★ on {self.page_type} ({self.created_at.strftime('%Y-%m-%d')})"
    
    def mark_as_reviewed(self):
        """Mark feedback as reviewed by admin"""
        self.is_reviewed = True
        self.save(update_fields=['is_reviewed'])

