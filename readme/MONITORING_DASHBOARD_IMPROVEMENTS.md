# Monitoring Dashboard Improvements

This document covers all the improvements made to the Halal Korea admin monitoring dashboard, including Google Analytics integration, enhanced metrics, mobile responsiveness, and new features.

## Table of Contents

1. [Overview](#overview)
2. [New Features](#new-features)
3. [Google Analytics Integration](#google-analytics-integration)
4. [Enhanced Metrics](#enhanced-metrics)
5. [Mobile Responsiveness](#mobile-responsiveness)
6. [Template Changes](#template-changes)
7. [Configuration](#configuration)
8. [Setup Guide](#setup-guide)

---

## Overview

The monitoring dashboard has been enhanced with the following improvements:

| Feature | Description |
|---------|-------------|
| **GA Integration** | Pull real visitor data from Google Analytics 4 |
| **Percentile Metrics** | P50, P95, P99 response time statistics |
| **System Health** | Real-time health checks for DB, cache, errors |
| **Notifications** | Bell icon with unread notification count |
| **Yesterday Comparison** | Compare today's metrics with yesterday |
| **Real Chart Data** | Charts now use actual data instead of hardcoded values |
| **Time Period Selector** | Filter data by 24h, 7 days, or 30 days |
| **Mobile Responsive** | Improved layout for mobile devices |

---

## New Features

### 1. System Health Banner

The overview dashboard now displays a health status banner showing:

- **Database**: Connection status and query time
- **Cache**: Redis/cache backend availability
- **Error Rate**: Current error percentage with thresholds
- **Response Time**: Average response time status
- **Security**: Recent security events count

Health statuses:
- 🟢 **Healthy**: All systems operating normally
- 🟡 **Warning**: Minor issues detected
- 🔴 **Critical**: Immediate attention required

### 2. Notification Badge

A notification bell icon in the header shows unread admin notifications:

- Displays count of unread `AdminNotification` objects
- Links directly to the notification admin list (filtered by unread)
- Only appears when there are unread notifications

### 3. Yesterday Comparison

The overview dashboard shows comparison with yesterday's metrics:

- Total requests (with % change)
- Error count (with % change)
- Average response time (with % change)
- Unique visitors (with % change)

Visual indicators:
- 🟢 Green arrow: Improvement
- 🔴 Red arrow: Degradation
- ⚪ Gray: No change

### 4. Time Period Selector

Performance and Analytics dashboards now include time period selectors:

- **24 hours**: Last 24 hours of data
- **7 days**: Last week (default)
- **30 days**: Last month

### 5. Percentile Statistics

Performance dashboard now shows response time percentiles:

| Metric | Description |
|--------|-------------|
| **P50** | Median response time (50th percentile) |
| **P95** | 95th percentile - most users experience this or better |
| **P99** | 99th percentile - worst case for 99% of requests |

This provides better insight than just average response time.

---

## Google Analytics Integration

### What Data is Available

| Metric | Description |
|--------|-------------|
| **Active Users** | Real-time users on site (last 30 min) |
| **Sessions** | Total sessions in time period |
| **Page Views** | Total page views |
| **Bounce Rate** | Percentage of single-page sessions |
| **Avg Session Duration** | Average time spent on site |
| **New Users** | First-time visitors |
| **Device Breakdown** | Desktop/Mobile/Tablet split |
| **Traffic Sources** | Organic, Direct, Referral, Social |
| **Geographic Data** | Top countries and cities |
| **Top Pages** | Most visited pages |
| **Daily Trends** | Historical data for charts |

### Setup Requirements

1. Google Cloud project with Analytics Data API enabled
2. Service account with JSON key file
3. Service account added to GA4 property as Viewer
4. Environment variables configured

See [GOOGLE_ANALYTICS_INTEGRATION.md](./GOOGLE_ANALYTICS_INTEGRATION.md) for detailed setup instructions.

### Quick Setup

```bash
# 1. Install the required package
pip install google-analytics-data

# 2. Add to .env
GA_PROPERTY_ID=123456789
GA_CREDENTIALS_FILE=/path/to/ga-credentials.json
```

---

## Enhanced Metrics

### Performance Dashboard

**Before:**
- Average response time only
- Hardcoded chart data
- No trend analysis

**After:**
- P50, P95, P99 percentiles
- Real response time trend chart
- Error rate trend chart
- Time period selector
- Color-coded status indicators

### Analytics Dashboard

**Before:**
- Basic request logs analysis
- Language distribution
- Browser/device stats from logs

**After:**
- Full GA4 integration
- Traffic sources breakdown
- Geographic distribution with flags
- Device category with progress bars
- Top pages table
- Daily trend charts
- Setup guide when GA not configured

### Overview Dashboard

**Before:**
- Basic statistics cards
- Recent activity list
- Static metrics

**After:**
- System health banner
- GA stats section (when configured)
- Yesterday comparison metrics
- Notification badge in header
- Improved card layouts

---

## Mobile Responsiveness

### Header Improvements

- Title truncates on small screens
- Subtitle hidden on mobile
- Spacing reduced between elements
- Username hidden on mobile (icon-only)

### Navigation Improvements

- Icons-only on mobile, full text on desktop
- Reduced spacing between nav items
- "Content Ops" → "Content" (shorter)
- Horizontal scroll with hidden scrollbar

### Card Grid Improvements

- 2 columns on mobile (was single column for some)
- Responsive text sizes
- Proper padding on all screen sizes

### Chart Improvements

- Responsive chart containers
- Touch-friendly time period buttons
- Proper aspect ratios on mobile

---

## Template Changes

### `base.html`

```diff
+ Notification badge with unread count
+ Responsive header layout
+ Mobile-friendly navigation (icons on small screens)
+ Improved spacing for mobile
- Fixed "Back to Admin" text (now responsive)
```

### `dashboard.html`

```diff
+ System health banner
+ GA stats section (6 cards)
+ Yesterday comparison metrics
+ Improved grid layouts
- Hardcoded statistics
```

### `performance.html`

```diff
+ Time period selector (24h/7d/30d)
+ P50, P95, P99 percentile cards
+ Real response time chart data
+ Error rate trend chart
+ Color-coded status indicators
- Hardcoded chart data
- Average-only metrics
```

### `analytics.html`

```diff
+ Complete rewrite with GA integration
+ Traffic overview section
+ Daily trends chart
+ Device breakdown with progress bars
+ Traffic sources table
+ Geographic distribution (countries/cities)
+ Top pages table
+ Setup guide when GA not configured
+ Language preferences with flag emojis
- Basic request log analysis only
```

---

## Configuration

### Environment Variables

```env
# Monitoring System
MONITORING_ENABLED=True
MONITORING_SAMPLE_RATE=0.1          # 10% sampling for small sites
MONITORING_SLOW_THRESHOLD_MS=1000   # 1 second threshold
MONITORING_RETENTION_DAYS=7         # 7 days data retention

# Google Analytics (optional)
GA_PROPERTY_ID=123456789
GA_CREDENTIALS_FILE=/path/to/ga-credentials.json
```

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `MONITORING_ENABLED` | `True` | Enable/disable monitoring |
| `MONITORING_SAMPLE_RATE` | `0.1` | Percentage of requests to log (0.1 = 10%) |
| `MONITORING_SLOW_THRESHOLD_MS` | `1000` | Threshold for slow request warnings |
| `MONITORING_RETENTION_DAYS` | `7` | Days to keep monitoring data |
| `GA_PROPERTY_ID` | `''` | GA4 Property ID (numeric) |
| `GA_CREDENTIALS_FILE` | `''` | Path to service account JSON |

---

## Setup Guide

### 1. Update Dependencies

```bash
pip install google-analytics-data>=0.18.0
```

Or update `requirements.txt`:
```
google-analytics-data>=0.18.0
```

### 2. Configure Environment

Add to your `.env` file:

```env
# Required for GA integration
GA_PROPERTY_ID=your-property-id
GA_CREDENTIALS_FILE=/absolute/path/to/credentials.json

# Recommended settings for small sites
MONITORING_SAMPLE_RATE=0.1
MONITORING_RETENTION_DAYS=7
```

### 3. Set Up Google Analytics (Optional)

If you want GA integration, follow the detailed setup in [GOOGLE_ANALYTICS_INTEGRATION.md](./GOOGLE_ANALYTICS_INTEGRATION.md).

### 4. Verify Installation

1. Start Django server: `python manage.py runserver`
2. Go to `/admin/monitoring/`
3. Check that:
   - System health banner appears
   - Cards show real data
   - Charts render with actual data
   - GA section shows data or setup guide

---

## File Structure

```
halal-korea/
├── utils/
│   ├── google_analytics.py          # NEW: GA Data API service
│   ├── admin_views.py               # UPDATED: Enhanced dashboard views
│   ├── models.py                    # Existing monitoring models
│   ├── monitoring_middleware.py     # Existing middleware
│   └── templates/monitoring/
│       ├── base.html                # UPDATED: Notification badge, mobile nav
│       ├── dashboard.html           # UPDATED: Health banner, GA stats
│       ├── performance.html         # UPDATED: Percentiles, real charts
│       ├── analytics.html           # UPDATED: Complete GA integration
│       ├── security.html            # Unchanged
│       ├── content_ops.html         # Unchanged
│       └── logs.html                # Unchanged
├── config/
│   └── settings.py                  # UPDATED: GA config, retention settings
└── readme/
    ├── MONITORING_DASHBOARD_IMPROVEMENTS.md  # This file
    └── GOOGLE_ANALYTICS_INTEGRATION.md       # Detailed GA setup
```

---

## API Reference

### Google Analytics Service

```python
from utils.google_analytics import ga_service

# Check if GA is configured
if ga_service.is_configured:
    # Get overview stats
    stats = ga_service.get_overview_stats(days=7)
    # Returns: {'users': 100, 'sessions': 150, 'pageviews': 500, ...}

    # Get real-time users
    active = ga_service.get_realtime_users()
    # Returns: 5

    # Get top pages
    pages = ga_service.get_top_pages(days=7, limit=10)
    # Returns: [{'path': '/', 'views': 100}, ...]

    # Get device breakdown
    devices = ga_service.get_device_breakdown(days=7)
    # Returns: [{'device': 'mobile', 'users': 60, 'percentage': 60.0}, ...]

    # Get traffic sources
    sources = ga_service.get_traffic_sources(days=7)
    # Returns: [{'source': 'google', 'users': 50, 'sessions': 75}, ...]

    # Get geographic data
    geo = ga_service.get_geographic_data(days=7)
    # Returns: {'countries': [...], 'cities': [...]}

    # Get daily trends
    trends = ga_service.get_daily_trends(days=30)
    # Returns: [{'date': '2024-01-01', 'users': 10, 'sessions': 15}, ...]
```

### Helper Functions in admin_views.py

```python
# Get yesterday's stats for comparison
yesterday_stats = _get_yesterday_stats()
# Returns: {'requests': 100, 'errors': 2, 'avg_response': 150, 'visitors': 50}

# Get system health status
health = _get_system_health()
# Returns: {'status': 'healthy', 'db': 'ok', 'cache': 'ok', ...}

# Get unread notification count
count = _get_unread_notification_count()
# Returns: 3

# Get percentile statistics
percentiles = _get_percentile_stats(days=7)
# Returns: {'p50': 100, 'p95': 500, 'p99': 1200}

# Get error rate trend
errors = _get_error_rate_trend(days=7)
# Returns: [{'date': '2024-01-01', 'rate': 0.5}, ...]

# Get response time trend
times = _get_response_time_trend(days=7)
# Returns: [{'date': '2024-01-01', 'avg': 150}, ...]
```

---

## Troubleshooting

### Dashboard shows no data

1. Check `MONITORING_ENABLED=True` in settings
2. Verify middleware is in `MIDDLEWARE` list
3. Check that some requests have been made to the site
4. Verify database migrations are applied

### GA section shows setup guide

1. Verify `GA_PROPERTY_ID` and `GA_CREDENTIALS_FILE` are set
2. Check credentials file path is absolute
3. Restart Django server after changing `.env`
4. See [GA Integration docs](./GOOGLE_ANALYTICS_INTEGRATION.md) for detailed setup

### Charts not rendering

1. Check browser console for JavaScript errors
2. Verify Chart.js is loading (CDN in base.html)
3. Check that view is passing chart data correctly

### Mobile layout issues

1. Clear browser cache
2. Check viewport meta tag in base.html
3. Test with browser dev tools responsive mode

### Percentiles showing as 0

1. Ensure PostgreSQL is being used (SQLite doesn't support PERCENTILE_CONT)
2. Check that there are logged requests in the database
3. Verify `RequestLog` model has `response_time` data

---

## Performance Considerations

### Sampling Rate

For small sites (< 10,000 daily visitors), 10% sampling (`MONITORING_SAMPLE_RATE=0.1`) provides good data while minimizing database writes.

### Data Retention

7-day retention (`MONITORING_RETENTION_DAYS=7`) is recommended for small sites to keep database size manageable.

### Caching

- GA API responses are cached for 5 minutes
- Dashboard queries are optimized with appropriate indexes
- Consider adding Redis caching for high-traffic dashboards

### Database Indexes

Ensure these indexes exist for optimal performance:

```sql
CREATE INDEX idx_requestlog_timestamp ON utils_requestlog(timestamp);
CREATE INDEX idx_requestlog_status ON utils_requestlog(status_code);
CREATE INDEX idx_securityevent_timestamp ON utils_securityevent(timestamp);
```

---

## Future Improvements

Potential enhancements to consider:

1. **WebSocket real-time updates** - Live dashboard without page refresh
2. **Custom alert thresholds** - UI for configuring AlertRule
3. **Export functionality** - Download reports as CSV/PDF
4. **Comparison periods** - Compare this week vs last week
5. **Custom date ranges** - Date picker for arbitrary ranges
6. **User journey tracking** - Session flow visualization
7. **Error grouping** - Group similar errors together
8. **Performance budgets** - Set and track performance targets
