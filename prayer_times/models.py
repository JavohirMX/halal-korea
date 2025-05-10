from django.db import models
from django.utils import timezone

# Create your models here.

class PrayerTimeCache(models.Model):
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    date = models.DateField()
    prayer_times = models.JSONField()
    last_updated = models.DateTimeField(auto_now=True)
    calculation_method = models.IntegerField(default=3)  # Default to Muslim World League
    asr_method = models.IntegerField(default=1)  # Default to Hanafi
    
    class Meta:
        unique_together = ['city', 'country', 'date', 'calculation_method', 'asr_method']
        indexes = [
            models.Index(fields=['city', 'country', 'date']),
            models.Index(fields=['last_updated']),
        ]
        
    @classmethod
    def get_cached_times(cls, city, country, date, calculation_method=3, asr_method=1):
        """Get cached prayer times if available and not expired"""
        try:
            cache = cls.objects.get(
                city=city,
                country=country,
                date=date,
                calculation_method=calculation_method,
                asr_method=asr_method
            )
            # Check if cache is older than 24 hours
            if timezone.now() - cache.last_updated > timezone.timedelta(hours=24):
                return None
            return cache.prayer_times
        except cls.DoesNotExist:
            return None
            
    @classmethod
    def set_cached_times(cls, city, country, date, prayer_times, calculation_method=3, asr_method=1):
        """Cache prayer times"""
        cls.objects.update_or_create(
            city=city,
            country=country,
            date=date,
            calculation_method=calculation_method,
            asr_method=asr_method,
            defaults={'prayer_times': prayer_times}
        )
