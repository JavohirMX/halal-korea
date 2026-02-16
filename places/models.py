from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


# Halal Place model
class HalalPlace(models.Model):
    CATEGORY_CHOICES = [
        ('restaurant', _('Restaurant')),
        ('market', _('Market')),
        ('mosque', _('Mosque')),
        ('prayer_room', _('Prayer Space')),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
        
    ]
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    location = models.PointField()
    address = models.CharField(max_length=255, db_index=True)
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
    
    # Search optimization fields
    name_romanized = models.CharField(max_length=500, blank=True, null=True, db_index=True,
                                      help_text="Romanized version of Korean name for search")
    name_korean = models.CharField(max_length=500, blank=True, null=True, db_index=True,
                                   help_text="Korean transliteration of English name for search")
    search_vector = SearchVectorField(null=True, blank=True,
                                      help_text="Full-text search vector for efficient searching")
    
    # Denormalized rating fields for performance (updated via signals on Review changes)
    cached_average_rating = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True, db_index=True,
        help_text="Cached average rating to avoid recalculating on every request"
    )
    cached_reviews_count = models.PositiveIntegerField(
        default=0, db_index=True,
        help_text="Cached reviews count to avoid counting on every request"
    )
    
    # Temporary closure fields
    temporary_closure_until = models.DateField(
        null=True, blank=True,
        help_text="Place is temporarily closed until this date"
    )
    temporary_closure_reason = models.CharField(
        max_length=255, blank=True,
        help_text="Reason for temporary closure (e.g., 'Renovation')"
    )
    
    class Meta:
        indexes = [
            GinIndex(fields=['search_vector'], name='places_search_vector_idx'),
            models.Index(fields=['status', 'created_at'], name='place_status_created_idx'),
            models.Index(fields=['status', 'category'], name='place_status_category_idx'),
            models.Index(fields=['category'], name='place_category_idx'),
        ]

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('places:place_detail', kwargs={'pk': self.pk})
    
    def update_search_vector(self):
        """Update the search vector field with weighted content"""
        from django.contrib.postgres.search import SearchVector
        from django.db.models import Value
        
        # Build search content including transliterations
        name_content = self.name or ''
        if self.name_romanized:
            name_content += ' ' + self.name_romanized
        if self.name_korean:
            name_content += ' ' + self.name_korean
        
        HalalPlace.objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector(Value(name_content), weight='A', config='simple') +
                SearchVector('description', weight='B', config='simple') +
                SearchVector('address', weight='C', config='simple')
            )
        )
    
    def update_cached_rating(self):
        """Update cached rating fields from reviews. Called via signal on review changes."""
        from django.db.models import Avg, Count
        from decimal import Decimal, ROUND_HALF_UP
        
        stats = self.reviews.aggregate(
            avg=Avg('rating'),
            count=Count('id')
        )
        
        if stats['avg'] is not None:
            # Round to 1 decimal place
            self.cached_average_rating = Decimal(str(stats['avg'])).quantize(
                Decimal('0.1'), rounding=ROUND_HALF_UP
            )
        else:
            self.cached_average_rating = None
        
        self.cached_reviews_count = stats['count'] or 0
        self.save(update_fields=['cached_average_rating', 'cached_reviews_count'])


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
    original_image = models.ImageField(
        upload_to='place_suggestions/originals/',
        help_text="Original uploaded image (without watermark)",
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to='place_suggestions/',
        help_text="Watermarked image for display"
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
    
    def save(self, *args, **kwargs):
        """Override save to apply watermark automatically"""
        from django.core.files.base import ContentFile
        from django.conf import settings
        from utils.watermark import apply_watermark_to_uploaded_file
        import io
        from pathlib import Path
        
        # Check if watermarking is enabled
        watermark_enabled = getattr(settings, 'WATERMARK_ENABLED', True)
        
        # If this is a new upload (not yet saved) and watermarking is enabled
        if not self.pk and self.image and watermark_enabled:
            # Save original image BEFORE watermarking
            if not self.original_image:
                # Read the original file content and create a separate copy
                original_file = self.image.file
                original_file.seek(0)  # Ensure we're at the beginning
                original_content = original_file.read()
                
                # Create a new ContentFile with the original content
                original_filename = Path(self.image.name).name
                self.original_image.save(
                    original_filename,
                    ContentFile(original_content),
                    save=False
                )
                
                # Reset the file pointer for watermarking
                original_file.seek(0)
            
            # Apply watermark to the image
            try:
                # Get the uploaded file (use original_image if available, otherwise image)
                uploaded_file = self.original_image.file if self.original_image else self.image.file
                uploaded_file.seek(0)  # Ensure we're at the beginning
                
                # Apply watermark
                watermarked_img = apply_watermark_to_uploaded_file(uploaded_file)
                
                # Convert PIL image to file
                img_io = io.BytesIO()
                
                # Determine format based on original filename
                original_ext = Path(self.image.name).suffix.lower()
                if original_ext in ['.jpg', '.jpeg']:
                    # Convert to RGB for JPEG
                    watermarked_img = watermarked_img.convert('RGB')
                    watermarked_img.save(img_io, format='JPEG', quality=95)
                else:
                    # Keep as PNG with transparency
                    watermarked_img.save(img_io, format='PNG')
                
                img_io.seek(0)
                
                # Replace the image field with watermarked version
                watermarked_filename = f"wm_{Path(self.image.name).name}"
                self.image.save(
                    watermarked_filename,
                    ContentFile(img_io.read()),
                    save=False
                )
                
            except Exception as e:
                # Log error but don't fail the save
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error applying watermark to image: {str(e)}", exc_info=True)
        
        super().save(*args, **kwargs)
    
    def reapply_watermark(self, opacity=None, angle=None, spacing=None):
        """Reapply watermark with custom settings"""
        from django.core.files.base import ContentFile
        from utils.watermark import apply_watermark_to_uploaded_file
        import io
        from pathlib import Path
        
        if not self.original_image:
            raise ValueError("No original image available to watermark")
        
        try:
            # Open original image
            original_file = self.original_image.file
            original_file.seek(0)
            
            # Apply watermark with custom settings
            watermarked_img = apply_watermark_to_uploaded_file(
                original_file,
                opacity=opacity,
                angle=angle,
                spacing=spacing
            )
            
            # Convert PIL image to file
            img_io = io.BytesIO()
            
            # Determine format
            original_ext = Path(self.original_image.name).suffix.lower()
            if original_ext in ['.jpg', '.jpeg']:
                watermarked_img = watermarked_img.convert('RGB')
                watermarked_img.save(img_io, format='JPEG', quality=95)
            else:
                watermarked_img.save(img_io, format='PNG')
            
            img_io.seek(0)
            
            # Replace the watermarked image
            watermarked_filename = f"wm_{Path(self.original_image.name).name}"
            self.image.save(
                watermarked_filename,
                ContentFile(img_io.read()),
                save=True
            )
            
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error reapplying watermark: {str(e)}", exc_info=True)
            return False


# Business Hours model
class BusinessHours(models.Model):
    """Business hours for a place with support for multiple time slots per day."""
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    place = models.OneToOneField(
        HalalPlace,
        on_delete=models.CASCADE,
        related_name='business_hours'
    )
    is_24_hours = models.BooleanField(
        default=False,
        help_text="Open 24 hours, 7 days a week"
    )
    notes = models.CharField(
        max_length=255, blank=True,
        help_text="Additional notes (e.g., 'Last order 30 min before close')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Business Hours'
        verbose_name_plural = 'Business Hours'
    
    def __str__(self):
        if self.is_24_hours:
            return f"{self.place.name} - Open 24 Hours"
        return f"{self.place.name} - Business Hours"


# Time Slot model for individual day hours
class TimeSlot(models.Model):
    """Individual time slot for a specific day (supports multiple per day)."""
    business_hours = models.ForeignKey(
        BusinessHours,
        on_delete=models.CASCADE,
        related_name='time_slots'
    )
    day_of_week = models.IntegerField(
        choices=BusinessHours.DAY_CHOICES,
        help_text="Day of the week (0=Monday, 6=Sunday)"
    )
    is_closed = models.BooleanField(
        default=False,
        help_text="Mark this day as closed (overrides time fields)"
    )
    open_time = models.TimeField(
        null=True, blank=True,
        help_text="Opening time in 24-hour format"
    )
    close_time = models.TimeField(
        null=True, blank=True,
        help_text="Closing time in 24-hour format"
    )
    
    class Meta:
        ordering = ['day_of_week', 'open_time']
        verbose_name = 'Time Slot'
        verbose_name_plural = 'Time Slots'
    
    def __str__(self):
        day_name = dict(BusinessHours.DAY_CHOICES).get(self.day_of_week, 'Unknown')
        if self.is_closed:
            return f"{day_name}: Closed"
        if self.open_time and self.close_time:
            return f"{day_name}: {self.open_time.strftime('%H:%M')} - {self.close_time.strftime('%H:%M')}"
        return f"{day_name}: Not set"


# Business Hours Suggestion model
class BusinessHoursSuggestion(models.Model):
    """User suggestion for business hours changes."""
    SUGGESTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    place = models.ForeignKey(
        HalalPlace,
        on_delete=models.CASCADE,
        related_name='hours_suggestions'
    )
    suggested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hours_suggestions'
    )
    
    # Suggested schedule stored as structured JSON
    # Format: {"0": [{"open": "09:00", "close": "22:00"}], "1": "closed", ...}
    suggested_hours = models.JSONField(
        help_text="Full weekly schedule as structured JSON"
    )
    is_24_hours = models.BooleanField(
        default=False,
        help_text="Suggested as open 24 hours"
    )
    suggested_notes = models.CharField(
        max_length=255, blank=True,
        help_text="Suggested notes for business hours"
    )
    reason = models.TextField(
        help_text="Why this change is needed"
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
        null=True, blank=True,
        related_name='reviewed_hours_suggestions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Business Hours Suggestion'
        verbose_name_plural = 'Business Hours Suggestions'
    
    def __str__(self):
        return f"Hours suggestion for {self.place.name} by {self.suggested_by.username}"


# Search Query Analytics model
class SearchQuery(models.Model):
    """Track search queries for analytics and improving search results"""
    query = models.CharField(max_length=255, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_queries'
    )
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    results_count = models.PositiveIntegerField(default=0)
    category_filter = models.CharField(max_length=20, blank=True, null=True)
    clicked_place = models.ForeignKey(
        HalalPlace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_clicks',
        help_text="Place the user clicked from search results"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Search Query'
        verbose_name_plural = 'Search Queries'
    
    def __str__(self):
        return f'"{self.query}" ({self.results_count} results)'


class ProximityLocation(models.Model):
    """
    Known locations for proximity search (e.g., "near Hongdae", "in Gangnam").
    These are searchable area names with their center coordinates.
    """
    name = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="Location name in English (lowercase, e.g., 'hongdae', 'gangnam')"
    )
    name_korean = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        db_index=True,
        help_text="Location name in Korean (e.g., '홍대', '강남')"
    )
    aliases = models.JSONField(
        default=list, 
        blank=True,
        help_text="Alternative names/spellings as JSON list (e.g., ['hongik', 'hongik university'])"
    )
    latitude = models.FloatField(help_text="Center latitude of this area")
    longitude = models.FloatField(help_text="Center longitude of this area")
    is_active = models.BooleanField(default=True, help_text="Whether this location is searchable")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Proximity Location'
        verbose_name_plural = 'Proximity Locations'
    
    def __str__(self):
        if self.name_korean:
            return f"{self.name} ({self.name_korean})"
        return self.name
    
    @property
    def coordinates(self):
        """Return (latitude, longitude) tuple"""
        return (self.latitude, self.longitude)
    
    @classmethod
    def get_locations_dict(cls):
        """
        Get all active locations as a dictionary for search.
        Cached for performance.
        """
        from django.core.cache import cache
        
        cache_key = 'proximity_locations_dict'
        locations = cache.get(cache_key)
        
        if locations is None:
            locations = {}
            for loc in cls.objects.filter(is_active=True):
                coords = (loc.latitude, loc.longitude)
                # Add main name
                locations[loc.name.lower()] = coords
                # Add Korean name if exists
                if loc.name_korean:
                    locations[loc.name_korean] = coords
                # Add aliases
                for alias in (loc.aliases or []):
                    locations[alias.lower()] = coords
            
            # Cache for 5 minutes
            cache.set(cache_key, locations, 300)
        
        return locations
    
    def save(self, *args, **kwargs):
        # Clear cache when location is saved
        from django.core.cache import cache
        cache.delete('proximity_locations_dict')
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Clear cache when location is deleted
        from django.core.cache import cache
        cache.delete('proximity_locations_dict')
        super().delete(*args, **kwargs)
