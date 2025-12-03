"""
Admin dashboard views for monitoring system.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum, Max, Min
from django.db.models.functions import TruncHour, TruncDate
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from utils.models import (
    RequestLog, SystemMetric, AdminAction, ContentModerationLog,
    SecurityEvent, AdminNotification
)
from utils.google_analytics import ga_service
from places.models import HalalPlace, PlaceEditSuggestion, PlaceImageSuggestion
from reviews.models import Review
from blog.models import BlogPost
from contact.models import ContactMessage
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@staff_member_required
def monitoring_dashboard(request):
    """Main monitoring dashboard with overview of key metrics."""
    context = {
        'title': 'Monitoring Dashboard',
        'today_stats': _get_today_stats(),
        'yesterday_stats': _get_yesterday_stats(),
        'recent_errors': _get_recent_errors(),
        'recent_security_events': _get_recent_security_events(),
        'pending_content': _get_pending_content(),
        'active_users': _get_active_users(),
        'system_health': _get_system_health(),
        'unread_notifications': _get_unread_notification_count(request.user),
        'ga_stats': ga_service.get_overview_stats(),
    }
    return render(request, 'monitoring/dashboard.html', context)


@staff_member_required
def performance_dashboard(request):
    """Performance monitoring dashboard."""
    days = int(request.GET.get('days', 7))
    
    context = {
        'title': 'Performance Dashboard',
        'days': days,
        'slow_endpoints': _get_slow_endpoints(days),
        'response_time_stats': _get_response_time_stats(days),
        'percentile_stats': _get_percentile_stats(days),
        'db_query_stats': _get_db_query_stats(days),
        'cache_stats': _get_cache_stats(days),
        'error_rate_trend': _get_error_rate_trend(days),
        'response_time_trend': _get_response_time_trend(days),
    }
    return render(request, 'monitoring/performance.html', context)


@staff_member_required
def security_dashboard(request):
    """Security monitoring dashboard."""
    context = {
        'title': 'Security Dashboard',
        'failed_logins': _get_failed_logins(),
        'rate_limit_hits': _get_rate_limit_hits(),
        'suspicious_activity': _get_suspicious_activity(),
        'recent_admin_actions': _get_recent_admin_actions(),
    }
    return render(request, 'monitoring/security.html', context)


@staff_member_required
def content_operations_dashboard(request):
    """Content moderation dashboard."""
    context = {
        'title': 'Content Operations',
        'pending_queues': _get_pending_queues(),
        'moderator_activity': _get_moderator_activity(),
        'submission_trends': _get_submission_trends(),
        'quality_metrics': _get_quality_metrics(),
    }
    return render(request, 'monitoring/content_ops.html', context)


@staff_member_required
def analytics_dashboard(request):
    """Product analytics dashboard with lazy loading."""
    days = int(request.GET.get('days', 30))
    
    # Only pass minimal context - data loads via AJAX
    context = {
        'title': 'Analytics Dashboard',
        'days': days,
        'ga_configured': bool(ga_service.is_available),
    }
    return render(request, 'monitoring/analytics.html', context)


@staff_member_required
def logs_dashboard(request):
    """Logs viewer dashboard."""
    log_type = request.GET.get('log_type', 'django')
    lines = int(request.GET.get('lines', 100))
    search = request.GET.get('search', '')
    level = request.GET.get('level', '')  # Log level filter
    
    # Get log files from settings
    logs_dir = settings.BASE_DIR / 'logs'
    
    # Available log files
    log_files = {
        'django': logs_dir / 'django.log',
        'error': logs_dir / 'django_errors.log',
        'security': logs_dir / 'security.log',
        'api': logs_dir / 'api.log',
        'database': logs_dir / 'database.log',
    }
    
    log_content = []
    log_size = 0
    log_exists = False
    log_stats = {'debug': 0, 'info': 0, 'warning': 0, 'error': 0, 'critical': 0}
    
    if log_type in log_files:
        log_path = log_files[log_type]
        if log_path.exists():
            log_exists = True
            log_size = log_path.stat().st_size
            
            try:
                # Read the last N lines
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    
                    # Get last N lines for display
                    last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    
                    # Calculate log level statistics from visible lines
                    for line in last_lines:
                        line_upper = line.upper()
                        if 'CRITICAL' in line_upper:
                            log_stats['critical'] += 1
                        elif 'ERROR' in line_upper:
                            log_stats['error'] += 1
                        elif 'WARNING' in line_upper:
                            log_stats['warning'] += 1
                        elif 'INFO' in line_upper:
                            log_stats['info'] += 1
                        elif 'DEBUG' in line_upper:
                            log_stats['debug'] += 1
                    
                    # Filter by log level if provided
                    if level:
                        last_lines = [line for line in last_lines if level.upper() in line.upper()]
                    
                    # Filter by search term if provided
                    if search:
                        last_lines = [line for line in last_lines if search.lower() in line.lower()]
                    
                    log_content = last_lines
            except Exception as e:
                log_content = [f"Error reading log file: {str(e)}"]
    
    # Calculate log file sizes for all logs
    log_file_info = {}
    for name, path in log_files.items():
        if path.exists():
            size_bytes = path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            log_file_info[name] = {
                'path': str(path),
                'size_bytes': size_bytes,
                'size_mb': round(size_mb, 2),
                'exists': True
            }
        else:
            log_file_info[name] = {
                'path': str(path),
                'size_bytes': 0,
                'size_mb': 0,
                'exists': False
            }
    
    context = {
        'title': 'System Logs',
        'log_type': log_type,
        'log_content': log_content,
        'log_size': log_size,
        'log_size_mb': round(log_size / (1024 * 1024), 2) if log_size > 0 else 0,
        'log_exists': log_exists,
        'lines': lines,
        'search': search,
        'level': level,
        'log_file_info': log_file_info,
        'available_logs': list(log_files.keys()),
        'log_stats': log_stats,
    }
    return render(request, 'monitoring/logs.html', context)


@staff_member_required
def api_logs(request):
    """API endpoint for fetching log content via AJAX."""
    log_type = request.GET.get('log_type', 'django')
    lines = int(request.GET.get('lines', 100))
    search = request.GET.get('search', '')
    level = request.GET.get('level', '')
    
    logs_dir = settings.BASE_DIR / 'logs'
    
    log_files = {
        'django': logs_dir / 'django.log',
        'error': logs_dir / 'django_errors.log',
        'security': logs_dir / 'security.log',
        'api': logs_dir / 'api.log',
        'database': logs_dir / 'database.log',
    }
    
    result = {
        'success': False,
        'log_content': [],
        'log_exists': False,
        'log_size': 0,
        'log_size_mb': 0,
        'line_count': 0,
        'log_stats': {'debug': 0, 'info': 0, 'warning': 0, 'error': 0, 'critical': 0},
        'log_file_info': {},
    }
    
    if log_type not in log_files:
        return JsonResponse(result)
    
    log_path = log_files[log_type]
    
    if log_path.exists():
        result['log_exists'] = True
        result['log_size'] = log_path.stat().st_size
        result['log_size_mb'] = round(result['log_size'] / (1024 * 1024), 2)
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                # Calculate stats
                for line in last_lines:
                    line_upper = line.upper()
                    if 'CRITICAL' in line_upper:
                        result['log_stats']['critical'] += 1
                    elif 'ERROR' in line_upper:
                        result['log_stats']['error'] += 1
                    elif 'WARNING' in line_upper:
                        result['log_stats']['warning'] += 1
                    elif 'INFO' in line_upper:
                        result['log_stats']['info'] += 1
                    elif 'DEBUG' in line_upper:
                        result['log_stats']['debug'] += 1
                
                # Filter by level
                if level:
                    last_lines = [line for line in last_lines if level.upper() in line.upper()]
                
                # Filter by search
                if search:
                    last_lines = [line for line in last_lines if search.lower() in line.lower()]
                
                result['log_content'] = [line.rstrip('\n') for line in last_lines]
                result['line_count'] = len(result['log_content'])
                result['success'] = True
        except Exception as e:
            result['log_content'] = [f"Error reading log file: {str(e)}"]
    
    # Get file info for all logs
    for name, path in log_files.items():
        if path.exists():
            size_bytes = path.stat().st_size
            result['log_file_info'][name] = {
                'size_bytes': size_bytes,
                'size_mb': round(size_bytes / (1024 * 1024), 2),
                'exists': True
            }
        else:
            result['log_file_info'][name] = {'size_bytes': 0, 'size_mb': 0, 'exists': False}
    
    return JsonResponse(result)


# ============================================================================
# API Endpoints for Real-time Data
# ============================================================================

@staff_member_required
def api_metrics(request):
    """API endpoint for time series metrics data."""
    metric_type = request.GET.get('type', 'request_count')
    hours = int(request.GET.get('hours', 24))
    
    end_time = timezone.now()
    start_time = end_time - timezone.timedelta(hours=hours)
    
    metrics = SystemMetric.objects.filter(
        metric_type=metric_type,
        timestamp__gte=start_time
    ).order_by('timestamp').values('timestamp', 'metric_name', 'value')
    
    # Format for Chart.js
    data = {
        'labels': [],
        'datasets': {}
    }
    
    for metric in metrics:
        timestamp = metric['timestamp'].strftime('%Y-%m-%d %H:%M')
        if timestamp not in data['labels']:
            data['labels'].append(timestamp)
        
        metric_name = metric['metric_name']
        if metric_name not in data['datasets']:
            data['datasets'][metric_name] = []
        data['datasets'][metric_name].append(metric['value'])
    
    return JsonResponse(data)


@staff_member_required
def api_stats(request):
    """API endpoint for aggregate statistics."""
    period = request.GET.get('period', 'today')
    
    if period == 'today':
        start_time = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_time = timezone.now() - timezone.timedelta(days=7)
    else:  # month
        start_time = timezone.now() - timezone.timedelta(days=30)
    
    stats = {
        'requests': RequestLog.objects.filter(timestamp__gte=start_time).count(),
        'errors': RequestLog.objects.filter(
            timestamp__gte=start_time,
            status_code__gte=500
        ).count(),
        'avg_response_time': RequestLog.objects.filter(
            timestamp__gte=start_time
        ).aggregate(avg=Avg('response_time_ms'))['avg'] or 0,
        'active_users': User.objects.filter(
            last_login__gte=start_time
        ).count(),
    }
    
    return JsonResponse(stats)


@staff_member_required
def api_performance(request):
    """API endpoint for performance data."""
    days = int(request.GET.get('days', 7))
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    # Get slowest endpoints
    slow_endpoints = RequestLog.objects.filter(
        timestamp__gte=start_time
    ).values('path').annotate(
        avg_time=Avg('response_time_ms'),
        count=Count('id'),
        error_count=Count('id', filter=Q(status_code__gte=400))
    ).order_by('-avg_time')[:10]
    
    data = {
        'endpoints': list(slow_endpoints)
    }
    
    return JsonResponse(data)


@staff_member_required
def api_analytics_data(request):
    """API endpoint for analytics data (lazy loading)."""
    days = int(request.GET.get('days', 30))
    
    # Get all GA data (cached)
    ga_data = ga_service.get_all_analytics_data(days)
    
    # Get local analytics (cached)
    user_engagement = _get_user_engagement(days)
    content_usage = _get_content_usage(days)
    language_preferences = _get_language_preferences()
    
    return JsonResponse({
        'ga_available': ga_data.get('is_available', False),
        'ga_stats': ga_data.get('overview', {}),
        'ga_devices': ga_data.get('devices', []),
        'ga_sources': ga_data.get('sources', []),
        'ga_trends': ga_data.get('trends', {}),
        'ga_top_pages': ga_data.get('top_pages', []),
        'geographic_distribution': ga_data.get('geo', {'countries': [], 'cities': []}),
        'user_engagement': user_engagement,
        'content_usage': content_usage,
        'language_preferences': language_preferences,
    })


@staff_member_required
def api_chart_data(request):
    """API endpoint for real-time chart data (last 24h)."""
    now = timezone.now()
    last_24h = now - timezone.timedelta(hours=24)
    
    # Requests & Errors per hour
    hourly_stats = RequestLog.objects.filter(
        timestamp__gte=last_24h
    ).annotate(
        hour=TruncHour('timestamp')
    ).values('hour').annotate(
        count=Count('id'),
        errors=Count('id', filter=Q(status_code__gte=500))
    ).order_by('hour')
    
    # Error distribution
    error_dist = RequestLog.objects.filter(
        timestamp__gte=last_24h,
        status_code__gte=400
    ).values('status_code').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Format for Chart.js
    labels = []
    requests_data = []
    errors_data = []
    
    for stat in hourly_stats:
        labels.append(stat['hour'].strftime('%H:%M'))
        requests_data.append(stat['count'])
        errors_data.append(stat['errors'])
        
    return JsonResponse({
        'traffic': {
            'labels': labels,
            'requests': requests_data,
            'errors': errors_data
        },
        'errors': {
            'labels': [str(e['status_code']) for e in error_dist],
            'data': [e['count'] for e in error_dist]
        }
    })


# ============================================================================
# Helper Functions for Dashboard Data
# ============================================================================

def _get_today_stats():
    """Get today's key statistics."""
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_requests = RequestLog.objects.filter(timestamp__gte=today_start).count()
    error_count = RequestLog.objects.filter(
        timestamp__gte=today_start,
        status_code__gte=500
    ).count()
    
    avg_response = RequestLog.objects.filter(
        timestamp__gte=today_start
    ).aggregate(avg=Avg('response_time_ms'))
    
    active_users_count = User.objects.filter(
        last_login__gte=today_start
    ).count()
    
    new_users = User.objects.filter(
        created_at__gte=today_start
    ).count()
    
    return {
        'total_requests': total_requests,
        'error_count': error_count,
        'error_rate': (error_count / total_requests * 100) if total_requests > 0 else 0,
        'avg_response_time': avg_response['avg'] or 0,
        'active_users': active_users_count,
        'new_users': new_users,
    }


