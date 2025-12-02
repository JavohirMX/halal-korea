from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from places.models import HalalPlace
from reviews.models import Review
from .forms import UserRegistrationForm, UserUpdateForm

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.place = HalalPlace.objects.create(
            name='Test Restaurant',
            description='A test halal restaurant',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='123 Test Street, Seoul',
            status='approved',
            submitted_by=self.user
        )

    def test_user_creation(self):
        """Test that a user can be created"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.preferred_language, 'en')

    def test_favorite_places(self):
        """Test adding and removing favorite places"""
        self.user.favorite_places.add(self.place)
        self.assertIn(self.place, self.user.favorite_places.all())
        
        self.user.favorite_places.remove(self.place)
        self.assertNotIn(self.place, self.user.favorite_places.all())

    def test_user_language_preference(self):
        """Test user language preference"""
        self.user.preferred_language = 'ko'
        self.user.save()
        self.assertEqual(self.user.preferred_language, 'ko')

class UserViewTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # Clear rate limiting cache
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.place = HalalPlace.objects.create(
            name='Test Restaurant',
            description='A test halal restaurant',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='123 Test Street, Seoul',
            status='approved',
            submitted_by=self.user
        )
        self.review = Review.objects.create(
            user=self.user,
            place=self.place,
            rating=5,
            comment='Great place!'
        )

    def test_profile_view(self):
        """Test viewing user profile"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')
        self.assertContains(response, 'testuser')
        self.assertContains(response, 'Test Restaurant')

    def test_edit_profile_view(self):
        """Test editing user profile"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('users:edit_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/edit_profile.html')

        # Test updating profile
        response = self.client.post(
            reverse('users:edit_profile'),
            {
                'username': 'testuser',
                'email': 'newemail@example.com',
                'preferred_language': 'ko'
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirects to profile
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')
        self.assertEqual(self.user.preferred_language, 'ko')

    def test_toggle_favorite(self):
        """Test toggling favorite places"""
        self.client.login(username='testuser', password='testpass123')
        
        # Add to favorites
        response = self.client.post(
            reverse('users:toggle_favorite', args=[self.place.id])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'added')
        self.assertIn(self.place, self.user.favorite_places.all())
        
        # Remove from favorites
        response = self.client.post(
            reverse('users:toggle_favorite', args=[self.place.id])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'removed')
        self.assertNotIn(self.place, self.user.favorite_places.all())

    def test_login_view(self):
        """Test user login"""
        response = self.client.post(
            reverse('users:login'),
            {
                'username': 'testuser',
                'password': 'testpass123'
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirects to home

    def test_logout_view(self):
        """Test user logout"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('users:logout'))
        self.assertEqual(response.status_code, 302)  # Redirects to home

    def test_register_view(self):
        """Test user registration"""
        response = self.client.post(
            reverse('users:register'),
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password1': 'newpass123',
                'password2': 'newpass123'
            }
        )
        # Can either redirect or render check_email page
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(User.objects.filter(username='newuser').exists())

class UserFormTest(TestCase):
    def test_registration_form_valid(self):
        """Test registration form validation with valid data"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'newpass123',
            'password2': 'newpass123'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_registration_form_invalid(self):
        """Test registration form validation with invalid data"""
        form_data = {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'newpass123',
            'password2': 'differentpass'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('password2', form.errors)

    def test_update_form_valid(self):
        """Test update form validation with valid data"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        form_data = {
            'username': 'testuser',
            'email': 'newemail@example.com',
            'preferred_language': 'ko'
        }
        form = UserUpdateForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())

    def test_update_form_invalid(self):
        """Test update form validation with invalid data"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        form_data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'preferred_language': 'invalid'
        }
        form = UserUpdateForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('preferred_language', form.errors)
