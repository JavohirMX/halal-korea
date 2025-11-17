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