def _get_recent_errors():
    """Get recent error logs."""
    return RequestLog.objects.filter(
        status_code__gte=500
    ).order_by('-timestamp')[:10]


def _get_recent_security_events():
    """Get recent security events."""
    return SecurityEvent.objects.filter(
        resolved=False
    ).order_by('-timestamp')[:10]


def _get_pending_content():
    """Get counts of pending content for moderation."""
    return {
        'places': HalalPlace.objects.filter(status='pending').count(),
        'reviews': Review.objects.count(),  # If you add status field
        'suggestions': PlaceEditSuggestion.objects.filter(status='pending').count(),
        'image_suggestions': PlaceImageSuggestion.objects.filter(status='pending').count(),
        'contact_messages': ContactMessage.objects.filter(is_read=False).count(),
        'blog_posts': BlogPost.objects.filter(status='draft').count(),
    }


def _get_active_users():
    """Get active users in the last hour."""
    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
    return User.objects.filter(
        last_login__gte=one_hour_ago
    ).count()


def _get_slow_endpoints(days):
    """Get slowest endpoints."""
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    return RequestLog.objects.filter(
        timestamp__gte=start_time
    ).values('path').annotate(
        avg_time=Avg('response_time_ms'),
        max_time=Max('response_time_ms'),
        count=Count('id')
    ).order_by('-avg_time')[:20]


