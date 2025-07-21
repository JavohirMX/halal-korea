# Database Backup System Documentation

## Overview

This project implements an automated database backup system for the Halal Korea Django application. The backup system creates compressed PostgreSQL dumps, detects database changes, and automatically sends backups to a Telegram channel when changes are detected. The system includes local retention policies, error handling, and comprehensive logging.

## Features

### Core Functionality
- **Automated PostgreSQL backups** using `pg_dump`
- **Change detection** via file size comparison
- **Telegram integration** for backup delivery
- **Local retention policy** (keeps last 3 backups)
- **Compression** using gzip to minimize file size
- **Error notifications** sent to Telegram
- **Comprehensive logging** of all backup operations

### Smart Backup Logic
- **First backup**: Always created and sent
- **Subsequent backups**: Only sent if database changes detected
- **Force option**: Manual backup regardless of changes
- **Size threshold**: 1KB difference triggers new backup
- **File limit handling**: Automatic warning for files over Telegram limits

## Configuration

### Environment Variables

Add these variables to your `.env` file:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=your_channel_id_here

# Backup Settings
BACKUP_ENABLED=True
```

### Database Requirements

The system works with PostgreSQL databases configured in Django settings:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
```

### Directory Structure

The backup system creates and manages:

```
project_root/
├── backups/                    # Local backup storage
│   ├── backup_20240115_020000.sql.gz
│   ├── backup_20240116_020000.sql.gz
│   └── backup_20240117_020000.sql.gz
└── logs/
    └── backup.log             # Backup operation logs
```

## Installation

### 1. Telegram Bot Setup

1. **Create a Telegram Bot**:
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Save the bot token

2. **Get Channel ID**:
   - Add your bot to your channel as admin
   - Send a message to the channel
   - Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find your channel ID in the response

3. **Configure Environment**:
   ```env
   TELEGRAM_BOT_TOKEN=1234567890:ABC...XYZ
   TELEGRAM_CHANNEL_ID=-1001234567890
   BACKUP_ENABLED=True
   ```

### 2. System Requirements

Ensure PostgreSQL client tools are installed:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql-client

# macOS
brew install postgresql
```

### 3. Test Installation

Test the backup system:

```bash
# Test backup creation and Telegram delivery
python manage.py backup_database --force

# Test change detection (should skip if no changes)
python manage.py backup_database
```

## Scheduling

### Cron Job Setup

For daily automated backups, set up a cron job:

1. **Open crontab**:
   ```bash
   crontab -e
   ```

2. **Add daily backup at 2:00 AM**:
   ```bash
   0 2 * * * cd /path/to/your/project && python manage.py backup_database >> logs/backup.log 2>&1
   ```

3. **Verify cron job**:
   ```bash
   crontab -l
   ```

### Alternative Scheduling Options

- **Weekly backups**: `0 2 * * 0` (Sunday at 2 AM)
- **Multiple daily**: `0 2,14 * * *` (2 AM and 2 PM)
- **Custom timing**: Adjust hour/minute as needed

## Usage

### Command Line Interface

The backup system is managed through Django's management command:

```bash
# Standard backup (only sends if changes detected)
python manage.py backup_database

# Force backup (always creates and sends)
python manage.py backup_database --force

# Help and options
python manage.py backup_database --help
```

### Command Options

- `--force`: Force backup creation even if no changes detected
- `--help`: Display help information

### Manual Testing

```bash
# Test backup creation
python manage.py backup_database --force

# Check backup directory
ls -la backups/

# View backup logs
tail -f logs/backup.log

