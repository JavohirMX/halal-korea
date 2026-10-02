from unittest.mock import patch

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from .models import ContactMessage
from .forms import ContactForm

User = get_user_model()

TURNSTILE_TOKEN = "test-turnstile-token"
TURNSTILE_SETTINGS = {
    "TURNSTILE_SITEKEY": "1x00000000000000000000AA",
    "TURNSTILE_SECRET": "1x0000000000000000000000000000000AA",
}


class ContactModelTest(TestCase):
    """Test the ContactMessage model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_contact_message_creation(self):
        """Test creating a contact message"""
        message = ContactMessage.objects.create(
            user=self.user,
            name='Test User',
            email='test@example.com',
            subject='Test Subject',
            message='This is a test message',
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(message.name, 'Test User')
        self.assertEqual(message.email, 'test@example.com')
        self.assertEqual(message.subject, 'Test Subject')
        self.assertFalse(message.is_read)
        self.assertIsNone(message.responded_at)
    
    def test_contact_message_str(self):
        """Test the string representation of contact message"""
        message = ContactMessage.objects.create(
            name='Test User',
            email='test@example.com',
            subject='Test Subject',
            message='This is a test message',
            ip_address='127.0.0.1'
        )
        
        self.assertIn('Test User', str(message))
        self.assertIn('Test Subject', str(message))
    
    def test_mark_as_read(self):
        """Test marking message as read"""
        message = ContactMessage.objects.create(
            name='Test User',
            email='test@example.com',
            message='This is a test message',
            ip_address='127.0.0.1'
        )
        
        self.assertFalse(message.is_read)
        message.mark_as_read()
        self.assertTrue(message.is_read)
    
    def test_mark_as_responded(self):
        """Test marking message as responded"""
        message = ContactMessage.objects.create(
            name='Test User',
            email='test@example.com',
            message='This is a test message',
            ip_address='127.0.0.1'
        )
        
        self.assertIsNone(message.responded_at)
        message.mark_as_responded()
        self.assertIsNotNone(message.responded_at)


@override_settings(**TURNSTILE_SETTINGS)
class ContactFormTest(TestCase):
    """Test the ContactForm"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.valid_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message.',
            'cf-turnstile-response': TURNSTILE_TOKEN,
        }
    
    @patch('utils.turnstile.verify_turnstile', return_value=True)
    def test_valid_form_anonymous_user(self, mock_verify):
        """Test valid form for anonymous user"""
        form = ContactForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
    
    @patch('utils.turnstile.verify_turnstile', return_value=True)
    def test_valid_form_authenticated_user(self, mock_verify):
        """Test valid form for authenticated user"""
        form = ContactForm(data=self.valid_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_invalid_without_captcha(self):
        """Contact form clean fails without a Turnstile token."""
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message.',
        }
        form = ContactForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('captcha', form.errors)

    @patch('utils.turnstile.verify_turnstile', return_value=False)
    def test_form_invalid_captcha(self, mock_verify):
        """Contact form clean fails when Turnstile verification fails."""
        form = ContactForm(data=self.valid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('captcha', form.errors)
    
    def test_empty_message(self):
        """Test form with empty message"""
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': '',
            'cf-turnstile-response': TURNSTILE_TOKEN,
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('message', form.errors)
    
    def test_whitespace_only_message(self):
        """Test form with whitespace-only message"""
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': '   ',
            'cf-turnstile-response': TURNSTILE_TOKEN,
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('message', form.errors)
    
    def test_name_too_short(self):
        """Test form with name too short"""
        form_data = {
            'name': 'T',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message.',
            'cf-turnstile-response': TURNSTILE_TOKEN,
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_invalid_email(self):
        """Test form with invalid email"""
        form_data = {
            'name': 'Test User',
            'email': 'invalid-email',
            'subject': 'Test Subject',
            'message': 'This is a test message.',
            'cf-turnstile-response': TURNSTILE_TOKEN,
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