def _get_response_time_stats(days):
    """Get response time statistics."""
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    return RequestLog.objects.filter(
        timestamp__gte=start_time
    ).aggregate(
        avg=Avg('response_time_ms'),
        max=Max('response_time_ms'),
        min=Min('response_time_ms')
    )


def _get_db_query_stats(days):
    """Get database query statistics."""
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    return RequestLog.objects.filter(
        timestamp__gte=start_time
    ).aggregate(
        avg_queries=Avg('db_query_count'),
        max_queries=Max('db_query_count')
    )


def _get_cache_stats(days):
    """Get cache performance statistics."""
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    cache_data = RequestLog.objects.filter(
        timestamp__gte=start_time
    ).aggregate(
        total_hits=Sum('cache_hits'),
        total_misses=Sum('cache_misses')
    )
    
    total_ops = (cache_data['total_hits'] or 0) + (cache_data['total_misses'] or 0)
    hit_rate = (cache_data['total_hits'] / total_ops * 100) if total_ops > 0 else 0
    
    return {
        'hits': cache_data['total_hits'] or 0,
        'misses': cache_data['total_misses'] or 0,
        'hit_rate': hit_rate
    }


def _get_failed_logins():
    """Get failed login attempts."""
    return SecurityEvent.objects.filter(
        event_type='failed_login'
    ).order_by('-timestamp')[:20]