# Test change detection
python manage.py backup_database  # Should skip if no changes
```

## Telegram Integration

### Message Formats

#### Success Notification
```
🗄️ Halal Korea Database Backup
📅 Date: 2024-01-15 02:00:00
📊 Size: 2.45 MB
🏷️ Database: halal_korea_db
✅ Status: Success
```

#### Error Notification
```
🚨 Halal Korea Backup Error
📅 Time: 2024-01-15 02:00:00
❌ Error: pg_dump failed: connection refused
🏷️ Database: halal_korea_db
```

### File Handling

- **File size limit**: 50MB (Telegram bot limit)
- **Compression**: Automatic gzip compression
- **Large files**: Error notification if backup exceeds limit
- **File naming**: `backup_YYYYMMDD_HHMMSS.sql.gz`

### Bot Permissions

Ensure your Telegram bot has:
- Permission to send messages to the channel
- Permission to send documents/files
- Admin rights in the channel (recommended)

## Change Detection

### How It Works

The system detects database changes by comparing backup file sizes:

1. **Creates new backup** using `pg_dump`
2. **Compares file size** with most recent existing backup
3. **Threshold check**: Difference > 1KB indicates changes
4. **Decision**: Send to Telegram if changes detected or forced

### Size Comparison Logic

```python
# Example size comparison
new_backup: 2.45 MB
old_backup: 2.43 MB
difference: 0.02 MB (20KB) > 1KB threshold
result: Changes detected → Send to Telegram
```

### False Positives

Minor variations that might trigger backups:
- Database statistics updates
- Index rebuilds
- PostgreSQL internal changes

These are generally insignificant and indicate normal database activity.

## Error Handling

### Common Errors and Solutions

#### 1. Database Connection Errors
```
Error: pg_dump failed: FATAL: password authentication failed
```
**Solution**: Check database credentials in `.env` file

#### 2. Telegram API Errors
```
Error: Failed to send backup to Telegram: HTTP 401 Unauthorized
```
**Solution**: Verify `TELEGRAM_BOT_TOKEN` and bot permissions

#### 3. File Permission Errors
```
Error: Permission denied: cannot create backup directory
```
**Solution**: Ensure write permissions for backup directory

#### 4. Large File Errors
```
Error: Backup file too large for Telegram: 75.50 MB
```
**Solution**: Consider database optimization or alternative storage

### Error Notification System

- **Automatic notifications**: Errors sent to Telegram channel
- **Local logging**: All errors logged to `logs/backup.log`
- **Non-blocking**: Telegram notification failures don't stop backup process
- **Detailed messages**: Include timestamp, error details, and context

## Backup File Management

### Local Retention Policy

- **Keep last 3 backups** locally
- **Automatic cleanup** of older backups
- **Chronological ordering** by creation time
- **Safe deletion** only after successful new backup

### File Naming Convention

```
backup_YYYYMMDD_HHMMSS.sql.gz
│      │        │
│      │        └─ Time (24-hour format)
│      └─ Date (ISO format)
└─ Prefix identifier
```

Examples:
- `backup_20240115_020000.sql.gz` - January 15, 2024, 2:00 AM
- `backup_20240116_143000.sql.gz` - January 16, 2024, 2:30 PM

### Storage Locations

- **Local**: `project_root/backups/`
- **Remote**: Telegram channel (permanent storage)
- **Logs**: `project_root/logs/backup.log`

## Backup Restoration

### Quick Restoration Guide

The backup restoration process allows you to recover your database from any saved backup file. All backups are compressed PostgreSQL dump files that can be restored using standard PostgreSQL tools.

### Prerequisites for Restoration

Before starting restoration:

1. **PostgreSQL access**: Ensure you have database admin privileges
2. **Backup file**: Download backup from Telegram or use local copy
3. **Target database**: Decide whether to restore to existing or new database
4. **Application downtime**: Plan for temporary service interruption

### Restoration Methods

#### Method 1: Full Database Restoration (Recommended)

Complete database replacement - **destroys existing data**:

```bash
# 1. Stop your Django application
sudo systemctl stop your-django-app  # or kill process

# 2. Download backup from Telegram (if needed)
# Save the .sql.gz file to your backups/ directory

# 3. Extract the backup file
gunzip backups/backup_20240115_020000.sql.gz

