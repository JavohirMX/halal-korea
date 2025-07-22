from django.core.management.base import BaseCommand
from utils.telegram_notifications import send_new_place_notification

class Command(BaseCommand):
    help = 'Test Telegram bot notification system'

    def handle(self, *args, **options):
        """Test the Telegram notification system with sample data"""
        
        self.stdout.write(self.style.SUCCESS('Testing Telegram notification system...'))
        
        # Sample test data
        test_data = {
            'place_id': 999,
            'name': 'Test Halal Restaurant',
            'category': 'restaurant',
            'address': '123 Test Street, Seoul, South Korea',
            'description': 'This is a test notification from the Django management command. If you receive this, your Telegram bot notifications are working correctly!',
            'submitted_by_username': 'test_user',
            'website': 'https://example.com',
            'phone_number': '+82-10-1234-5678',
            'photos_count': 2,
        }
        
        try:
            result = send_new_place_notification(test_data)
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(
                        '✅ Test notification sent successfully! '
                        'Check your Telegram chat for the message.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  Test notification was not sent. '
                        'This could mean notifications are disabled or there was an error. '
                        'Check your settings and logs for more information.'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Error testing Telegram notifications: {str(e)}'
                )
            )
            
        self.stdout.write(
            self.style.SUCCESS('\n📝 To configure Telegram notifications:')
        )
        self.stdout.write('1. Set TELEGRAM_NOTIFICATIONS_ENABLED=True in your .env file')
        self.stdout.write('2. Add your TELEGRAM_BOT_TOKEN from @BotFather')
        self.stdout.write('3. Add your TELEGRAM_CHAT_ID')
        self.stdout.write('4. See readme/TELEGRAM_NOTIFICATIONS.md for detailed setup instructions') 