"""
Management command to check alert rules and trigger notifications.
Should be run periodically via cron (e.g., every 5 minutes).
"""
from django.core.management.base import BaseCommand
from utils.monitoring_alerts import check_alerts
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check alert rules and trigger notifications for monitoring system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
    
    def handle(self, *args, **options):
        verbose = options['verbose']
        
        if verbose:
            self.stdout.write(self.style.SUCCESS('Starting alert check...'))
        
        try:
            triggered_count = check_alerts()
            
            if triggered_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  {triggered_count} alert(s) triggered')
                )
            else:
                if verbose:
                    self.stdout.write(
                        self.style.SUCCESS('✓ No alerts triggered')
                    )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error checking alerts: {e}')
            )
            logger.error(f"Error in check_alerts command: {e}", exc_info=True)
            raise