def _get_rate_limit_hits():
    """Get rate limit violations."""
    return SecurityEvent.objects.filter(
        event_type='rate_limit_hit'
    ).order_by('-timestamp')[:20]


def _get_suspicious_activity():
    """Get suspicious activity events."""
    return SecurityEvent.objects.filter(
        event_type='suspicious_activity',
        resolved=False
    ).order_by('-timestamp')[:20]


def _get_recent_admin_actions():
    """Get recent admin actions."""
    return AdminAction.objects.order_by('-timestamp')[:20]


def _get_pending_queues():
    """Get detailed pending queue information."""
    pending_places = HalalPlace.objects.filter(status='pending')
    pending_suggestions = PlaceEditSuggestion.objects.filter(status='pending')
    pending_images = PlaceImageSuggestion.objects.filter(status='pending')
    unread_contacts = ContactMessage.objects.filter(is_read=False)
    
    return {
        'places': {
            'count': pending_places.count(),
            'oldest': pending_places.order_by('created_at').first(),
        },
        'suggestions': {
            'count': pending_suggestions.count(),
            'oldest': pending_suggestions.order_by('created_at').first(),
        },
        'images': {
            'count': pending_images.count(),
            'oldest': pending_images.order_by('created_at').first(),
        },
        'contacts': {
            'count': unread_contacts.count(),
            'oldest': unread_contacts.order_by('created_at').first(),
        },
    }


