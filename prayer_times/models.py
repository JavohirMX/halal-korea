from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, date


class RamadanConfig(models.Model):
    year = models.IntegerField(unique=True, help_text="Gregorian year (e.g. 2026)")
    hijri_year = models.IntegerField(help_text="Hijri year (e.g. 1447)")
    start_date = models.DateField(help_text="First day of fasting per local authority (e.g. KMF)")
    end_date = models.DateField(help_text="Last day of fasting")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="e.g. 'Per KMF announcement on Feb 17'")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ramadan Configuration"
        verbose_name_plural = "Ramadan Configurations"
        ordering = ['-year']

    def __str__(self):
        return f"Ramadan {self.hijri_year} ({self.year})"

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date.")

    @property
    def total_days(self):
        return (self.end_date - self.start_date).days + 1

    @classmethod
    def get_active_config(cls):
        today = date.today()
        try:
            return cls.objects.get(
                is_active=True,
                year=today.year
            )
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(is_active=True, year=today.year).first()


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
            # Convert date string to datetime if needed
            if isinstance(date, str):
                date = datetime.strptime(date, '%d-%m-%Y').date()
                
            cache = cls.objects.get(
                city=city,
                country=country,
                date=date,
                calculation_method=calculation_method,
                asr_method=asr_method
            )
            
            # Check if cache is older than 23 hours
            expiration_time = timezone.now() - timezone.timedelta(hours=23)
            if cache.last_updated < expiration_time:
                cache.delete()  # Delete expired cache
                return None
                
            return cache.prayer_times
        except cls.DoesNotExist:
            return None
            
    @classmethod
    def set_cached_times(cls, city, country, date, prayer_times, calculation_method=3, asr_method=1):
        """Cache prayer times"""
        # Convert date string to datetime if needed
        if isinstance(date, str):
            date = datetime.strptime(date, '%d-%m-%Y').date()
            
        # Ensure calculation_method and asr_method are not None
        calculation_method = calculation_method or 3
        asr_method = asr_method or 1
            
        cls.objects.update_or_create(
            city=city,
            country=country,
            date=date,
            calculation_method=calculation_method,
            asr_method=asr_method,
            defaults={'prayer_times': prayer_times}
        )
