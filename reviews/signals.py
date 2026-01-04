"""
Signals for Reviews app

Handles automatic updates for cached rating fields when reviews are created, updated, or deleted.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Review

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Review)
def update_place_rating_on_review_save(sender, instance, created, **kwargs):
    """
    Update the place's cached rating when a review is created or updated.
    """
    try:
        place = instance.place
        place.update_cached_rating()
        logger.debug(
            f"Updated cached rating for place {place.pk} after review {'creation' if created else 'update'}"
        )
    except Exception as e:
        logger.warning(f"Error updating cached rating for place after review save: {e}")


@receiver(post_delete, sender=Review)
def update_place_rating_on_review_delete(sender, instance, **kwargs):
    """
    Update the place's cached rating when a review is deleted.
    """
    try:
        # The place still exists even though the review is being deleted
        place = instance.place
        place.update_cached_rating()
        logger.debug(f"Updated cached rating for place {place.pk} after review deletion")
    except Exception as e:
        logger.warning(f"Error updating cached rating for place after review delete: {e}")
