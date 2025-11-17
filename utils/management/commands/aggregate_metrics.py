"""
Management command to aggregate request logs into system metrics.
Should be run hourly via cron job.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Avg, Count, Max, Min, Q
from django.conf import settings
from utils.models import RequestLog, SystemMetric
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Aggregate request logs into hourly system metrics and clean up old data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Number of hours to aggregate (default: 1)'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old request logs after aggregation'
        )
    
    def handle(self, *args, **options):
        hours = options['hours']
        cleanup = options['cleanup']
        
        self.stdout.write(self.style.SUCCESS(f'Starting metric aggregation for last {hours} hour(s)...'))
        
        # Calculate time window
        end_time = timezone.now()
        start_time = end_time - timezone.timedelta(hours=hours)
        
        # Get request logs in time window
        logs = RequestLog.objects.filter(
            timestamp__gte=start_time,
            timestamp__lt=end_time
        )
        
        total_logs = logs.count()
        self.stdout.write(f'Found {total_logs} request logs to aggregate')
        
        if total_logs == 0:
            self.stdout.write(self.style.WARNING('No logs to aggregate'))
            return
        
        # Aggregate metrics
        self._aggregate_request_metrics(logs, start_time)
        self._aggregate_error_metrics(logs, start_time)
        self._aggregate_performance_metrics(logs, start_time)
        self._aggregate_endpoint_metrics(logs, start_time)
        
        # Cleanup old logs if requested
        if cleanup:
            self._cleanup_old_logs()
        
        self.stdout.write(self.style.SUCCESS('Metric aggregation completed successfully'))
    
    def _aggregate_request_metrics(self, logs, timestamp):
        """Aggregate total request counts."""
        total_requests = logs.count()
        
        SystemMetric.objects.create(
            timestamp=timestamp,
            metric_type='request_count',
            metric_name='total_requests',
            value=total_requests,
            metadata={'aggregation': 'hourly'}
        )
        
        # By status code category
        success_count = logs.filter(status_code__lt=400).count()
        client_error_count = logs.filter(status_code__gte=400, status_code__lt=500).count()
        server_error_count = logs.filter(status_code__gte=500).count()
        
        SystemMetric.objects.create(
            timestamp=timestamp,
            metric_type='request_count',
            metric_name='successful_requests',
            value=success_count,
            metadata={'status_range': '2xx-3xx'}
        )
        
        SystemMetric.objects.create(
            timestamp=timestamp,
            metric_type='request_count',
            metric_name='client_errors',
            value=client_error_count,
            metadata={'status_range': '4xx'}
        )
        
        SystemMetric.objects.create(
            timestamp=timestamp,
            metric_type='request_count',
            metric_name='server_errors',
            value=server_error_count,
            metadata={'status_range': '5xx'}
        )
        
        self.stdout.write(f'  ✓ Request metrics: {total_requests} total, {server_error_count} errors')
    
    def _aggregate_error_metrics(self, logs, timestamp):
        """Aggregate error counts and types."""
        error_logs = logs.filter(status_code__gte=400)
        error_count = error_logs.count()
        
        SystemMetric.objects.create(
            timestamp=timestamp,
            metric_type='error_count',
            metric_name='total_errors',
            value=error_count,
            metadata={'aggregation': 'hourly'}
        )
        
        # Group by error type
        error_types = error_logs.exclude(error_type='').values('error_type').annotate(
            count=Count('id')
        )
        
        for error_type_data in error_types:
            SystemMetric.objects.create(
                timestamp=timestamp,
                metric_type='error_count',
                metric_name=error_type_data['error_type'] or 'unknown',
                value=error_type_data['count'],
                metadata={'aggregation': 'hourly'}
            )
        
        self.stdout.write(f'  ✓ Error metrics: {error_count} errors, {len(error_types)} types')
    
    def _aggregate_performance_metrics(self, logs, timestamp):
        """Aggregate performance metrics (response times, queries)."""
        perf_stats = logs.aggregate(
            avg_response_time=Avg('response_time_ms'),
            max_response_time=Max('response_time_ms'),
            min_response_time=Min('response_time_ms'),
            avg_db_queries=Avg('db_query_count'),
        )
        
        # Average response time
        if perf_stats['avg_response_time']:
            SystemMetric.objects.create(
                timestamp=timestamp,
                metric_type='avg_response_time',
                metric_name='all_endpoints',
                value=perf_stats['avg_response_time'],
                metadata={
                    'max': perf_stats['max_response_time'],
                    'min': perf_stats['min_response_time']
                }
            )
        
        # Database query metrics
        if perf_stats['avg_db_queries']:
            SystemMetric.objects.create(
                timestamp=timestamp,
                metric_type='db_query_count',
                metric_name='avg_queries_per_request',
                value=perf_stats['avg_db_queries'],
                metadata={'aggregation': 'hourly'}
            )
        
        # Cache hit rate
        total_cache_ops = logs.aggregate(
            total_hits=Count('id', filter=Q(cache_hits__gt=0)),
            total_misses=Count('id', filter=Q(cache_misses__gt=0))
        )
        
        total_ops = total_cache_ops['total_hits'] + total_cache_ops['total_misses']
        if total_ops > 0:
            hit_rate = (total_cache_ops['total_hits'] / total_ops) * 100
            SystemMetric.objects.create(
                timestamp=timestamp,
                metric_type='cache_hit_rate',
                metric_name='overall',
                value=hit_rate,
                metadata={
                    'hits': total_cache_ops['total_hits'],
                    'misses': total_cache_ops['total_misses']
                }
            )
        
        self.stdout.write(f'  ✓ Performance metrics: {perf_stats["avg_response_time"]:.2f}ms avg response')
    
    def _aggregate_endpoint_metrics(self, logs, timestamp):
        """Aggregate metrics per endpoint."""
        # Group by path
        endpoint_stats = logs.values('path').annotate(
            count=Count('id'),
            avg_time=Avg('response_time_ms'),
            error_count=Count('id', filter=Q(status_code__gte=400))
        ).order_by('-count')[:20]  # Top 20 endpoints
        
        for endpoint in endpoint_stats:
            # Request count per endpoint
            SystemMetric.objects.create(
                timestamp=timestamp,
                metric_type='request_count',
                metric_name=endpoint['path'][:100],
                value=endpoint['count'],
                metadata={
                    'avg_response_time': endpoint['avg_time'],
                    'error_count': endpoint['error_count']
                }
            )
        
        self.stdout.write(f'  ✓ Endpoint metrics: {len(endpoint_stats)} endpoints tracked')
    
    def _cleanup_old_logs(self):
        """Clean up request logs older than retention period."""
        retention_days = getattr(settings, 'MONITORING_RETENTION_DAYS', 30)
        cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)
        
        old_logs = RequestLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        
        if count > 0:
            old_logs.delete()
            self.stdout.write(self.style.WARNING(f'  ✓ Cleaned up {count} old request logs (>{retention_days} days)'))
        else:
            self.stdout.write('  ✓ No old logs to clean up')

