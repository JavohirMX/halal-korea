from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from unittest.mock import patch, MagicMock
import time

from .tokens import password_reset_token
from .forms import PasswordResetRequestForm, PasswordResetConfirmForm
from .rate_limiting import check_password_reset_rate_limit, record_password_reset_attempt

User = get_user_model()


class PasswordResetTokenTest(TestCase):
    """Test password reset token generation and validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_token_generation(self):
        """Test that tokens are generated correctly"""
        token = password_reset_token.make_token(self.user)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 10)
    
    def test_token_validation(self):
        """Test that valid tokens are accepted"""
        token = password_reset_token.make_token(self.user)
        self.assertTrue(password_reset_token.check_token(self.user, token))
    
    def test_token_invalid_after_password_change(self):
        """Test that tokens become invalid after password change"""
        token = password_reset_token.make_token(self.user)
        
        # Change password
        self.user.set_password('newpassword123')
        self.user.save()
        
        # Token should now be invalid
        self.assertFalse(password_reset_token.check_token(self.user, token))
    
    def test_token_invalid_for_different_user(self):
        """Test that tokens are user-specific"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        token = password_reset_token.make_token(self.user)
        self.assertFalse(password_reset_token.check_token(other_user, token))


class PasswordResetFormsTest(TestCase):
    """Test password reset forms"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_password_reset_request_form_valid(self):
        """Test password reset request form with valid data"""
        form_data = {'email': 'test@example.com'}
        form = PasswordResetRequestForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], 'test@example.com')
    
    def test_password_reset_request_form_email_normalization(self):
        """Test that email is normalized (lowercased and stripped)"""
        form_data = {'email': '  TEST@EXAMPLE.COM  '}
        form = PasswordResetRequestForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], 'test@example.com')
    
    def test_password_reset_request_form_invalid_email(self):
        """Test password reset request form with invalid email"""
        form_data = {'email': 'invalid-email'}
        form = PasswordResetRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_password_reset_confirm_form_valid(self):
        """Test password reset confirm form with valid passwords"""
        form_data = {
            'new_password1': 'newstrongpass123',
            'new_password2': 'newstrongpass123'
        }
        form = PasswordResetConfirmForm(user=self.user, data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_password_reset_confirm_form_password_mismatch(self):
        """Test password reset confirm form with mismatched passwords"""
        form_data = {
            'new_password1': 'newstrongpass123',
            'new_password2': 'differentpass123'
        }
        form = PasswordResetConfirmForm(user=self.user, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('new_password2', form.errors)


class PasswordResetRateLimitingTest(TestCase):
    """Test password reset rate limiting"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_rate_limiting_allows_initial_requests(self):
        """Test that initial requests are allowed"""
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        allowed, error_msg = check_password_reset_rate_limit(request, 'test@example.com')
        self.assertTrue(allowed)
        self.assertEqual(error_msg, "")
    
    @patch('users.rate_limiting.RateLimiter.is_rate_limited')
    def test_rate_limiting_blocks_excessive_requests(self, mock_rate_limited):
        """Test that excessive requests are blocked"""
        mock_rate_limited.return_value = (True, 5, 30)  # limited, count, reset_time
        
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        allowed, error_msg = check_password_reset_rate_limit(request, 'test@example.com')
        self.assertFalse(allowed)
        self.assertIn("Too many password reset requests", error_msg)
    
    def test_record_password_reset_attempt(self):
        """Test that password reset attempts are recorded"""
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        # Should not raise any exceptions
        record_password_reset_attempt(request, 'test@example.com')


