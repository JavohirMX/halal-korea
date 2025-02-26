from django.db import models
from django.conf import settings
from places.models import HalalPlace

# Review model
class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    place = models.ForeignKey(
        HalalPlace,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'place']

    def __str__(self):
        return f'Review by {self.user.username} for {self.place.name}'
