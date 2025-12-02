"""
Management command to populate search vectors and transliterations for all places.

Usage:
    python manage.py populate_search_data
    python manage.py populate_search_data --force  # Re-populate even if already set
"""

from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from django.db.models import Value

from places.models import HalalPlace
from utils.transliteration import generate_transliterations


class Command(BaseCommand):
    help = 'Populate search vectors and transliterations for all places'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-populate even if data already exists',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of places to process in each batch',
        )

    def handle(self, *args, **options):
        force = options['force']
        batch_size = options['batch_size']
        
        self.stdout.write('Starting search data population...')
        
        # Get places to update
        if force:
            places = HalalPlace.objects.all()
        else:
            # Only places without transliterations
            places = HalalPlace.objects.filter(
                name_romanized__isnull=True,
                name_korean__isnull=True
            )
        
        total = places.count()
        self.stdout.write(f'Found {total} places to process')
        
        updated = 0
        errors = 0
        
        for i, place in enumerate(places.iterator(chunk_size=batch_size)):
            try:
                # Generate transliterations
                transliterations = generate_transliterations(place.name)
                
                # Update place
                place.name_romanized = transliterations.get('romanized')
                place.name_korean = transliterations.get('korean')
                place.save(update_fields=['name_romanized', 'name_korean'])
                
                # Update search vector
                place.update_search_vector()
                
                updated += 1
                
                if (i + 1) % batch_size == 0:
                    self.stdout.write(f'Processed {i + 1}/{total} places...')
                    
            except Exception as e:
                errors += 1
                self.stderr.write(f'Error processing place {place.id} ({place.name}): {e}')
        
        self.stdout.write(self.style.SUCCESS(
            f'Done! Updated {updated} places, {errors} errors.'
        ))
        
        # Also update search vectors for all places (in case some were missed)
        self.stdout.write('Updating search vectors for all approved places...')
        
        try:
            # Bulk update search vectors
            HalalPlace.objects.filter(status='approved').update(
                search_vector=(
                    SearchVector('name', weight='A', config='simple') +
                    SearchVector('name_romanized', weight='A', config='simple') +
                    SearchVector('name_korean', weight='A', config='simple') +
                    SearchVector('description', weight='B', config='simple') +
                    SearchVector('address', weight='C', config='simple')
                )
            )
            self.stdout.write(self.style.SUCCESS('Search vectors updated successfully!'))
        except Exception as e:
            self.stderr.write(f'Error updating search vectors: {e}')
            self.stderr.write('You may need to run migrations first.')
