from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from places.models import HalalPlace
from reviews.models import Review
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test data for the Halal Places project'

    def handle(self, *args, **kwargs):
        # Create test users
        self.stdout.write('Creating test users...')
        test_users = []
        for i in range(3):
            user, created = User.objects.get_or_create(
                username=f'testuser{i}',
                email=f'testuser{i}@example.com',
                defaults={'preferred_language': 'EN'}
            )
            if created:
                user.set_password('password123')
                user.save()
            test_users.append(user)

        # Create test places
        self.stdout.write('Creating test places...')
        test_places = []
        for i in range(5):
            place = HalalPlace.objects.create(
                name=f'Test Restaurant {i}',
                description=f'This is a test restaurant {i}',
                category='restaurant',
                latitude=37.5665 + random.random(),
                longitude=126.9780 + random.random(),
                address=f'Test Address {i}, Seoul',
                phone_number=f'010-1234-{i:04d}',
                website=f'http://test{i}.com',
                status='approved',
            )
            test_places.append(place)

        # Create test reviews
        self.stdout.write('Creating test reviews...')
        for user in test_users:
            for place in test_places:
                Review.objects.get_or_create(
                    user=user,
                    place=place,
                    defaults={
                        'rating': random.randint(1, 5),
                        'comment': f'Test review for {place.name}'
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully created test data!')) 