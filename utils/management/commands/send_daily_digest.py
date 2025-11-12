"""
Management command to send daily monitoring digest email.
Should be run once per day via cron (e.g., at 8 AM).
"""
from django.core.management.base import BaseCommand
from utils.monitoring_emails import send_daily_digest
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send daily monitoring digest email to admins'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Sending daily digest email...'))
        
        try:
            success = send_daily_digest()
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('✓ Daily digest email sent successfully')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Daily digest email not sent (disabled or no recipients)')
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error sending daily digest: {e}')
            )
            logger.error(f"Error in send_daily_digest command: {e}", exc_info=True)
            raise