def _get_moderator_activity():
    """Get moderator activity statistics."""
    last_7_days = timezone.now() - timezone.timedelta(days=7)
    
    activity = ContentModerationLog.objects.filter(
        timestamp__gte=last_7_days
    ).values('moderator__username').annotate(
        total_actions=Count('id'),
        approved=Count('id', filter=Q(action='approved')),
        rejected=Count('id', filter=Q(action='rejected')),
        avg_time=Avg('time_in_queue_hours')
    ).order_by('-total_actions')[:10]
    
    return list(activity)


def _get_submission_trends():
    """Get submission trends over time."""
    last_30_days = timezone.now() - timezone.timedelta(days=30)
    
    places_by_day = HalalPlace.objects.filter(
        created_at__gte=last_30_days
    ).extra(select={'day': 'date(created_at)'}).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    return {
        'places': list(places_by_day),
    }


def _get_quality_metrics():
    """Get content quality metrics."""
    total_places = HalalPlace.objects.count()
    approved_places = HalalPlace.objects.filter(status='approved').count()
    rejected_places = HalalPlace.objects.filter(status='rejected').count()
    
    places_with_images = HalalPlace.objects.exclude(
        Q(photo_urls__isnull=True) | Q(photo_urls=[])
    ).count()
    
    return {
        'approval_rate': (approved_places / total_places * 100) if total_places > 0 else 0,
        'rejection_rate': (rejected_places / total_places * 100) if total_places > 0 else 0,
        'places_with_images': places_with_images,
        'image_coverage': (places_with_images / total_places * 100) if total_places > 0 else 0,
    }


