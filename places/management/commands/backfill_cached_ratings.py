"""
Management command to backfill cached rating fields for all places.

Run this after adding the cached_average_rating and cached_reviews_count fields
to populate existing places with their rating data.

Usage:
    python manage.py backfill_cached_ratings
    python manage.py backfill_cached_ratings --batch-size=100
"""

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from places.models import HalalPlace


class Command(BaseCommand):
    help = 'Backfill cached rating fields for all places'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of places to process in each batch (default: 100)'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        
        # Get all place IDs to process
        place_ids = list(HalalPlace.objects.values_list('pk', flat=True))
        total = len(place_ids)
        
        self.stdout.write(f"Processing {total} places in batches of {batch_size}...")
        
        updated = 0
        for i in range(0, total, batch_size):
            batch_ids = place_ids[i:i + batch_size]
            
            # Get aggregated rating data for this batch
            rating_data = HalalPlace.objects.filter(
                pk__in=batch_ids
            ).annotate(
                calc_avg=Avg('reviews__rating'),
                calc_count=Count('reviews')
            ).values('pk', 'calc_avg', 'calc_count')
            
            # Update each place
            for data in rating_data:
                from decimal import Decimal, ROUND_HALF_UP
                
                avg_rating = None
                if data['calc_avg'] is not None:
                    avg_rating = Decimal(str(data['calc_avg'])).quantize(
                        Decimal('0.1'), rounding=ROUND_HALF_UP
                    )
                
                HalalPlace.objects.filter(pk=data['pk']).update(
                    cached_average_rating=avg_rating,
                    cached_reviews_count=data['calc_count'] or 0
                )
                updated += 1
            
            self.stdout.write(f"  Processed {min(i + batch_size, total)}/{total} places...")
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated cached ratings for {updated} places")
        )
