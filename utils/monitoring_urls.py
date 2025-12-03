"""
URL configuration for monitoring dashboard.

All monitoring-related URLs are defined here and included in the main urls.py.
These URLs are prefixed with 'admin/monitoring/' in the main configuration.
"""
from django.urls import path
from utils import admin_views

app_name = 'monitoring'

urlpatterns = [
    # --- Dashboard Views ---
    path('', admin_views.monitoring_dashboard, name='dashboard'),
    path('performance/', admin_views.performance_dashboard, name='performance'),
    path('security/', admin_views.security_dashboard, name='security'),
    path('content/', admin_views.content_operations_dashboard, name='content'),
    path('analytics/', admin_views.analytics_dashboard, name='analytics'),
    path('logs/', admin_views.logs_dashboard, name='logs'),
    
    # --- API Endpoints ---
    path('api/logs/', admin_views.api_logs, name='api_logs'),
    path('api/metrics/', admin_views.api_metrics, name='api_metrics'),
    path('api/stats/', admin_views.api_stats, name='api_stats'),
    path('api/performance/', admin_views.api_performance, name='api_performance'),
    path('api/charts/', admin_views.api_chart_data, name='api_charts'),
    path('api/analytics/', admin_views.api_analytics_data, name='api_analytics'),
]
