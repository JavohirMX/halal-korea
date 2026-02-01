# Halal Korea - Admin Monitoring System

## Overview

The Admin Monitoring System provides comprehensive visibility into application health, performance, security, and content operations. It combines real-time dashboards, automated alerts, and detailed analytics to help administrators maintain and optimize the Halal Korea platform.

## Features

### 📊 Monitoring Dashboards

- **Overview Dashboard**: Real-time KPIs, error tracking, pending content queues
- **Performance Dashboard**: Response times, database queries, cache performance, slow endpoints
- **Security Dashboard**: Failed logins, suspicious activity, admin action audit trail
- **Content Operations**: Moderation queues, moderator activity, quality metrics
- **Analytics Dashboard**: User engagement, content usage, geographic distribution

### 🚨 Alert System

- **Configurable Alert Rules**: Define custom thresholds for various conditions
- **Multiple Alert Channels**: Telegram, Email, In-app notifications
- **Alert Types**:
  - Error rate spikes
  - Slow response times
  - Old pending content
  - Failed login spikes
  - Database slow queries
  - Low cache hit rates
  - External API failures

### 📈 Metrics Collection

- **Request Logging**: Sampled request tracking with performance data
- **System Metrics**: Hourly/daily aggregated metrics
- **Admin Actions**: Complete audit trail of admin operations
- **Content Moderation**: Track approval/rejection workflows
- **Security Events**: Failed logins, rate limits, suspicious activity

### 🔔 Notifications

- **In-app Notifications**: Badge counts and dropdown for admins
- **Telegram Alerts**: Instant notifications for critical issues
- **Email Digests**: Daily summary reports

## Architecture

### Data Flow

```
App Events → Middleware/Signals → Monitoring Models (PostgreSQL)
                                → Sentry (errors/performance)
                                → Telegram (critical alerts)
                                ↓
                        Admin Dashboard (aggregated views)
```

### Key Components

1. **Monitoring Models** (`utils/models.py`)
   - SystemMetric: Aggregated metrics
   - RequestLog: Sampled request tracking
   - AdminAction: Audit trail
   - ContentModerationLog: Moderation workflow
   - SecurityEvent: Security incidents
   - AdminNotification: In-app notifications
   - AlertRule: Configurable alert rules

2. **Monitoring Middleware** (`utils/monitoring_middleware.py`)
   - Request/response timing
   - Error capture
   - Performance metrics collection
   - Sampling logic (1% normal, 100% errors/slow)

3. **Signal Handlers** (`utils/monitoring_signals.py`)
   - Content moderation tracking
   - Security event logging
   - User authentication monitoring

4. **Alert Manager** (`utils/monitoring_alerts.py`)
   - Rule evaluation engine
   - Multi-channel notification system
   - Cooldown management

5. **Dashboard Views** (`utils/admin_views.py`)
   - Staff-only access
   - Real-time data aggregation
   - API endpoints for charts

## Installation & Setup

### 1. Database Migrations

The monitoring models are already migrated. If you need to re-run:

```bash
python manage.py migrate utils
```

### 2. Configuration

Add to your `.env` file:

```env
# Monitoring Configuration
MONITORING_ENABLED=True
MONITORING_SAMPLE_RATE=0.01  # 1% sampling for normal requests
MONITORING_SLOW_THRESHOLD_MS=1000  # 1 second
MONITORING_RETENTION_DAYS=30

# Sentry (Optional)
SENTRY_DSN=your-sentry-dsn-here
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# Alert Configuration
ALERT_TELEGRAM_ENABLED=True
ALERT_EMAIL_ENABLED=True
ALERT_EMAIL_RECIPIENTS=admin@example.com,ops@example.com
```

### 3. Sentry Setup (Optional)

If using Sentry for error tracking:

