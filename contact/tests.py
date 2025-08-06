from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import ContactMessage
from .forms import ContactForm

User = get_user_model()


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


class ContactFormTest(TestCase):
    """Test the ContactForm"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_valid_form_anonymous_user(self):
        """Test valid form for anonymous user"""
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message.'
        }
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_valid_form_authenticated_user(self):
        """Test valid form for authenticated user"""
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message.'
        }
        form = ContactForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_empty_message(self):
        """Test form with empty message"""
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': ''
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
            'message': '   '
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
            'message': 'This is a test message.'
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
            'message': 'This is a test message.'
        }
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
