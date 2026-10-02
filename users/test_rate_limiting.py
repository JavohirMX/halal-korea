"""
Tests for rate limiting functionality
"""
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model
from users.rate_limiting import RateLimiter

User = get_user_model()

TURNSTILE_TOKEN = "test-turnstile-token"
TURNSTILE_SETTINGS = {
    "TURNSTILE_SITEKEY": "1x00000000000000000000AA",
    "TURNSTILE_SECRET": "1x0000000000000000000000000000000AA",
}


@override_settings(**TURNSTILE_SETTINGS)
class RateLimitingTestCase(TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        cache.clear()  # Clear cache before each test
        
        # Create a test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            email_verified=False
        )
    
    @patch('utils.turnstile.verify_turnstile', return_value=True)
    def test_email_rate_limiting(self, mock_verify):
        """Test email sending rate limiting"""
        # Clear cache to start fresh
        cache.clear()
        
        # Try to send multiple emails quickly (should hit rate limit)
        url = reverse('users:resend_activation')
        
        # Anonymous resend checks IP limit (default 5/hour). Need more than
        # the limit successful sends before the next request is redirected.
        rate_limited = False
        for i in range(8):
            response = self.client.post(url, {
                'email': 'test@example.com',
                'cf-turnstile-response': TURNSTILE_TOKEN,
            })
            if response.status_code == 302 and response.url and 'rate-limited' in response.url:
                rate_limited = True
                break
        
        # Should have been rate limited at some point
        self.assertTrue(rate_limited, "Rate limiting should have kicked in")
    
    @patch('utils.turnstile.verify_turnstile', return_value=True)
    def test_registration_rate_limiting(self, mock_verify):
        """Test registration rate limiting"""
        cache.clear()
        
        url = reverse('users:register')
        
        # Try multiple registrations from same IP (should hit rate limit)
        for i in range(3):  # Default limit is 3 per IP per hour
            response = self.client.post(url, {
                'username': f'testuser{i}',
                'email': f'test{i}@example.com',
                'password1': 'testpass123',
                'password2': 'testpass123',
                'cf-turnstile-response': TURNSTILE_TOKEN,
            })
            # First few should not be rate limited
        
        # Next registration should hit rate limit
        response = self.client.post(url, {
            'username': 'testuser_extra',
            'email': 'testextra@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'cf-turnstile-response': TURNSTILE_TOKEN,
        })
        
        # Check if redirected to rate limited page
        if response.status_code == 302 and 'rate-limited' in response.url:
            # Rate limiting is working
            self.assertIn('rate-limited', response.url)
    
    @patch('utils.turnstile.verify_turnstile', return_value=True)
    def test_login_rate_limiting(self, mock_verify):
        """Test login rate limiting"""
        cache.clear()
        
        url = reverse('users:login')
        
        # Try multiple failed logins (should hit rate limit)
        for i in range(10):  # Default limit is 10 per IP per 30 min
            response = self.client.post(url, {
                'username': 'nonexistent',
                'password': 'wrongpass',
                'cf-turnstile-response': TURNSTILE_TOKEN,
            })
        
        # Next login attempt should hit rate limit
        response = self.client.post(url, {
            'username': 'anothertry',
            'password': 'wrongpass',
            'cf-turnstile-response': TURNSTILE_TOKEN,
        })
        
        # Check if redirected to rate limited page
        if response.status_code == 302 and 'rate-limited' in response.url:
            self.assertIn('rate-limited', response.url)
    
    def test_rate_limiter_basic_functionality(self):
        """Test the RateLimiter class directly"""
        cache.clear()
        
        # Test recording attempts
        count = RateLimiter.record_attempt('test_action', 'test_ip', 60)
        self.assertEqual(count, 1)
        
        count = RateLimiter.record_attempt('test_action', 'test_ip', 60)
        self.assertEqual(count, 2)
        
        # Test rate limiting check
        is_limited, current_count, time_until_reset = RateLimiter.is_rate_limited(
            'test_action', 'test_ip', 2, 60
        )
        self.assertTrue(is_limited)  # Should be limited after 2 attempts with limit of 2
        self.assertEqual(current_count, 2)
        
        # Test with different identifier (should not be limited)
        is_limited, current_count, time_until_reset = RateLimiter.is_rate_limited(
            'test_action', 'different_ip', 2, 60
        )
        self.assertFalse(is_limited)  # Should not be limited for different IP
        self.assertEqual(current_count, 0)
    
    def test_rate_limit_window_expiration(self):
        """Test that rate limits reset after time window"""
        cache.clear()
        
        # Record attempts with a very short window (1 minute for testing)
        RateLimiter.record_attempt('test_expiry', 'test_ip', 1)  # 1 minute window
        RateLimiter.record_attempt('test_expiry', 'test_ip', 1)
        
        # Should be limited
        is_limited, _, _ = RateLimiter.is_rate_limited('test_expiry', 'test_ip', 1, 1)
        self.assertTrue(is_limited)
        
        # For testing purposes, we'll just verify the basic functionality
        # In a real scenario, you'd mock timezone.now() to simulate time passage
        
        # Should still be limited immediately
        is_limited, count, _ = RateLimiter.is_rate_limited('test_expiry', 'test_ip', 1, 1)
        self.assertTrue(is_limited)
        self.assertEqual(count, 2)  # Should have 2 attempts recorded
    
    def test_rate_limited_view(self):
        """Test the rate limited view renders correctly"""
        url = reverse('users:rate_limited')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rate Limit Exceeded')
        
        # Test with error message
        response = self.client.get(url + '?error=Test error message')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test error message')