1. Create account at [sentry.io](https://sentry.io)
2. Create new Django project
3. Copy DSN to `.env` file
4. Sentry will automatically capture errors in production (when DEBUG=False)

### 4. Cron Jobs Setup

Add these cron jobs for automated monitoring:

```bash
# Check alerts every 5 minutes
*/5 * * * * cd /path/to/halal-korea && source .venv/bin/activate && python manage.py check_alerts

# Aggregate metrics hourly
0 * * * * cd /path/to/halal-korea && source .venv/bin/activate && python manage.py aggregate_metrics --cleanup

# Send daily digest at 8 AM
0 8 * * * cd /path/to/halal-korea && source .venv/bin/activate && python manage.py send_daily_digest

# Check monitoring health daily at 9 AM
0 9 * * * cd /path/to/halal-korea && source .venv/bin/activate && python manage.py check_monitoring_health --alert
```

## Usage

### Accessing Dashboards

1. Log in to Django admin as staff user
2. Navigate to `/admin/monitoring/` or use the navigation menu
3. Explore different dashboard sections:
   - Overview: `/admin/monitoring/`
   - Performance: `/admin/monitoring/performance/`
   - Security: `/admin/monitoring/security/`
   - Content Ops: `/admin/monitoring/content/`
   - Analytics: `/admin/monitoring/analytics/`

### Creating Alert Rules

1. Go to Django admin → Alert Rules
2. Click "Add Alert Rule"
3. Configure:
   - **Name**: Descriptive name for the alert
   - **Condition**: Choose from available conditions
   - **Threshold**: Numeric threshold value
   - **Window**: Time window in minutes to evaluate
   - **Alert Channels**: Select telegram, email, and/or in_app
   - **Cooldown**: Minimum minutes between alerts

Example alert rules:

```python
# High Error Rate Alert
Name: "High Error Rate"
Condition: "Error Rate Above Threshold"
Threshold: 5.0  # 5% error rate
Window: 10  # minutes
Channels: ["telegram", "in_app"]
Cooldown: 60  # 1 hour

# Slow Response Time Alert
Name: "Slow Response Times"
Condition: "Response Time Above Threshold"
Threshold: 2000  # 2 seconds
Window: 15  # minutes
Channels: ["email", "in_app"]
Cooldown: 120  # 2 hours

# Old Pending Content Alert
Name: "Old Pending Content"
Condition: "Queue Age Above Threshold"
Threshold: 48  # hours
Window: 60  # minutes
Channels: ["telegram", "email"]
Cooldown: 1440  # 24 hours
```

### Viewing Monitoring Data

#### Request Logs
- Admin → Request Logs
- Filter by status code, date, user
- Export to CSV for analysis

#### Security Events
- Admin → Security Events
- Mark events as resolved
- Filter by event type and severity

#### Admin Actions
- Admin → Admin Actions
- Complete audit trail
- Cannot be deleted (compliance)

### Managing Notifications

#### In-app Notifications
- Bell icon in admin header (when implemented)
- Mark as read or dismiss
- Links to relevant admin pages

#### Telegram Alerts
- Configured via `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- Instant notifications for critical issues
- Includes severity emoji and context

#### Email Alerts
- Daily digest at configured time
- Critical alerts sent immediately
- Configured via `ALERT_EMAIL_RECIPIENTS`

## Management Commands

### aggregate_metrics

Aggregate request logs into system metrics:

```bash
# Aggregate last hour (default)
python manage.py aggregate_metrics

# Aggregate last 24 hours
python manage.py aggregate_metrics --hours 24

# Aggregate and cleanup old logs
python manage.py aggregate_metrics --cleanup
```

### check_alerts

Check all enabled alert rules:

```bash
# Check alerts (quiet mode)
python manage.py check_alerts

# Check alerts with verbose output
python manage.py check_alerts --verbose
```

### check_monitoring_health

Verify monitoring system health:

```bash
# Check health without alerts
python manage.py check_monitoring_health

# Check health and send alerts if issues found
python manage.py check_monitoring_health --alert
```

### send_daily_digest

Send daily monitoring digest email:

```bash
python manage.py send_daily_digest
```

## API Endpoints

### Metrics API

Get time series metrics data:

```
GET /admin/monitoring/api/metrics/?type=request_count&hours=24
```

Parameters:
- `type`: Metric type (request_count, error_count, avg_response_time, etc.)
- `hours`: Time window in hours

### Stats API

Get aggregate statistics:

```
GET /admin/monitoring/api/stats/?period=today
```

Parameters:
- `period`: today, week, or month

### Performance API

Get performance data:

```
GET /admin/monitoring/api/performance/?days=7
```

Parameters:
- `days`: Number of days to analyze

## Privacy & Security

### IP Hashing

All IP addresses are hashed using SHA-256 with application secret key:

```python
def hash_ip(ip_address):
    salt = settings.SECRET_KEY[:16]
    return hashlib.sha256(f"{salt}{ip_address}".encode()).hexdigest()[:16]
```

### Data Retention

- **RequestLog**: 30 days raw data, then aggregated
- **SecurityEvent**: 90 days, then archived
- **AdminAction**: Permanent (audit requirement)
- **SystemMetric**: Permanent (aggregated)

### Access Control

- All monitoring views require `is_staff=True`
- Security dashboard requires `is_superuser=True` (planned)
- Audit logs cannot be deleted

## Performance Considerations

### Sampling

- Normal requests: 1% sampling rate (configurable)
- Error requests: 100% logging
- Slow requests (>1s): 100% logging

This prevents overwhelming the database while capturing all important events.

### Database Indexes

Key indexes for performance:
- `RequestLog`: timestamp, status_code, response_time_ms
- `SystemMetric`: timestamp + metric_type + metric_name
- `SecurityEvent`: timestamp + event_type + severity
- `AdminAction`: timestamp + admin_user + action_type

### Aggregation

Hourly aggregation reduces database size:
- Raw logs: ~1000 rows/hour → 20-50 metric rows/hour
- 30-day retention: ~720K raw logs → ~36K metrics

## Troubleshooting

### No Metrics Being Recorded

1. Check `MONITORING_ENABLED` setting
2. Verify middleware is installed in `MIDDLEWARE` setting
3. Check logs for errors: `tail -f logs/django.log`
4. Test manually: Make requests and check `/admin/utils/requestlog/`

### Alerts Not Triggering

1. Verify alert rules are enabled
2. Check cooldown period hasn't been exceeded
3. Run manually: `python manage.py check_alerts --verbose`
4. Check alert channel configuration (Telegram, Email)

### Dashboard Not Loading

1. Verify user has staff permission
2. Check for template errors in logs
3. Ensure all migrations are applied
4. Clear browser cache

### High Database Load

1. Reduce `MONITORING_SAMPLE_RATE` (e.g., 0.005 for 0.5%)
2. Increase `MONITORING_SLOW_THRESHOLD_MS`
3. Run cleanup more frequently: `aggregate_metrics --cleanup`
4. Consider archiving old data

## Best Practices

1. **Start with Conservative Thresholds**: Set alert thresholds high initially, then tune based on actual patterns
2. **Use Cooldown Periods**: Prevent alert fatigue with appropriate cooldown times
3. **Regular Review**: Review dashboards weekly to identify trends
4. **Clean Up Old Data**: Run aggregation with cleanup regularly
5. **Test Alerts**: Manually trigger alerts to verify notification channels
6. **Monitor the Monitoring**: Use `check_monitoring_health` to ensure system is working
7. **Document Incidents**: Use admin notes in SecurityEvent resolution
8. **Tune Sampling**: Adjust sample rate based on traffic volume

## Future Enhancements

Planned features for future releases:

- **Advanced Analytics**: Cohort analysis, funnel visualization
- **Anomaly Detection**: ML-based alerting for unusual patterns
- **Distributed Tracing**: Full request tracing across services
- **Real-time Dashboard**: WebSocket updates instead of polling
- **Mobile App**: Admin mobile app for monitoring on-the-go
- **Integration**: Slack, Discord, PagerDuty integrations
- **Capacity Planning**: Predictive analytics for scaling
- **Cost Tracking**: Monitor external API costs

## Support

For issues or questions:

1. Check logs: `logs/django.log`, `logs/django_errors.log`
2. Review this documentation
3. Check Django admin for configuration
4. Contact development team

## License

Part of the Halal Korea project. See main LICENSE file.