# 4. Drop existing database (CAUTION: This deletes all data!)
dropdb -h localhost -U your_db_user halal_korea_db

# 5. Create fresh database
createdb -h localhost -U your_db_user halal_korea_db

# 6. Restore from backup
psql -h localhost -U your_db_user -d halal_korea_db < backups/backup_20240115_020000.sql

# 7. Restart your Django application
sudo systemctl start your-django-app
```

#### Method 2: Test Database Restoration

Restore to a separate test database for verification:

```bash
# 1. Extract backup file
gunzip -c backups/backup_20240115_020000.sql.gz > backups/backup_20240115_020000.sql

# 2. Create test database
createdb -h localhost -U your_db_user halal_korea_test

# 3. Restore to test database
psql -h localhost -U your_db_user -d halal_korea_test < backups/backup_20240115_020000.sql

# 4. Verify restoration
psql -h localhost -U your_db_user -d halal_korea_test -c "\dt"  # List tables
psql -h localhost -U your_db_user -d halal_korea_test -c "SELECT COUNT(*) FROM places_halalplace;"
```

#### Method 3: Selective Data Restoration

Restore specific tables or data:

```bash
# 1. Extract backup and create temporary database
gunzip -c backups/backup_20240115_020000.sql.gz > backups/backup_20240115_020000.sql
createdb -h localhost -U your_db_user temp_restore_db
psql -h localhost -U your_db_user -d temp_restore_db < backups/backup_20240115_020000.sql

# 2. Export specific table data
pg_dump -h localhost -U your_db_user -d temp_restore_db \
        --table=places_halalplace --data-only > specific_table.sql

# 3. Restore specific data to main database
psql -h localhost -U your_db_user -d halal_korea_db < specific_table.sql

# 4. Clean up temporary database
dropdb -h localhost -U your_db_user temp_restore_db
```

### Point-in-Time Recovery Scenarios

#### Scenario 1: Data Corruption Recovery

When you discover data corruption:

```bash
# 1. Identify the last known good backup
ls -la backups/ | head -10

# 2. Check backup contents before restoration
gunzip -c backups/backup_20240115_020000.sql.gz | head -50

# 3. Create backup of current state (even if corrupted)
python manage.py backup_database --force

# 4. Restore from good backup (follow Method 1)
```

#### Scenario 2: Accidental Data Deletion

When important data has been accidentally deleted:

```bash
# 1. Immediately stop write operations to prevent further changes
# 2. Identify backup containing the deleted data
# 3. Use Method 3 (Selective Restoration) to recover specific data
# 4. Verify data integrity after restoration
```

#### Scenario 3: Migration Rollback

When a Django migration causes issues:

```bash
# 1. Find pre-migration backup
ls -la backups/ | grep "$(date -d 'yesterday' +%Y%m%d)"

# 2. Restore database to pre-migration state
# 3. Fix migration issues
# 4. Re-run migrations after fixes
```

### Restoration Verification

#### Post-Restoration Checks

After any restoration, verify data integrity:

```python
# Django shell verification commands
python manage.py shell

# Check record counts
from places.models import HalalPlace
from users.models import CustomUser
from reviews.models import Review

print(f"Places: {HalalPlace.objects.count()}")
print(f"Users: {CustomUser.objects.count()}")
print(f"Reviews: {Review.objects.count()}")

# Check recent data
recent_places = HalalPlace.objects.order_by('-created_at')[:5]
for place in recent_places:
    print(f"{place.name} - {place.created_at}")
```

#### Application Testing

```bash
# 1. Run Django tests
python manage.py test

# 2. Check database migrations
python manage.py showmigrations

# 3. Verify admin interface
python manage.py createsuperuser  # if needed

# 4. Test critical functionality
# - User authentication
# - Place creation/editing
# - Review submission
# - Search functionality
```

### Emergency Recovery Procedures

#### Complete System Failure Recovery

When your entire system needs restoration:

```bash
# 1. Set up fresh server/environment
# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your settings

