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