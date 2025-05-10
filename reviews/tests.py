from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from places.models import HalalPlace
from .models import Review
from .forms import ReviewForm

User = get_user_model()

class ReviewModelTest(TestCase):
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
        self.review = Review.objects.create(
            user=self.user,
            place=self.place,
            rating=5,
            comment='Great place!'
        )

    def test_review_creation(self):
        """Test that a review can be created"""
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.comment, 'Great place!')
        self.assertEqual(self.review.user, self.user)
        self.assertEqual(self.review.place, self.place)

    def test_review_str_method(self):
        """Test the string representation of a review"""
        expected_str = f'Review by {self.user.username} for {self.place.name}'
        self.assertEqual(str(self.review), expected_str)

    def test_unique_review_constraint(self):
        """Test that a user can only review a place once"""
        with self.assertRaises(Exception):
            Review.objects.create(
                user=self.user,
                place=self.place,
                rating=4,
                comment='Another review'
            )

class ReviewViewTest(TestCase):
    def setUp(self):
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

    def test_add_review_requires_login(self):
        """Test that adding a review requires login"""
        response = self.client.post(
            reverse('reviews:add_review', args=[self.place.id]),
            {'rating': 5, 'comment': 'Great place!'}
        )
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_add_review_authenticated(self):
        """Test adding a review when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('reviews:add_review', args=[self.place.id]),
            {'rating': 5, 'comment': 'Great place!'}
        )
        self.assertEqual(response.status_code, 302)  # Redirects to place detail
        self.assertTrue(Review.objects.filter(
            user=self.user,
            place=self.place,
            rating=5,
            comment='Great place!'
        ).exists())

    def test_add_review_invalid_rating(self):
        """Test adding a review with invalid rating"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('reviews:add_review', args=[self.place.id]),
            {'rating': 6, 'comment': 'Great place!'}
        )
        self.assertEqual(response.status_code, 302)  # Redirects to place detail
        self.assertFalse(Review.objects.filter(
            user=self.user,
            place=self.place
        ).exists())

    def test_edit_review(self):
        """Test editing a review"""
        review = Review.objects.create(
            user=self.user,
            place=self.place,
            rating=3,
            comment='Okay place'
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('reviews:edit_review', args=[review.id]),
            {'rating': 4, 'comment': 'Better than okay'}
        )
        self.assertEqual(response.status_code, 302)  # Redirects to place detail
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, 'Better than okay')

    def test_delete_review(self):
        """Test deleting a review"""
        review = Review.objects.create(
            user=self.user,
            place=self.place,
            rating=3,
            comment='Okay place'
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('reviews:delete_review', args=[review.id])
        )
        self.assertEqual(response.status_code, 302)  # Redirects to place detail
        self.assertFalse(Review.objects.filter(id=review.id).exists())

    def test_ajax_add_review(self):
        """Test adding a review via AJAX"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('reviews:add_review', args=[self.place.id]),
            {'rating': 5, 'comment': 'Great place!'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['review']['rating'], 5)
        self.assertEqual(data['review']['content'], 'Great place!')

class ReviewFormTest(TestCase):
    def setUp(self):
        self.form_data = {
            'rating': 5,
            'comment': 'Great place!'
        }

    def test_form_valid(self):
        """Test form validation with valid data"""
        form = ReviewForm(data=self.form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_rating(self):
        """Test form validation with invalid rating"""
        form_data = self.form_data.copy()
        form_data['rating'] = 6  # Rating should be between 1 and 5
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)

    def test_form_empty_comment(self):
        """Test form validation with empty comment"""
        form_data = self.form_data.copy()
        form_data['comment'] = ''
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())  # Comment is required
        self.assertIn('comment', form.errors)