# 4. Download latest backup from Telegram
# 5. Create database and restore
createdb -h localhost -U postgres halal_korea_db
gunzip -c backup_latest.sql.gz | psql -h localhost -U postgres -d halal_korea_db

# 6. Run Django setup
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput

# 7. Start application
python manage.py runserver
```

#### Automated Recovery Script

Create a recovery script for common scenarios:

```bash
#!/bin/bash
# recovery.sh - Automated database recovery script

set -e  # Exit on any error

BACKUP_FILE="$1"
DB_NAME="${DB_NAME:-halal_korea_db}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -la backups/backup_*.sql.gz
    exit 1
fi

echo "🚨 WARNING: This will replace all data in $DB_NAME"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo "📋 Starting recovery process..."

# 1. Create backup of current state
echo "📦 Creating emergency backup of current state..."
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "emergency_backup_$(date +%Y%m%d_%H%M%S).sql.gz"

# 2. Stop Django application (adjust as needed)
echo "🛑 Stopping Django application..."
sudo systemctl stop halal-korea || echo "Could not stop service (may not be running)"

# 3. Drop and recreate database
echo "🗑️ Dropping existing database..."
dropdb -h "$DB_HOST" -U "$DB_USER" "$DB_NAME"

echo "🔨 Creating fresh database..."
createdb -h "$DB_HOST" -U "$DB_USER" "$DB_NAME"

# 4. Restore from backup
echo "📥 Restoring from backup: $BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME"
else
    psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
fi

# 5. Run Django migrations if needed
echo "🔄 Running Django migrations..."
python manage.py migrate --run-syncdb

# 6. Restart application
echo "🚀 Starting Django application..."
sudo systemctl start halal-korea || echo "Could not start service automatically"

echo "✅ Recovery completed successfully!"
echo "📊 Verifying restoration..."

# Basic verification
python manage.py shell -c "
from places.models import HalalPlace
from users.models import CustomUser
print(f'✅ Places: {HalalPlace.objects.count()}')
print(f'✅ Users: {CustomUser.objects.count()}')
print('✅ Database restoration verified')
"
```

Make the script executable:
```bash
chmod +x recovery.sh

# Usage examples
./recovery.sh backups/backup_20240115_020000.sql.gz
./recovery.sh emergency_backup_20240116_143000.sql.gz
```

### Best Practices for Restoration

#### Before Restoration

1. **Create emergency backup** of current state
2. **Stop all write operations** to prevent data conflicts
3. **Document the reason** for restoration in logs
4. **Notify stakeholders** about potential downtime
5. **Test restoration process** in staging environment first

#### During Restoration

1. **Monitor the process** for errors or timeouts
2. **Keep detailed logs** of all commands executed
3. **Verify each step** before proceeding to next
4. **Have rollback plan** ready in case of issues

#### After Restoration

1. **Verify data integrity** through application testing
2. **Check all critical functionality** works correctly
3. **Monitor application logs** for unusual errors
4. **Update team** on completion status
5. **Document lessons learned** for future reference

### Common Restoration Issues

#### Issue 1: Permission Denied
```
ERROR: permission denied for database "halal_korea_db"
```
**Solution**: Ensure database user has CREATEDB privileges:
```sql
ALTER USER your_db_user CREATEDB;
```

#### Issue 2: Database Still in Use
```
ERROR: database "halal_korea_db" is being accessed by other users
```
**Solution**: Terminate active connections:
```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'halal_korea_db';
```

#### Issue 3: Disk Space Issues
```
ERROR: could not write to file: No space left on device
```
**Solution**: 
- Check disk space: `df -h`
- Clean up old backups: `rm -f backups/backup_old_*.sql.gz`
- Use streaming restoration for large backups

#### Issue 4: Character Encoding Problems
```
ERROR: invalid byte sequence for encoding "UTF8"
```
**Solution**: Specify encoding during restoration:
```bash
psql -h localhost -U user -d database --set client_encoding=UTF8 < backup.sql
```

### Automation and Monitoring

#### Restoration Health Checks

Create automated checks to verify restoration success:

```python
# restoration_health_check.py
import os
import sys
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from places.models import HalalPlace
from users.models import CustomUser
from reviews.models import Review

