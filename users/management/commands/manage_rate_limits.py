"""
Django management command to manage rate limits
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Manage rate limits for users and IPs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['list', 'clear', 'clear-ip', 'clear-user'],
            default='list',
            help='Action to perform: list, clear, clear-ip, clear-user'
        )
        parser.add_argument(
            '--ip',
            type=str,
            help='IP address to clear rate limits for'
        )
        parser.add_argument(
            '--user-id',
            type=str,
            help='User ID to clear rate limits for'
        )
        parser.add_argument(
            '--action-type',
            type=str,
            choices=['email_send_ip', 'email_send_user', 'registration_ip', 'login_ip'],
            help='Type of action to clear rate limits for'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            self.list_rate_limits()
        elif action == 'clear':
            self.clear_all_rate_limits()
        elif action == 'clear-ip':
            if not options['ip']:
                self.stderr.write('Error: --ip is required for clear-ip action')
                return
            self.clear_ip_rate_limits(options['ip'], options.get('action_type'))
        elif action == 'clear-user':
            if not options['user_id']:
                self.stderr.write('Error: --user-id is required for clear-user action')
                return
            self.clear_user_rate_limits(options['user_id'], options.get('action_type'))

    def list_rate_limits(self):
        """List current rate limits"""
        self.stdout.write(self.style.SUCCESS('Current Rate Limits:'))
        self.stdout.write('')
        
        # Get all cache keys that start with rate_limit:
        # Note: This is a simplified approach. In production with Redis,
        # you might want to use SCAN or other methods to list keys
        
        rate_limit_keys = [
            'email_send_ip', 'email_send_user', 
            'registration_ip', 'login_ip'
        ]
        
        found_limits = False
        
        for key_type in rate_limit_keys:
            self.stdout.write(f"📧 {key_type.replace('_', ' ').title()}:")
            
            # This is a basic implementation - in a real scenario with Redis,
            # you'd scan for keys matching the pattern
            sample_keys = [
                f"rate_limit:{key_type}:192.168.1.1",
                f"rate_limit:{key_type}:127.0.0.1",
                f"rate_limit:{key_type}:10.0.0.1"
            ]
            
            for cache_key in sample_keys:
                data = cache.get(cache_key)
                if data:
                    found_limits = True
                    identifier = cache_key.split(':')[-1]
                    count = data.get('count', 0)
                    first_attempt = data.get('first_attempt')
                    
                    if first_attempt:
                        time_remaining = self.calculate_time_remaining(first_attempt, 60)  # Assuming 60 min window
                        self.stdout.write(f"  └─ {identifier}: {count} attempts, {time_remaining} min remaining")
            
            if not found_limits:
                self.stdout.write("  └─ No active limits")
            self.stdout.write('')
        
        if not found_limits:
            self.stdout.write(self.style.WARNING('No active rate limits found.'))

    def calculate_time_remaining(self, first_attempt, window_minutes):
        """Calculate time remaining in rate limit window"""
        if not first_attempt:
            return 0
        
        now = timezone.now()
        window_end = first_attempt + timedelta(minutes=window_minutes)
        
        if now >= window_end:
            return 0
        
        return int((window_end - now).total_seconds() / 60)

    def clear_all_rate_limits(self):
        """Clear all rate limits"""
        # Note: This is a simplified approach
        # In production, you'd want to scan for all rate_limit:* keys
        
        self.stdout.write('Clearing all rate limits...')
        
        # Since Django's cache doesn't support pattern deletion,
        # we'll just clear the entire cache for rate limits
        # In production with Redis, you'd use SCAN and DEL
        
        try:
            cache.clear()  # This clears ALL cache, not just rate limits
            self.stdout.write(self.style.SUCCESS('✅ All cache cleared (including rate limits)'))
            self.stdout.write(self.style.WARNING('⚠️  Note: This cleared the entire cache, not just rate limits'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error clearing cache: {e}'))

    def clear_ip_rate_limits(self, ip, action_type=None):
        """Clear rate limits for a specific IP"""
        if action_type:
            cache_key = f"rate_limit:{action_type}:{ip}"
            if cache.delete(cache_key):
                self.stdout.write(self.style.SUCCESS(f'✅ Cleared {action_type} rate limit for IP: {ip}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  No {action_type} rate limit found for IP: {ip}'))
        else:
            # Clear all rate limits for this IP
            action_types = ['email_send_ip', 'registration_ip', 'login_ip']
            cleared = 0
            
            for action in action_types:
                cache_key = f"rate_limit:{action}:{ip}"
                if cache.delete(cache_key):
                    cleared += 1
                    self.stdout.write(f'  ✅ Cleared {action}')
            
            if cleared > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ Cleared {cleared} rate limits for IP: {ip}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  No rate limits found for IP: {ip}'))

    def clear_user_rate_limits(self, user_id, action_type=None):
        """Clear rate limits for a specific user"""
        if action_type:
            if 'user' not in action_type:
                self.stdout.write(self.style.ERROR(f'❌ Action type "{action_type}" is not user-specific'))
                return
            
            cache_key = f"rate_limit:{action_type}:{user_id}"
            if cache.delete(cache_key):
                self.stdout.write(self.style.SUCCESS(f'✅ Cleared {action_type} rate limit for User ID: {user_id}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  No {action_type} rate limit found for User ID: {user_id}'))
        else:
            # Clear all user-specific rate limits
            action_types = ['email_send_user']
            cleared = 0
            
            for action in action_types:
                cache_key = f"rate_limit:{action}:{user_id}"
                if cache.delete(cache_key):
                    cleared += 1
                    self.stdout.write(f'  ✅ Cleared {action}')
            
            if cleared > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ Cleared {cleared} rate limits for User ID: {user_id}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  No rate limits found for User ID: {user_id}'))
