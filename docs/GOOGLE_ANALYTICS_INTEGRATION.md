# Google Analytics Integration for Monitoring Dashboard

This document explains how to set up and use the Google Analytics integration in the Halal Korea monitoring dashboard.

## Overview

The monitoring dashboard can pull real-time and historical data from Google Analytics 4 (GA4) to display:

- **Daily unique visitors** and active users
- **Session metrics** (total sessions, average duration, bounce rate)
- **Page views** and top pages
- **Traffic sources** (organic, direct, referral, social)
- **Device breakdown** (desktop, mobile, tablet)
- **Geographic data** (countries and cities)
- **Daily/weekly trends**

## Prerequisites

1. A Google Analytics 4 property already tracking your site
2. A Google Cloud project with billing enabled
3. Admin access to your GA4 property

## Setup Instructions

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown at the top of the page
3. Click **New Project**
4. Enter a project name (e.g., "Halal Korea Analytics")
5. Click **Create**

### Step 2: Enable the Google Analytics Data API

1. In Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for "**Google Analytics Data API**"
3. Click on it and then click **Enable**

> ⚠️ **Important**: Make sure you enable "Google Analytics Data API" (for GA4), not "Google Analytics API" (for Universal Analytics).

### Step 3: Create a Service Account

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** at the top
3. Select **Service account**
4. Fill in the details:
   - **Service account name**: `halal-korea-analytics` (or any name)
   - **Service account ID**: auto-generated
   - **Description**: "Service account for reading GA4 data"
5. Click **Create and Continue**
6. For **Role**, you can skip this step (click **Continue**)
7. Click **Done**

### Step 4: Download the JSON Key File

1. In the **Credentials** page, find your service account in the list
2. Click on the service account email
3. Go to the **Keys** tab
4. Click **Add Key** → **Create new key**
5. Select **JSON** as the key type
6. Click **Create**
7. The JSON file will automatically download to your computer

> 🔒 **Security**: This file contains sensitive credentials. Never commit it to git!

8. Move the file to your project directory and rename it:
   ```bash
   mv ~/Downloads/your-project-*.json /path/to/halal-korea/ga-credentials.json
   ```

### Step 5: Grant Access to Your GA4 Property