def _get_user_engagement(days):
    """Get user engagement metrics."""
    cache_key = f"user_engagement_{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    total_users = User.objects.count()
    active_users = User.objects.filter(last_login__gte=start_time).count()
    new_users = User.objects.filter(created_at__gte=start_time).count()
    
    result = {
        'total_users': total_users,
        'active_users': active_users,
        'new_users': new_users,
        'dau': User.objects.filter(
            last_login__gte=timezone.now() - timezone.timedelta(days=1)
        ).count(),
        'mau': active_users if days >= 30 else None,
    }
    
    cache.set(cache_key, result, 300)  # Cache for 5 minutes
    return result


def _get_content_usage(days):
    """Get content usage statistics."""
    cache_key = f"content_usage_{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    most_viewed_places = HalalPlace.objects.filter(
        status='approved'
    ).order_by('-id')[:10]  # Would need view_count field
    
    most_reviewed = HalalPlace.objects.annotate(
        review_count=Count('reviews')
    ).order_by('-review_count')[:10]
    
    result = {
        'most_reviewed': list(most_reviewed.values('name', 'review_count')),
        'popular_categories': list(
            HalalPlace.objects.values('category').annotate(
                count=Count('id')
            ).order_by('-count')
        ),
    }
    
    cache.set(cache_key, result, 300)  # Cache for 5 minutes
    return result


def _get_geographic_distribution():
    """Get geographic distribution of content."""
    # This would need geocoding or city field
    return {
        'by_city': [],  # Placeholder
    }


def _get_language_preferences():
    """Get language preference distribution."""
    cache_key = "language_preferences"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    result = list(
        User.objects.values('preferred_language').annotate(
            count=Count('id')
        ).order_by('-count')
    )
    
    cache.set(cache_key, result, 300)  # Cache for 5 minutes
    return result


# ============================================================================
# New Helper Functions for Enhanced Dashboard
# ============================================================================

