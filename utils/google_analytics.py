"""
Google Analytics Data API integration for monitoring dashboard.

To use this, you need:
1. Create a service account in Google Cloud Console
2. Add the service account email to your GA4 property (Admin > Property Access Management)
3. Download the JSON credentials file
4. Set GA_PROPERTY_ID and GA_CREDENTIALS_FILE in your environment

Install: pip install google-analytics-data
"""
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Try to import Google Analytics library
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric, OrderBy
    )
    from google.oauth2 import service_account
    GA_AVAILABLE = True
except ImportError:
    GA_AVAILABLE = False
    logger.info("Google Analytics Data API not installed. Run: pip install google-analytics-data")


class GoogleAnalyticsService:
    """Service for fetching Google Analytics 4 data."""
    
    CACHE_TTL = 300  # Cache for 5 minutes
    
    def __init__(self):
        self.client = None
        self.property_id = getattr(settings, 'GA_PROPERTY_ID', '')
        self.credentials_file = getattr(settings, 'GA_CREDENTIALS_FILE', '')
        
        if GA_AVAILABLE and self.property_id and self.credentials_file:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=['https://www.googleapis.com/auth/analytics.readonly']
                )
                self.client = BetaAnalyticsDataClient(credentials=credentials)
                logger.info("Google Analytics client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GA client: {e}")
    
    @property
    def is_available(self):
        """Check if GA integration is properly configured."""
        return self.client is not None
    
    def _run_report(self, date_ranges, dimensions, metrics, order_bys=None, limit=10):
        """Run a GA4 report with caching."""
        if not self.is_available:
            return None
        
        # Create cache key
        cache_key = f"ga_report_{hash(str(date_ranges) + str(dimensions) + str(metrics))}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=date_ranges,
                dimensions=dimensions,
                metrics=metrics,
                order_bys=order_bys or [],
                limit=limit
            )
            response = self.client.run_report(request)
            
            # Cache the response
            cache.set(cache_key, response, self.CACHE_TTL)
            return response
        except Exception as e:
            logger.error(f"GA API error: {e}")
            return None
    
    def get_overview_stats(self, days=7):
        """Get overview statistics for the dashboard."""
        cache_key = f"ga_overview_{days}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if not self.is_available:
            return self._get_fallback_stats()
        
        try:
            # Today's stats
            today_response = self._run_report(
                date_ranges=[DateRange(start_date="today", end_date="today")],
                dimensions=[],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="sessions"),
                    Metric(name="screenPageViews"),
                    Metric(name="bounceRate"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="newUsers"),
                ]
            )
            
            # Yesterday's stats for comparison
            yesterday_response = self._run_report(
                date_ranges=[DateRange(start_date="yesterday", end_date="yesterday")],
                dimensions=[],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="sessions"),
                    Metric(name="screenPageViews"),
                ]
            )
            
            today_data = self._extract_metrics(today_response)
            yesterday_data = self._extract_metrics(yesterday_response)
            
            stats = {
                'active_users': int(today_data.get('activeUsers', 0)),
                'sessions': int(today_data.get('sessions', 0)),
                'page_views': int(today_data.get('screenPageViews', 0)),
                'bounce_rate': float(today_data.get('bounceRate', 0)) * 100,
                'avg_session_duration': float(today_data.get('averageSessionDuration', 0)),
                'new_users': int(today_data.get('newUsers', 0)),
                # Comparisons with yesterday
                'users_change': self._calc_change(
                    today_data.get('activeUsers', 0),
                    yesterday_data.get('activeUsers', 0)
                ),
                'sessions_change': self._calc_change(
                    today_data.get('sessions', 0),
                    yesterday_data.get('sessions', 0)
                ),
                'page_views_change': self._calc_change(
                    today_data.get('screenPageViews', 0),
                    yesterday_data.get('screenPageViews', 0)
                ),
                'is_available': True,
            }
            
            cache.set(cache_key, stats, self.CACHE_TTL)
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching GA overview: {e}")
            return self._get_fallback_stats()
    
    def get_realtime_users(self):
        """Get current active users (approximation using last 30 minutes)."""
        # Note: Real-time data requires different API, this is an approximation
        if not self.is_available:
            return {'count': 0, 'is_available': False}
        
        try:
            response = self._run_report(
                date_ranges=[DateRange(start_date="today", end_date="today")],
                dimensions=[],
                metrics=[Metric(name="active1DayUsers")]
            )
            data = self._extract_metrics(response)
            return {
                'count': int(data.get('active1DayUsers', 0)),
                'is_available': True
            }
        except Exception as e:
            logger.error(f"Error fetching realtime users: {e}")
            return {'count': 0, 'is_available': False}
    
    def get_top_pages(self, days=7, limit=10):
        """Get top pages by page views."""
        if not self.is_available:
            return []
        
        try:
            response = self._run_report(
                date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                dimensions=[Dimension(name="pagePath")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="averageSessionDuration"),
                ],
                order_bys=[OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
                    desc=True
                )],
                limit=limit
            )
            
            pages = []
            if response and response.rows:
                for row in response.rows:
                    pages.append({
                        'path': row.dimension_values[0].value,
                        'views': int(row.metric_values[0].value),
                        'avg_time': float(row.metric_values[1].value),
                    })
            return pages
            
        except Exception as e:
            logger.error(f"Error fetching top pages: {e}")
            return []
    
    def get_geographic_data(self, days=7, limit=10):
        """Get user distribution by country/city."""
        if not self.is_available:
            return {'countries': [], 'cities': []}
        
        try:
            # By country
            country_response = self._run_report(
                date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                dimensions=[Dimension(name="country")],
                metrics=[Metric(name="activeUsers")],
                order_bys=[OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="activeUsers"),
                    desc=True
                )],
                limit=limit
            )
            
            # By city
            city_response = self._run_report(
                date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                dimensions=[Dimension(name="city")],
                metrics=[Metric(name="activeUsers")],
                order_bys=[OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="activeUsers"),
                    desc=True
                )],
                limit=limit
            )
            
            countries = []
            if country_response and country_response.rows:
                for row in country_response.rows:
                    countries.append({
                        'name': row.dimension_values[0].value,
                        'users': int(row.metric_values[0].value),
                    })
            
            cities = []
            if city_response and city_response.rows:
                for row in city_response.rows:
                    cities.append({
                        'name': row.dimension_values[0].value,
                        'users': int(row.metric_values[0].value),
                    })
            
            return {'countries': countries, 'cities': cities}
            
        except Exception as e:
            logger.error(f"Error fetching geographic data: {e}")
            return {'countries': [], 'cities': []}
    
    def get_device_breakdown(self, days=7):
        """Get device category breakdown."""
        if not self.is_available:
            return []
        
        try:
            response = self._run_report(
                date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                dimensions=[Dimension(name="deviceCategory")],
                metrics=[Metric(name="activeUsers")],
                order_bys=[OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="activeUsers"),
                    desc=True
                )]
            )
            
            devices = []
            if response and response.rows:
                total = sum(int(row.metric_values[0].value) for row in response.rows)
                for row in response.rows:
                    count = int(row.metric_values[0].value)
                    devices.append({
                        'device': row.dimension_values[0].value.title(),
                        'users': count,
                        'percentage': round(count / total * 100, 1) if total > 0 else 0,
                    })
            return devices
            
        except Exception as e:
            logger.error(f"Error fetching device breakdown: {e}")
            return []
    
    def get_traffic_sources(self, days=7, limit=10):
        """Get traffic sources breakdown."""
        if not self.is_available:
            return []
        
        try:
            response = self._run_report(
                date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                dimensions=[Dimension(name="sessionDefaultChannelGroup")],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="activeUsers"),
                ],
                order_bys=[OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                    desc=True
                )],
                limit=limit
            )
            
            sources = []
            if response and response.rows:
                for row in response.rows:
                    sources.append({
                        'source': row.dimension_values[0].value,
                        'sessions': int(row.metric_values[0].value),
                        'users': int(row.metric_values[1].value),
                    })
            return sources
            
        except Exception as e:
            logger.error(f"Error fetching traffic sources: {e}")
            return []
    
    def get_daily_trends(self, days=7):
        """Get daily active users and sessions trend."""
        if not self.is_available:
            return {'labels': [], 'users': [], 'sessions': [], 'page_views': []}
        
        try:
            response = self._run_report(
                date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                dimensions=[Dimension(name="date")],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="sessions"),
                    Metric(name="screenPageViews"),
                ],
                order_bys=[OrderBy(
                    dimension=OrderBy.DimensionOrderBy(dimension_name="date"),
                    desc=False
                )],
                limit=days + 1
            )
            
            trends = {'labels': [], 'users': [], 'sessions': [], 'page_views': []}
            if response and response.rows:
                for row in response.rows:
                    date_str = row.dimension_values[0].value
                    # Format date (YYYYMMDD -> MM/DD)
                    formatted_date = f"{date_str[4:6]}/{date_str[6:8]}"
                    trends['labels'].append(formatted_date)
                    trends['users'].append(int(row.metric_values[0].value))
                    trends['sessions'].append(int(row.metric_values[1].value))
                    trends['page_views'].append(int(row.metric_values[2].value))
            
            return trends
            
        except Exception as e:
            logger.error(f"Error fetching daily trends: {e}")
            return {'labels': [], 'users': [], 'sessions': [], 'page_views': []}
    
    def _extract_metrics(self, response):
        """Extract metrics from a GA response."""
        if not response or not response.rows:
            return {}
        
        result = {}
        row = response.rows[0]
        for i, header in enumerate(response.metric_headers):
            result[header.name] = row.metric_values[i].value
        return result
    
    def _calc_change(self, current, previous):
        """Calculate percentage change."""
        try:
            current = float(current)
            previous = float(previous)
            if previous == 0:
                return 100 if current > 0 else 0
            return round((current - previous) / previous * 100, 1)
        except (ValueError, TypeError):
            return 0
    
    def _get_fallback_stats(self):
        """Return fallback stats when GA is not available."""
        return {
            'active_users': 0,
            'sessions': 0,
            'page_views': 0,
            'bounce_rate': 0,
            'avg_session_duration': 0,
            'new_users': 0,
            'users_change': 0,
            'sessions_change': 0,
            'page_views_change': 0,
            'is_available': False,
        }


# Singleton instance
ga_service = GoogleAnalyticsService()
