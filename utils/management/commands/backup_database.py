import os
import gzip
import shutil  # noqa: F401
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from decouple import config


class Command(BaseCommand):
    help = 'Creates database backup and sends to Telegram if changes detected'

    def __init__(self):
        super().__init__()
        self.backup_dir = Path(settings.BASE_DIR) / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        # Telegram configuration
        self.bot_token = config('TELEGRAM_BOT_TOKEN', default=None)
        self.channel_id = config('TELEGRAM_CHANNEL_ID', default=None)
        self.backup_enabled = config('BACKUP_ENABLED', default=True, cast=bool)
        
        # Database configuration
        self.db_config = settings.DATABASES['default']

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force backup even if no changes detected',
        )

    def handle(self, *args, **options):
        if not self.backup_enabled:
            self.stdout.write(self.style.WARNING('Database backup is disabled'))
            return

        if not self.bot_token or not self.channel_id:
            raise CommandError('TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set')

        try:
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'backup_{timestamp}.sql.gz'
            backup_path = self.backup_dir / backup_filename

            # Create database backup
            self.stdout.write('Creating database backup...')
            self._create_backup(backup_path)

            # Check if changes detected or force backup
            changes_detected = options['force'] or self._changes_detected(backup_path)
            
            if changes_detected:
                self.stdout.write(self.style.SUCCESS('Changes detected or forced backup'))
                
                # Send to Telegram
                self._send_to_telegram(backup_path)
                
                # Clean up old backups (keep only 3)
                self._cleanup_old_backups()
                
                self.stdout.write(self.style.SUCCESS(f'Backup completed: {backup_filename}'))
            else:
                # Remove the new backup if no changes
                backup_path.unlink()
                self.stdout.write(self.style.WARNING('No changes detected, backup skipped'))

        except Exception as e:
            error_msg = f'Backup failed: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            self._send_error_notification(error_msg)
            raise CommandError(error_msg)

    def _create_backup(self, backup_path):
        """Create PostgreSQL database backup using pg_dump"""
        # Prepare pg_dump command
        pg_dump_cmd = [
            'pg_dump',
            '--verbose',
            '--clean',
            '--no-acl',
            '--no-owner',
            f"--host={self.db_config['HOST']}",
            f"--port={self.db_config['PORT']}",
            f"--username={self.db_config['USER']}",
            f"--dbname={self.db_config['NAME']}"
        ]

        # Set environment variable for password
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config['PASSWORD']

        try:
            # Run pg_dump and compress output
            with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                result = subprocess.run(  # noqa: F841
                    pg_dump_cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    check=True,
                    text=True
                )
            
            self.stdout.write(f'Backup created: {backup_path} ({self._get_file_size_mb(backup_path):.2f} MB)')
            
        except subprocess.CalledProcessError as e:
            raise CommandError(f'pg_dump failed: {e.stderr}')
        except Exception as e:
            raise CommandError(f'Backup creation failed: {str(e)}')

    def _changes_detected(self, new_backup_path):
        """Check if database has changed by comparing file sizes"""
        # Get list of existing backups sorted by modification time
        existing_backups = sorted(
            [f for f in self.backup_dir.glob('backup_*.sql.gz') if f != new_backup_path],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        if not existing_backups:
            # No previous backup exists
            return True

        # Compare with the most recent backup
        latest_backup = existing_backups[0]
        new_size = new_backup_path.stat().st_size
        old_size = latest_backup.stat().st_size
        
        # Consider changes if size difference is more than 1KB
        size_diff = abs(new_size - old_size)
        threshold = 1024  # 1KB
        
        self.stdout.write(f'Size comparison: {self._get_file_size_mb(new_backup_path):.2f} MB vs {self._get_file_size_mb(latest_backup):.2f} MB')
        
        return size_diff > threshold

    def _send_to_telegram(self, backup_path):
        """Send backup file to Telegram channel"""
        url = f'https://api.telegram.org/bot{self.bot_token}/sendDocument'
        
        # Prepare file info
        file_size_mb = self._get_file_size_mb(backup_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        caption = (
            f"🗄️ <b>Halal Korea Database Backup</b>\n"
            f"📅 <b>Date:</b> {timestamp}\n"
            f"📊 <b>Size:</b> {file_size_mb:.2f} MB\n"
            f"🏷️ <b>Database:</b> {self.db_config['NAME']}\n"
            f"✅ <b>Status:</b> Success"
        )

        # Check Telegram file size limit (50MB for bots)
        if file_size_mb > 50:
            self._send_error_notification(f'Backup file too large for Telegram: {file_size_mb:.2f} MB')
            return

        try:
            with open(backup_path, 'rb') as f:
                files = {'document': f}
                data = {
                    'chat_id': self.channel_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(url, files=files, data=data, timeout=300)
                response.raise_for_status()
                
            self.stdout.write(self.style.SUCCESS('Backup sent to Telegram successfully'))
            
        except requests.exceptions.RequestException as e:
            raise CommandError(f'Failed to send backup to Telegram: {str(e)}')

    def _send_error_notification(self, error_message):
        """Send error notification to Telegram"""
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = (
            f"🚨 <b>Halal Korea Backup Error</b>\n"
            f"📅 <b>Time:</b> {timestamp}\n"
            f"❌ <b>Error:</b> {error_message}\n"
            f"🏷️ <b>Database:</b> {self.db_config['NAME']}"
        )

        try:
            data = {
                'chat_id': self.channel_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
        except requests.exceptions.RequestException:
            # Ignore telegram errors when sending error notifications
            pass

    def _cleanup_old_backups(self):
        """Keep only the 3 most recent backups"""
        backups = sorted(
            self.backup_dir.glob('backup_*.sql.gz'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # Keep only the 3 most recent backups
        for old_backup in backups[3:]:
            old_backup.unlink()
            self.stdout.write(f'Removed old backup: {old_backup.name}')

    def _get_file_size_mb(self, file_path):
        """Get file size in MB"""
        return file_path.stat().st_size / (1024 * 1024) 