def _get_yesterday_stats():
    """Get yesterday's statistics for comparison."""
    yesterday_start = (timezone.now() - timezone.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    yesterday_end = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_requests = RequestLog.objects.filter(
        timestamp__gte=yesterday_start,
        timestamp__lt=yesterday_end
    ).count()
    
    error_count = RequestLog.objects.filter(
        timestamp__gte=yesterday_start,
        timestamp__lt=yesterday_end,
        status_code__gte=500
    ).count()
    
    avg_response = RequestLog.objects.filter(
        timestamp__gte=yesterday_start,
        timestamp__lt=yesterday_end
    ).aggregate(avg=Avg('response_time_ms'))
    
    return {
        'total_requests': total_requests,
        'error_count': error_count,
        'error_rate': (error_count / total_requests * 100) if total_requests > 0 else 0,
        'avg_response_time': avg_response['avg'] or 0,
    }


def _get_system_health():
    """Get overall system health status."""
    now = timezone.now()
    last_hour = now - timezone.timedelta(hours=1)
    
    # Check error rate
    recent_requests = RequestLog.objects.filter(timestamp__gte=last_hour).count()
    recent_errors = RequestLog.objects.filter(
        timestamp__gte=last_hour,
        status_code__gte=500
    ).count()
    error_rate = (recent_errors / recent_requests * 100) if recent_requests > 0 else 0
    
    # Check response time
    avg_response = RequestLog.objects.filter(
        timestamp__gte=last_hour
    ).aggregate(avg=Avg('response_time_ms'))['avg'] or 0
    
    # Check unresolved security events
    critical_events = SecurityEvent.objects.filter(
        resolved=False,
        severity__in=['critical', 'high']
    ).count()
    
    # Check database connectivity
    db_healthy = True
    try:
        connection.ensure_connection()
    except Exception:
        db_healthy = False
    
    # Check cache connectivity
    cache_healthy = True
    try:
        cache.set('_health_check', 'ok', 1)
        cache_healthy = cache.get('_health_check') == 'ok'
    except Exception:
        cache_healthy = False
    
    # Determine overall status
    if not db_healthy or not cache_healthy or critical_events > 0 or error_rate > 10:
        status = 'critical'
        status_text = 'Critical Issues'
    elif error_rate > 5 or avg_response > 2000:
        status = 'warning'
        status_text = 'Degraded Performance'
    else:
        status = 'healthy'
        status_text = 'All Systems Operational'
    
    return {
        'status': status,
        'status_text': status_text,
        'error_rate': round(error_rate, 1),
        'avg_response_time': round(avg_response, 0),
        'critical_events': critical_events,
        'db_healthy': db_healthy,
        'cache_healthy': cache_healthy,
        'checks': [
            {'name': 'Database', 'healthy': db_healthy},
            {'name': 'Cache', 'healthy': cache_healthy},
            {'name': 'Error Rate', 'healthy': error_rate < 5},
            {'name': 'Response Time', 'healthy': avg_response < 1000},
            {'name': 'Security', 'healthy': critical_events == 0},
        ]
    }


def _get_unread_notification_count(user):
    """Get count of unread notifications for the user."""
    return AdminNotification.objects.filter(
        Q(recipient=user) | Q(recipient__isnull=True),
        read=False,
        dismissed=False
    ).count()


def _get_percentile_stats(days):
    """Get P50, P95, P99 response time percentiles."""
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    # Get all response times for the period
    response_times = list(
        RequestLog.objects.filter(
            timestamp__gte=start_time
        ).values_list('response_time_ms', flat=True).order_by('response_time_ms')
    )
    
    if not response_times:
        return {'p50': 0, 'p95': 0, 'p99': 0}
    
    def percentile(data, p):
        n = len(data)
        k = (n - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < n else f
        return data[f] + (k - f) * (data[c] - data[f]) if f != c else data[f]
    
    return {
        'p50': round(percentile(response_times, 50), 0),
        'p95': round(percentile(response_times, 95), 0),
        'p99': round(percentile(response_times, 99), 0),
    }


def _get_error_rate_trend(days):
    """Get error rate trend over time."""
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    daily_stats = RequestLog.objects.filter(
        timestamp__gte=start_time
    ).annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(
        total=Count('id'),
        errors=Count('id', filter=Q(status_code__gte=500))
    ).order_by('date')
    
    labels = []
    rates = []
    
    for stat in daily_stats:
        labels.append(stat['date'].strftime('%m/%d'))
        rate = (stat['errors'] / stat['total'] * 100) if stat['total'] > 0 else 0
        rates.append(round(rate, 2))
    
    return {'labels': labels, 'rates': rates}


def _get_response_time_trend(days):
    """Get response time trend over time."""
    start_time = timezone.now() - timezone.timedelta(days=days)
    
    daily_stats = RequestLog.objects.filter(
        timestamp__gte=start_time
    ).annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(
        avg_time=Avg('response_time_ms'),
        max_time=Max('response_time_ms')
    ).order_by('date')
    
    labels = []
    avg_times = []
    max_times = []
    
    for stat in daily_stats:
        labels.append(stat['date'].strftime('%m/%d'))
        avg_times.append(round(stat['avg_time'] or 0, 0))
        max_times.append(round(stat['max_time'] or 0, 0))
    
    return {'labels': labels, 'avg_times': avg_times, 'max_times': max_times}
