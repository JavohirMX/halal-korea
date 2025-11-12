"""
Monitoring models for tracking system metrics, requests, admin actions, and security events.
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import hashlib


def hash_ip(ip_address):
    """Hash IP address for privacy while maintaining uniqueness for tracking."""
    if not ip_address:
        return None
    salt = settings.SECRET_KEY[:16]
    return hashlib.sha256(f"{salt}{ip_address}".encode()).hexdigest()[:16]


def hash_user_agent(user_agent):
    """Hash user agent for privacy."""
    if not user_agent:
        return ''  # Return empty string instead of None
    salt = settings.SECRET_KEY[:16]
    return hashlib.sha256(f"{salt}{user_agent}".encode()).hexdigest()[:16]


class SystemMetric(models.Model):
    """Aggregate metrics by hour/day for system monitoring."""
    
    METRIC_TYPE_CHOICES = [
        ('request_count', 'Request Count'),
        ('error_count', 'Error Count'),
        ('avg_response_time', 'Average Response Time'),
        ('db_query_count', 'Database Query Count'),
        ('cache_hit_rate', 'Cache Hit Rate'),
        ('active_users', 'Active Users'),
        ('api_call_count', 'External API Call Count'),
        ('api_latency', 'External API Latency'),
    ]
    
    timestamp = models.DateTimeField(db_index=True)
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPE_CHOICES, db_index=True)
    metric_name = models.CharField(max_length=100, db_index=True, help_text="Specific metric identifier (e.g., endpoint path, API name)")
    value = models.FloatField()
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional context data")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'metric_type', 'metric_name']),
            models.Index(fields=['metric_type', 'timestamp']),
        ]
        verbose_name = 'System Metric'
        verbose_name_plural = 'System Metrics'
    
    def __str__(self):
        return f"{self.metric_type} - {self.metric_name}: {self.value} at {self.timestamp}"


class RequestLog(models.Model):
    """Sampled request tracking with performance data."""
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField(db_index=True)
    response_time_ms = models.FloatField(db_index=True, help_text="Response time in milliseconds")
    
    # User info (nullable for anonymous requests)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_logs'
    )
    is_staff = models.BooleanField(default=False, db_index=True)
    
    # Privacy-protected fields
    ip_hash = models.CharField(max_length=16, db_index=True, help_text="Hashed IP address")
    user_agent_hash = models.CharField(max_length=16, blank=True, help_text="Hashed user agent")
    
    # Performance metrics
    db_query_count = models.IntegerField(default=0)
    cache_hits = models.IntegerField(default=0)
    cache_misses = models.IntegerField(default=0)
    
    # Error tracking
    error_type = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['status_code', 'timestamp']),
            models.Index(fields=['response_time_ms']),
            models.Index(fields=['is_staff', 'timestamp']),
        ]
        verbose_name = 'Request Log'
        verbose_name_plural = 'Request Logs'
    
    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code} ({self.response_time_ms}ms)"
    
    @property
    def is_error(self):
        return self.status_code >= 400
    
    @property
    def is_slow(self):
        return self.response_time_ms > getattr(settings, 'MONITORING_SLOW_THRESHOLD_MS', 1000)


class AdminAction(models.Model):
    """Audit trail for admin operations."""
    
    ACTION_TYPE_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('archive', 'Archive'),
        ('bulk_action', 'Bulk Action'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_actions'
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES, db_index=True)
    
    # Content tracking
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    object_repr = models.CharField(max_length=200, help_text="String representation of the object")
    
    # Change tracking
    changes = models.JSONField(default=dict, blank=True, help_text="Before/after values for updates")
    
    # Privacy
    ip_hash = models.CharField(max_length=16, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'admin_user']),
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['admin_user', 'timestamp']),
        ]
        verbose_name = 'Admin Action'
        verbose_name_plural = 'Admin Actions'
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.action_type} {self.object_repr}"


class ContentModerationLog(models.Model):
    """Track moderation workflow for content approval/rejection."""
    
    CONTENT_TYPE_CHOICES = [
        ('place', 'Halal Place'),
        ('review', 'Review'),
        ('blog', 'Blog Post'),
        ('suggestion', 'Edit Suggestion'),
        ('image_suggestion', 'Image Suggestion'),
        ('contact', 'Contact Message'),
    ]
    
    ACTION_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
        ('pending', 'Set to Pending'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moderation_actions'
    )
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    object_id = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    
    time_in_queue_hours = models.FloatField(
        null=True,
        blank=True,
        help_text="Hours between submission and moderation"
    )
    reason = models.TextField(blank=True, help_text="Optional reason for rejection")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'moderator']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        verbose_name = 'Content Moderation Log'
        verbose_name_plural = 'Content Moderation Logs'
    
    def __str__(self):
        return f"{self.moderator.username} - {self.action} {self.content_type} #{self.object_id}"


class SecurityEvent(models.Model):
    """Security incidents and suspicious activity tracking."""
    
    EVENT_TYPE_CHOICES = [
        ('failed_login', 'Failed Login'),
        ('rate_limit_hit', 'Rate Limit Hit'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('permission_denied', 'Permission Denied'),
        ('csrf_failure', 'CSRF Failure'),
        ('invalid_token', 'Invalid Token'),
        ('multiple_accounts', 'Multiple Accounts from Same IP'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium', db_index=True)
    
    # User info (nullable for anonymous attempts)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events'
    )
    
    # Privacy-protected tracking
    ip_hash = models.CharField(max_length=16, db_index=True)
    
    # Event details
    details = models.JSONField(default=dict, help_text="Additional context about the event")
    
    # Resolution tracking
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_security_events'
    )
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'event_type']),
            models.Index(fields=['severity', 'resolved', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
        ]
        verbose_name = 'Security Event'
        verbose_name_plural = 'Security Events'
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{self.event_type} - {user_str} ({self.severity})"
    
    def mark_resolved(self, user, notes=''):
        """Mark the security event as resolved."""
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.resolution_notes = notes
        self.save(update_fields=['resolved', 'resolved_at', 'resolved_by', 'resolution_notes'])


class AdminNotification(models.Model):
    """In-app notifications for admin users."""
    
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Recipient (null = all admins)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_notifications',
        help_text="Leave blank to send to all admins"
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    link = models.CharField(max_length=500, blank=True, help_text="Optional link to related page")
    
    # Status tracking
    read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['recipient', 'read', 'timestamp']),
            models.Index(fields=['severity', 'read']),
        ]
        verbose_name = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'
    
    def __str__(self):
        recipient_str = self.recipient.username if self.recipient else 'All Admins'
        return f"{self.title} - {recipient_str}"
    
    def mark_read(self):
        """Mark notification as read."""
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save(update_fields=['read', 'read_at'])
    
    def mark_dismissed(self):
        """Mark notification as dismissed."""
        if not self.dismissed:
            self.dismissed = True
            self.dismissed_at = timezone.now()
            self.save(update_fields=['dismissed', 'dismissed_at'])


class AlertRule(models.Model):
    """Configurable alert rules for monitoring."""
    
    CONDITION_CHOICES = [
        ('error_rate_above', 'Error Rate Above Threshold'),
        ('response_time_above', 'Response Time Above Threshold'),
        ('queue_age_above', 'Queue Age Above Threshold'),
        ('failed_login_spike', 'Failed Login Spike'),
        ('db_slow_queries', 'Database Slow Queries'),
        ('cache_hit_rate_below', 'Cache Hit Rate Below Threshold'),
        ('api_failure', 'External API Failure'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    
    # Rule configuration
    condition = models.CharField(max_length=30, choices=CONDITION_CHOICES)
    threshold = models.FloatField(help_text="Threshold value for the condition")
    window_minutes = models.IntegerField(default=10, help_text="Time window to evaluate the condition")
    
    # Alert channels (JSON array of channel names)
    alert_channels = models.JSONField(
        default=list,
        help_text="List of alert channels: ['telegram', 'email', 'in_app']"
    )
    
    # Status
    enabled = models.BooleanField(default=True, db_index=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    trigger_count = models.IntegerField(default=0)
    
    # Rate limiting
    cooldown_minutes = models.IntegerField(
        default=60,
        help_text="Minimum minutes between alerts for this rule"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'
    
    def __str__(self):
        status = "Enabled" if self.enabled else "Disabled"
        return f"{self.name} ({status})"
    
    def can_trigger(self):
        """Check if enough time has passed since last trigger (cooldown)."""
        if not self.enabled:
            return False
        if not self.last_triggered:
            return True
        
        cooldown_delta = timezone.timedelta(minutes=self.cooldown_minutes)
        return timezone.now() - self.last_triggered > cooldown_delta
    
    def record_trigger(self):
        """Record that this alert was triggered."""
        self.last_triggered = timezone.now()
        self.trigger_count += 1
        self.save(update_fields=['last_triggered', 'trigger_count'])

