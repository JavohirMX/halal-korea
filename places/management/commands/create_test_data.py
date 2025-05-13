from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from places.models import HalalPlace
from reviews.models import Review
from django.contrib.gis.geos import Point
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test data for development'

    def handle(self, *args, **kwargs):
        # Create test users
        self.stdout.write('Creating test users...')
        users = []
        for i in range(6,15):
            user, created = User.objects.get_or_create(
                username=f'testuser{i}',
                email=f'testuser{i}@example.com',
                defaults={'password': 'testpass123'}
            )
            if created:
                user.set_password('testpass123')
                user.save()
            users.append(user)
        
        # Create test places
        self.stdout.write('Creating test places...')
        places = []
        categories = ['restaurant', 'market', 'mosque']
        
        for i in range(20,60):
            longitude = 126.9780 + random.uniform(-0.3, 0.3)
            latitude = 37.5665 + random.uniform(-0.3, 0.3)
            place, created = HalalPlace.objects.get_or_create(
                name=f'Test Place {i}',
                defaults={
                    'description': f'This is test place {i}',
                    'category': random.choice(categories),
                    'location': Point(longitude, latitude),
                    'address': f'Test Address {i}, Seoul',
                    'phone_number': f'010-1234-{i:04d}',
                    'website': f'http://example{i}.com',
                    'status': 'approved',
                    'submitted_by': random.choice(users)
                }
            )
            if created:
                places.append(place)
        
        # Create test reviews
        self.stdout.write('Creating test reviews...')
        approved_places = HalalPlace.objects.filter(status='approved')
        for place in approved_places:
            # Get users who haven't reviewed this place yet
            existing_reviewers = Review.objects.filter(place=place).values_list('user', flat=True)
            available_users = [user for user in users if user.id not in existing_reviewers]
            
            # Create reviews with remaining users
            num_reviews = min(random.randint(1, 5), len(available_users))
            for user in random.sample(available_users, num_reviews):
                Review.objects.create(
                    place=place,
                    user=user,
                    rating=random.randint(1, 5),
                    comment=f'This is a test review for {place.name}'
                )
        
        # Add favorite places
        self.stdout.write('Adding favorite places...')
        for user in users:
            # Get random number of approved places to favorite
            num_favorites = random.randint(1, min(5, approved_places.count()))
            places_to_favorite = random.sample(list(approved_places), num_favorites)
            user.favorite_places.add(*places_to_favorite)

        self.stdout.write(self.style.SUCCESS('Successfully created test data')) 