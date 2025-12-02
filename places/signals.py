"""
Signals for Places app

Handles automatic updates for search-related fields when places are saved.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import HalalPlace
from utils.transliteration import generate_transliterations

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=HalalPlace)
def update_place_transliterations(sender, instance, **kwargs):
    """
    Auto-generate transliterations for place names before saving.
    """
    try:
        # Check if name has changed or transliterations are missing
        if instance.pk:
            try:
                old_instance = HalalPlace.objects.get(pk=instance.pk)
                name_changed = old_instance.name != instance.name
            except HalalPlace.DoesNotExist:
                name_changed = True
        else:
            name_changed = True
        
        # Only update if name changed or transliterations are missing
        if name_changed or not instance.name_romanized or not instance.name_korean:
            transliterations = generate_transliterations(instance.name)
            
            if transliterations.get('romanized'):
                instance.name_romanized = transliterations['romanized']
            
            if transliterations.get('korean'):
                instance.name_korean = transliterations['korean']
                
    except Exception as e:
        logger.warning(f"Error generating transliterations for place {instance.pk}: {e}")


@receiver(post_save, sender=HalalPlace)
def update_place_search_vector(sender, instance, created, **kwargs):
    """
    Update search vector after place is saved.
    """
    try:
        # Only update search vector if place is approved
        if instance.status == 'approved':
            instance.update_search_vector()
    except Exception as e:
        logger.warning(f"Error updating search vector for place {instance.pk}: {e}")
