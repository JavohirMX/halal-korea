"""
Management command to send daily digest email to admins.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from utils.monitoring_emails import send_daily_digest


class Command(BaseCommand):
    help = 'Send daily monitoring digest email to admins'
    
    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write(self.style.WARNING('Preparing daily digest...'))
        
        # Check if email alerts are enabled
        if not getattr(settings, 'ALERT_EMAIL_ENABLED', False):
            self.stdout.write(self.style.ERROR('Email alerts are disabled in settings'))
            self.stdout.write('Set ALERT_EMAIL_ENABLED=True to enable')
            return
        
        # Check if recipients are configured
        recipients = getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
        if not recipients:
            self.stdout.write(self.style.ERROR('No email recipients configured'))
            self.stdout.write('Set ALERT_EMAIL_RECIPIENTS in settings')
            return
        
        # Send digest
        self.stdout.write(f'Sending digest to {len(recipients)} recipient(s)...')
        
        success = send_daily_digest()
        
        if success:
            self.stdout.write(self.style.SUCCESS('✓ Daily digest sent successfully'))
        else:
            self.stdout.write(self.style.ERROR('✗ Failed to send daily digest'))
            self.stdout.write('Check logs for more details')
