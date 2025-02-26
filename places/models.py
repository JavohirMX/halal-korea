from django.db import models


# Halal Place model
class HalalPlace(models.Model):
    CATEGORY_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('market', 'Market'),
        ('mosque', 'Mosque'),
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
    latitude = models.FloatField()
    longitude = models.FloatField()
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

    def __str__(self):
        return self.name