1. Copy the service account email address (looks like `name@project-id.iam.gserviceaccount.com`)
2. Go to [Google Analytics](https://analytics.google.com)
3. Select your property
4. Go to **Admin** (gear icon at bottom left)
5. Under **Property**, click **Property Access Management**
6. Click the **+** button → **Add users**
7. Paste the service account email
8. Select **Viewer** role (minimum required)
9. Uncheck "Notify new users by email" (service accounts can't receive email)
10. Click **Add**

### Step 6: Get Your GA4 Property ID

1. In Google Analytics, go to **Admin**
2. Under **Property**, click **Property Settings**
3. Copy the **Property ID** (a numeric value like `123456789`)

> ⚠️ **Note**: The Property ID is different from the Measurement ID (G-XXXXXXXXXX). You need the numeric Property ID.

### Step 7: Configure Environment Variables

Add the following to your `.env` file:

```env
# Google Analytics Configuration
GA_PROPERTY_ID=123456789
GA_CREDENTIALS_FILE=/absolute/path/to/halal-korea/ga-credentials.json
```

Replace:
- `123456789` with your actual GA4 Property ID
- `/absolute/path/to/...` with the actual path to your credentials file

### Step 8: Install Required Package

The integration requires the `google-analytics-data` package:

```bash
pip install google-analytics-data
```

Or add to `requirements.txt`:
```
google-analytics-data>=0.18.0
```

### Step 9: Verify the Setup

1. Start your Django development server
2. Go to the monitoring dashboard: `/admin/monitoring/`
3. Click on **Analytics** tab
4. If configured correctly, you'll see GA data
5. If not configured, you'll see a setup guide

## Dashboard Features

### Overview Dashboard (`/admin/monitoring/`)

Displays Google Analytics cards showing:
- **Active Users** (last 30 minutes)
- **Sessions** (today)
- **Page Views** (today)
- **Bounce Rate** (today)
- **Avg Session Duration** (today)
- **New Users** (today)

### Analytics Dashboard (`/admin/monitoring/analytics/`)

Comprehensive analytics view with:

#### Traffic Overview
- Total users, sessions, page views
- Bounce rate and engagement metrics
- New vs returning users

#### Traffic Trends Chart
- Line chart showing daily trends
- Configurable time periods (7, 14, 30 days)

#### Device Breakdown
- Visual breakdown of desktop/mobile/tablet usage
- Progress bars with percentages

#### Traffic Sources
- Table showing acquisition channels
- Users and sessions per source

#### Geographic Distribution
- Top countries with flag emojis
- Top cities

#### Top Pages
- Most visited pages
- View counts for each

## Architecture

### Files Structure

```
halal-korea/
├── utils/
│   ├── google_analytics.py      # GA Data API service
│   ├── admin_views.py           # Dashboard views with GA integration
│   └── templates/monitoring/
│       ├── dashboard.html       # Overview with GA stats
│       └── analytics.html       # Full analytics page
├── config/
│   └── settings.py              # GA configuration
└── ga-credentials.json          # Service account key (gitignored)
```

### Google Analytics Service (`utils/google_analytics.py`)

The `GoogleAnalyticsService` class provides methods to fetch data from GA4:

```python
from utils.google_analytics import ga_service

# Get overview stats for the last 7 days
stats = ga_service.get_overview_stats(days=7)

# Get real-time active users
active = ga_service.get_realtime_users()

# Get top pages
pages = ga_service.get_top_pages(days=7, limit=10)

# Get geographic data
geo = ga_service.get_geographic_data(days=7)

# Get device breakdown
devices = ga_service.get_device_breakdown(days=7)

# Get traffic sources
sources = ga_service.get_traffic_sources(days=7)

# Get daily trends
trends = ga_service.get_daily_trends(days=30)
```

### Caching

API responses are cached for 5 minutes to reduce API calls and improve dashboard performance. The cache key is based on the method name and parameters.

## Troubleshooting

### "GA not configured" message

**Cause**: Missing or invalid environment variables.

**Solution**:
1. Check that `GA_PROPERTY_ID` and `GA_CREDENTIALS_FILE` are set in `.env`
2. Verify the credentials file path is absolute and correct
3. Restart the Django server after changing `.env`

### "Permission denied" error

**Cause**: Service account doesn't have access to the GA property.

**Solution**:
1. Verify the service account email is added to GA property
2. Make sure it has at least "Viewer" role
3. Wait a few minutes for permissions to propagate

### "API not enabled" error

**Cause**: Google Analytics Data API is not enabled.

**Solution**:
1. Go to Google Cloud Console → APIs & Services → Library
2. Search for "Google Analytics Data API"
3. Click **Enable**

### "Invalid property ID" error

**Cause**: Using Measurement ID instead of Property ID.

**Solution**:
- Use the numeric Property ID (e.g., `123456789`)
- Not the Measurement ID (e.g., `G-XXXXXXXXXX`)

### No data showing

**Cause**: GA property has no data or wrong date range.

**Solution**:
1. Verify your site is sending data to GA (check Realtime reports in GA)
2. Wait 24-48 hours for new properties to collect data
3. Check that the Property ID matches the property receiving data

## API Quotas and Limits

Google Analytics Data API has the following limits:

| Quota | Limit |
|-------|-------|
| Requests per day | 25,000 |
| Requests per minute per user | 120 |
| Concurrent requests | 10 |

The monitoring dashboard is designed to stay well within these limits with:
- 5-minute caching
- Efficient batch queries
- Reasonable default time ranges

## Security Considerations

1. **Never commit credentials**: The `ga-credentials.json` file is in `.gitignore`
2. **Minimal permissions**: Service account only needs "Viewer" role
3. **Environment variables**: Sensitive values stored in `.env`
4. **Admin-only access**: Dashboard requires admin authentication

## Extending the Integration

### Adding New Metrics

To add new metrics to the dashboard:

1. Add a new method to `GoogleAnalyticsService` in `utils/google_analytics.py`
2. Call the method in the appropriate view in `utils/admin_views.py`
3. Display the data in the relevant template

### Example: Adding Event Tracking

```python
# In google_analytics.py
def get_events(self, days=7, limit=10):
    """Get top events."""
    if not self.client:
        return []
    
    request = RunReportRequest(
        property=f"properties/{self.property_id}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
        limit=limit
    )
    
    response = self.client.run_report(request)
    return [
        {
            'event_name': row.dimension_values[0].value,
            'count': int(row.metric_values[0].value)
        }
        for row in response.rows
    ]
```

## References

- [Google Analytics Data API Documentation](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [GA4 Dimensions & Metrics Explorer](https://ga-dev-tools.google/ga4/dimensions-metrics-explorer/)
- [Python Client Library](https://googleapis.dev/python/analyticsdata/latest/index.html)
- [Google Cloud Console](https://console.cloud.google.com)