def check_restoration_health():
    """Verify database health after restoration"""
    
    checks = []
    
    # Check record counts
    place_count = HalalPlace.objects.count()
    user_count = CustomUser.objects.count()
    review_count = Review.objects.count()
    
    checks.append(f"✅ Places: {place_count}")
    checks.append(f"✅ Users: {user_count}")  
    checks.append(f"✅ Reviews: {review_count}")
    
    # Check for recent data (should exist if backup is recent)
    recent_threshold = datetime.now() - timedelta(days=7)
    recent_places = HalalPlace.objects.filter(created_at__gte=recent_threshold).count()
    checks.append(f"✅ Recent places (7 days): {recent_places}")
    
    # Check database relationships
    try:
        # Test a complex query
        places_with_reviews = HalalPlace.objects.filter(review__isnull=False).distinct().count()
        checks.append(f"✅ Places with reviews: {places_with_reviews}")
    except Exception as e:
        checks.append(f"❌ Relationship check failed: {e}")
    
    # Check critical functionality
    try:
        # Test user authentication setup
        superusers = CustomUser.objects.filter(is_superuser=True).count()
        checks.append(f"✅ Superusers: {superusers}")
    except Exception as e:
        checks.append(f"❌ User check failed: {e}")
    
    print("🔍 Database Health Check Results:")
    for check in checks:
        print(f"  {check}")
    
    # Overall health score
    passed = len([c for c in checks if c.startswith("✅")])
    total = len(checks)
    print(f"\n📊 Health Score: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Database restoration verified successfully!")
        return True
    else:
        print("⚠️  Some checks failed - investigate issues")
        return False

if __name__ == "__main__":
    success = check_restoration_health()
    sys.exit(0 if success else 1)
```

Run after restoration:
```bash
python restoration_health_check.py
```

This comprehensive restoration guide ensures you can confidently recover your Halal Korea database from any backup, whether dealing with routine maintenance, emergency recovery, or testing scenarios.

## Monitoring and Maintenance

### Log Monitoring

Monitor backup operations through log files:

```bash
# View recent backup logs
tail -20 logs/backup.log

# Monitor backup process in real-time
tail -f logs/backup.log

# Search for errors
grep "ERROR" logs/backup.log

# Check specific dates
grep "2024-01-15" logs/backup.log
```

### Backup Verification

Regularly verify backup integrity:

```bash
# List recent backups
ls -la backups/

