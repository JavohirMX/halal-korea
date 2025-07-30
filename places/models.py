from django.conf import settings
from django.contrib.gis.db import models


# Halal Place model
class HalalPlace(models.Model):
    CATEGORY_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('market', 'Market'),
        ('mosque', 'Mosque'),
        ('prayer_room', 'Prayer Room'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
        
    ]
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    location = models.PointField()
    address = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    google_map_link = models.URLField(blank=True, null=True)
    kakao_map_link = models.URLField(blank=True, null=True)
    naver_map_link = models.URLField(blank=True, null=True)
    photo_urls = models.JSONField(blank=True, null=True)  # Array of URLs
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_places'
    )

    def __str__(self):
        return self.name


# Place Edit Suggestion model for field changes
class PlaceEditSuggestion(models.Model):
    SUGGESTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    EDITABLE_FIELDS = [
        ('name', 'Name'),
        ('description', 'Description'),
        ('category', 'Category'),
        ('address', 'Address'),
        ('phone_number', 'Phone Number'),
        ('website', 'Website'),
        ('google_map_link', 'Google Map Link'),
        ('kakao_map_link', 'Kakao Map Link'),
        ('naver_map_link', 'Naver Map Link'),
        ('location', 'Location'),
    ]
    
    place = models.ForeignKey(
        HalalPlace,
        on_delete=models.CASCADE,
        related_name='edit_suggestions'
    )
    suggested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='place_suggestions'
    )
    field_name = models.CharField(max_length=50, choices=EDITABLE_FIELDS)
    current_value = models.TextField(blank=True, null=True)
    suggested_value = models.TextField()
    reason = models.TextField(
        help_text="Please explain why this change is needed"
    )
    status = models.CharField(
        max_length=20, 
        choices=SUGGESTION_STATUS_CHOICES, 
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_suggestions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.place.name} - {self.get_field_name_display()} edit by {self.suggested_by.username}"


# Place Image Suggestion model for image uploads
class PlaceImageSuggestion(models.Model):
    SUGGESTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    place = models.ForeignKey(
        HalalPlace,
        on_delete=models.CASCADE,
        related_name='image_suggestions'
    )
    suggested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='image_suggestions'
    )
    image = models.ImageField(
        upload_to='place_suggestions/',
        help_text="Upload an image for this place"
    )
    caption = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Optional caption for the image"
    )
    status = models.CharField(
        max_length=20, 
        choices=SUGGESTION_STATUS_CHOICES, 
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_image_suggestions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Image for {self.place.name} by {self.suggested_by.username}"
