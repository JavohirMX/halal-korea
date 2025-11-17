from django.core.management.base import BaseCommand
from places.models import HalalPlace


class Command(BaseCommand):
    help = 'Clear photo_urls from all HalalPlace objects (does not delete actual files)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleared without making changes',
        )
        parser.add_argument(
            '--status',
            type=str,
            help='Filter by status (e.g., pending, approved, rejected, archived)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        status_filter = options['status']

        # Build query
        queryset = HalalPlace.objects.all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            self.stdout.write(
                self.style.WARNING(f'Filtering by status: {status_filter}')
            )

        # Get count of places with images
        places_with_images = queryset.exclude(photo_urls__isnull=True).exclude(photo_urls=[])
        total_count = places_with_images.count()

        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No places with images found.')
            )
            return

        # Count total images
        total_images = 0
        for place in places_with_images:
            if place.photo_urls:
                total_images += len(place.photo_urls)

        self.stdout.write(
            self.style.WARNING(
                f'\nFound {total_count} place(s) with a total of {total_images} image(s)'
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('\n--- DRY RUN MODE ---')
            )
            self.stdout.write('The following places would have their images cleared:\n')
            for place in places_with_images[:10]:  # Show first 10
                image_count = len(place.photo_urls) if place.photo_urls else 0
                self.stdout.write(
                    f'  - {place.name} (ID: {place.id}) - {image_count} image(s)'
                )
            
            if total_count > 10:
                self.stdout.write(f'  ... and {total_count - 10} more')
            
            self.stdout.write(
                self.style.WARNING(
                    '\nNo changes made. Run without --dry-run to clear images.'
                )
            )
            return

        # Confirm action
        self.stdout.write(
            self.style.WARNING(
                '\nThis will clear photo_urls from all matching places.'
            )
        )
        confirm = input('Are you sure you want to continue? [y/N]: ')
        
        if confirm.lower() != 'y':
            self.stdout.write(
                self.style.ERROR('Operation cancelled.')
            )
            return

        # Clear images
        updated_count = places_with_images.update(photo_urls=None)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully cleared images from {updated_count} place(s)'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                'Note: Actual image files were not deleted from storage.'
            )
        )