# Check backup file sizes
du -h backups/*

# Test backup restoration (in test environment)
gunzip -c backup_20240115_020000.sql.gz | psql test_database
```

### Performance Monitoring

Track backup performance:
- **Backup creation time**: Monitor for increasing duration
- **File sizes**: Watch for unexpected growth
- **Success rate**: Monitor failed backup attempts
- **Change frequency**: Track how often changes are detected

## Security Considerations

### Sensitive Data Protection

- **Password security**: Database password passed via environment variable
- **File permissions**: Backup files readable only by owner
- **Network security**: Encrypted transmission to Telegram
- **Local cleanup**: Automatic removal of old backups

### Access Control

- **Bot token security**: Keep Telegram bot token secret
- **Channel privacy**: Use private Telegram channels
- **Database access**: Dedicated backup user with minimal privileges
- **File system**: Restricted access to backup directory

### Best Practices

1. **Use dedicated database user** for backups with read-only access
2. **Secure bot token** in environment variables, not code
3. **Private Telegram channels** for backup storage
4. **Regular security audits** of backup access logs
5. **Encrypted storage** for additional security layers

## Troubleshooting

### Common Issues

#### Backup Not Created
```bash
# Check database connection
python manage.py dbshell

# Verify pg_dump availability
which pg_dump
pg_dump --version

# Test manual backup
pg_dump -h localhost -U user -d database > test_backup.sql
```

#### Telegram Not Receiving
```bash
# Test bot token
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Test channel access
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d "chat_id=<CHANNEL_ID>&text=Test message"
```

#### Change Detection Issues
```bash
# Check backup directory
ls -la backups/

# Compare file sizes manually
du -b backups/*

# Force backup to test
python manage.py backup_database --force
```

### Debug Mode

Enable detailed logging for troubleshooting:

```python
# Temporary debug settings
import logging
logging.getLogger('utils.management.commands.backup_database').setLevel(logging.DEBUG)
```

### Health Checks

Create a simple health check script:

```python
#!/usr/bin/env python
import os
from pathlib import Path

def check_backup_health():
    backup_dir = Path('backups')
    if not backup_dir.exists():
        print("❌ Backup directory missing")
        return False
    
    backups = list(backup_dir.glob('backup_*.sql.gz'))
    if not backups:
        print("❌ No backups found")
        return False
    
    latest = max(backups, key=lambda x: x.stat().st_mtime)
    age_hours = (time.time() - latest.stat().st_mtime) / 3600
    
    if age_hours > 25:  # More than 25 hours old
        print(f"⚠️  Latest backup is {age_hours:.1f} hours old")
    else:
        print(f"✅ Latest backup: {age_hours:.1f} hours old")
    
    return True

if __name__ == "__main__":
    check_backup_health()
```

## Integration Examples

### Custom Backup Triggers

```python
# In your Django views or signals
from django.core.management import call_command

def on_critical_data_change(sender, **kwargs):
    """Trigger backup on important data changes"""
    try:
        call_command('backup_database', force=True)
    except Exception as e:
        logger.error(f"Emergency backup failed: {e}")
```

### Backup Status API

```python
# Add to your Django views
def backup_status_api(request):
    backup_dir = Path(settings.BASE_DIR) / 'backups'
    backups = list(backup_dir.glob('backup_*.sql.gz'))
    
    if backups:
        latest = max(backups, key=lambda x: x.stat().st_mtime)
        status = {
            'latest_backup': latest.name,
            'backup_count': len(backups),
            'last_modified': latest.stat().st_mtime
        }
    else:
        status = {'error': 'No backups found'}
    
    return JsonResponse(status)
```

### Monitoring Integration

```python
# For external monitoring systems
def backup_prometheus_metrics():
    """Generate Prometheus metrics for backup monitoring"""
    backup_dir = Path(settings.BASE_DIR) / 'backups'
    backups = list(backup_dir.glob('backup_*.sql.gz'))
    
    metrics = {
        'backup_count': len(backups),
        'backup_size_bytes': sum(b.stat().st_size for b in backups),
        'last_backup_timestamp': max(b.stat().st_mtime for b in backups) if backups else 0
    }
    
    return metrics
```

## Production Deployment

### Environment Setup

```bash
# Production environment variables
DJANGO_DEBUG=False
BACKUP_ENABLED=True
TELEGRAM_BOT_TOKEN=production_token
TELEGRAM_CHANNEL_ID=production_channel
```

### Monitoring Setup

1. **Log aggregation**: Send backup logs to centralized logging
2. **Alerting**: Set up alerts for backup failures
3. **Metrics**: Track backup frequency and file sizes
4. **Health checks**: Regular verification of backup functionality

### Scaling Considerations

- **Large databases**: Consider incremental backups
- **Multiple environments**: Separate bots/channels for staging/production
- **High frequency**: Adjust change detection threshold for busy systems
- **Storage costs**: Monitor Telegram channel storage usage

This backup system provides reliable, automated database protection for the Halal Korea application with intelligent change detection and seamless Telegram integration. 