class PasswordResetViewsTest(TestCase):
    """Test password reset views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            email_verified=True
        )
    
    def test_password_reset_request_get(self):
        """Test GET request to password reset request page"""
        response = self.client.get(reverse('users:password_reset_request'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset your password')
        self.assertContains(response, 'email')
    
    def test_password_reset_request_post_existing_user(self):
        """Test POST request with existing user email"""
        response = self.client.post(reverse('users:password_reset_request'), {
            'email': 'test@example.com'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password reset email sent')
        
        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset Your Halal Korea Password', mail.outbox[0].subject)
        self.assertIn('test@example.com', mail.outbox[0].to)
    
    def test_password_reset_request_post_nonexistent_user(self):
        """Test POST request with non-existent user email (should still show success)"""
        response = self.client.post(reverse('users:password_reset_request'), {
            'email': 'nonexistent@example.com'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password reset email sent')
        
        # No email should be sent for non-existent user
        self.assertEqual(len(mail.outbox), 0)
    
    def test_password_reset_request_invalid_form(self):
        """Test POST request with invalid form data"""
        response = self.client.post(reverse('users:password_reset_request'), {
            'email': 'invalid-email'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid email address')
    
    @patch('users.views.check_password_reset_rate_limit')
    def test_password_reset_request_rate_limited(self, mock_rate_limit):
        """Test password reset request when rate limited"""
        mock_rate_limit.return_value = (False, "Too many requests")
        
        response = self.client.post(reverse('users:password_reset_request'), {
            'email': 'test@example.com'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect to rate limited page
        self.assertIn('/users/rate-limited/', response.url)
    
    def test_password_reset_confirm_get_valid_token(self):
        """Test GET request to password reset confirm with valid token"""
        token = password_reset_token.make_token(self.user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        response = self.client.get(reverse('users:password_reset_confirm', kwargs={
            'uidb64': uidb64,
            'token': token
        }))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Set new password')
        self.assertContains(response, 'new_password1')
        self.assertContains(response, 'new_password2')
    
    def test_password_reset_confirm_get_invalid_token(self):
        """Test GET request to password reset confirm with invalid token"""
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        response = self.client.get(reverse('users:password_reset_confirm', kwargs={
            'uidb64': uidb64,
            'token': 'invalid-token'
        }))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid reset link')
        self.assertContains(response, 'expired')
    
    def test_password_reset_confirm_post_valid(self):
        """Test POST request to password reset confirm with valid data"""
        token = password_reset_token.make_token(self.user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        response = self.client.post(reverse('users:password_reset_confirm', kwargs={
            'uidb64': uidb64,
            'token': token
        }), {
            'new_password1': 'newstrongpass123',
            'new_password2': 'newstrongpass123'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(response.url, reverse('places:home'))
        
        # Check that password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newstrongpass123'))
        
        # Check that user is logged in
        self.assertIn('_auth_user_id', self.client.session)
    
    def test_password_reset_confirm_post_invalid_passwords(self):
        """Test POST request with invalid password data"""
        token = password_reset_token.make_token(self.user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        response = self.client.post(reverse('users:password_reset_confirm', kwargs={
            'uidb64': uidb64,
            'token': token
        }), {
            'new_password1': 'newpass',
            'new_password2': 'differentpass'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Set new password')
        # Should show form errors
    
    def test_password_reset_confirm_invalid_uid(self):
        """Test password reset confirm with invalid UID"""
        response = self.client.get(reverse('users:password_reset_confirm', kwargs={
            'uidb64': 'invalid-uid',
            'token': 'some-token'
        }))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid password reset link')


class PasswordResetIntegrationTest(TestCase):
    """Integration tests for the complete password reset flow"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123',
            email_verified=True
        )
    
    def test_complete_password_reset_flow(self):
        """Test the complete password reset flow from request to completion"""
        # Step 1: Request password reset
        response = self.client.post(reverse('users:password_reset_request'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        
        # Step 2: Extract reset link from email
        email_body = mail.outbox[0].body
        # Find the reset URL in the email (simplified extraction)
        lines = email_body.split('\n')
        reset_url = None
        for line in lines:
            if '/users/password-reset/' in line and line.strip():
                reset_url = line.strip()
                break
        
        self.assertIsNotNone(reset_url)
        
        # Step 3: Visit reset link
        # Extract path from full URL
        reset_path = reset_url.split('http://testserver')[-1] if 'http://testserver' in reset_url else reset_url
        response = self.client.get(reset_path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Set new password')
        
        # Step 4: Submit new password
        response = self.client.post(reset_path, {
            'new_password1': 'newstrongpass123',
            'new_password2': 'newstrongpass123'
        })
        
        # Should redirect to home page
        self.assertEqual(response.status_code, 302)
        
        # Step 5: Verify password was changed and user is logged in
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newstrongpass123'))
        self.assertFalse(self.user.check_password('oldpass123'))
        
        # User should be logged in
        self.assertIn('_auth_user_id', self.client.session)
    
    def test_login_template_has_forgot_password_link(self):
        """Test that login template includes forgot password link"""
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot your password?')
        self.assertContains(response, reverse('users:password_reset_request'))


class PasswordResetSecurityTest(TestCase):
    """Security tests for password reset functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_token_expires_after_password_change(self):
        """Test that reset tokens become invalid after password change"""
        token = password_reset_token.make_token(self.user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        # Change password directly
        self.user.set_password('changedpass123')
        self.user.save()
        
        # Token should now be invalid
        response = self.client.get(reverse('users:password_reset_confirm', kwargs={
            'uidb64': uidb64,
            'token': token
        }))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid reset link')
    
    def test_no_user_enumeration(self):
        """Test that the system doesn't reveal whether an email exists"""
        # Request reset for existing user
        response1 = self.client.post(reverse('users:password_reset_request'), {
            'email': 'test@example.com'
        })
        
        # Request reset for non-existing user
        response2 = self.client.post(reverse('users:password_reset_request'), {
            'email': 'nonexistent@example.com'
        })
        
        # Both should show the same success message
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response1, 'Password reset email sent')
        self.assertContains(response2, 'Password reset email sent')
    
    def test_csrf_protection(self):
        """Test that password reset forms are protected by CSRF"""
        # POST without CSRF token should fail
        response = self.client.post(reverse('users:password_reset_request'), {
            'email': 'test@example.com'
        }, HTTP_X_CSRFTOKEN='')
        
        self.assertEqual(response.status_code, 403)
    
    def test_email_contains_security_info(self):
        """Test that password reset emails contain security information"""
        self.client.post(reverse('users:password_reset_request'), {
            'email': 'test@example.com'
        })
        
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        
        # Should contain IP address and user agent info
        self.assertIn('IP Address:', email_body)
        self.assertIn('Browser:', email_body)
        self.assertIn('If this wasn\'t you', email_body)
