"""
Admin registration for monitoring models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from utils.models import (
    SystemMetric, RequestLog, AdminAction, ContentModerationLog,
    SecurityEvent, AdminNotification, AlertRule
)


@admin.register(SystemMetric)
class SystemMetricAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'metric_type', 'metric_name', 'value', 'created_at')
    list_filter = ('metric_type', 'timestamp')
    search_fields = ('metric_name',)
    readonly_fields = ('timestamp', 'metric_type', 'metric_name', 'value', 'metadata', 'created_at')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'method', 'path_short', 'status_code_badge', 'response_time_ms', 'user', 'is_staff')
    list_filter = ('status_code', 'method', 'is_staff', 'timestamp')
    search_fields = ('path', 'error_type')
    readonly_fields = ('timestamp', 'path', 'method', 'status_code', 'response_time_ms', 
                      'user', 'is_staff', 'ip_hash', 'user_agent_hash', 'db_query_count',
                      'cache_hits', 'cache_misses', 'error_type', 'error_message')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def path_short(self, obj):
        return obj.path[:50] + '...' if len(obj.path) > 50 else obj.path
    path_short.short_description = 'Path'
    
    def status_code_badge(self, obj):
        color = 'green' if obj.status_code < 400 else 'red' if obj.status_code >= 500 else 'orange'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.status_code
        )
    status_code_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False


@admin.register(AdminAction)
class AdminActionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'admin_user', 'action_type', 'object_repr', 'content_type')
    list_filter = ('action_type', 'timestamp', 'admin_user')
    search_fields = ('object_repr', 'admin_user__username')
    readonly_fields = ('timestamp', 'admin_user', 'action_type', 'content_type', 
                      'object_id', 'object_repr', 'changes', 'ip_hash')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False  # Audit log should not be deletable


@admin.register(ContentModerationLog)
class ContentModerationLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'moderator', 'content_type', 'action', 'time_in_queue_hours')
    list_filter = ('action', 'content_type', 'timestamp', 'moderator')
    search_fields = ('moderator__username',)
    readonly_fields = ('timestamp', 'moderator', 'content_type', 'object_id', 
                      'action', 'time_in_queue_hours', 'reason')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'event_type', 'severity_badge', 'user', 'resolved_status')
    list_filter = ('event_type', 'severity', 'resolved', 'timestamp')
    search_fields = ('user__username', 'ip_hash')
    readonly_fields = ('timestamp', 'event_type', 'severity', 'user', 'ip_hash', 'details')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    actions = ['mark_as_resolved']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('timestamp', 'event_type', 'severity', 'user', 'ip_hash', 'details')
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_at', 'resolved_by', 'resolution_notes')
        }),
    )
    
    def severity_badge(self, obj):
        colors = {
            'low': '#3b82f6',
            'medium': '#f59e0b',
            'high': '#f97316',
            'critical': '#ef4444'
        }
        color = colors.get(obj.severity, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color, obj.get_severity_display().upper()
        )
    severity_badge.short_description = 'Severity'
    
    def resolved_status(self, obj):
        if obj.resolved:
            return format_html('<span style="color: green;">✓ Resolved</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    resolved_status.short_description = 'Status'
    
    def mark_as_resolved(self, request, queryset):
        for event in queryset:
            event.mark_resolved(request.user, 'Resolved via admin action')
        self.message_user(request, f'{queryset.count()} event(s) marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected as resolved'
    
    def has_add_permission(self, request):
        return False


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'title', 'severity_badge', 'recipient', 'read_status')
    list_filter = ('severity', 'read', 'dismissed', 'timestamp')
    search_fields = ('title', 'message', 'recipient__username')
    readonly_fields = ('timestamp', 'title', 'message', 'severity', 'link', 'recipient')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    actions = ['mark_as_read', 'mark_as_dismissed']
    
    def severity_badge(self, obj):
        colors = {
            'info': '#3b82f6',
            'warning': '#f59e0b',
            'error': '#f97316',
            'critical': '#ef4444'
        }
        color = colors.get(obj.severity, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_severity_display().upper()
        )
    severity_badge.short_description = 'Severity'
    
    def read_status(self, obj):
        if obj.dismissed:
            return format_html('<span style="color: gray;">Dismissed</span>')
        elif obj.read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: orange; font-weight: bold;">Unread</span>')
    read_status.short_description = 'Status'
    
    def mark_as_read(self, request, queryset):
        for notification in queryset:
            notification.mark_read()
        self.message_user(request, f'{queryset.count()} notification(s) marked as read.')
    mark_as_read.short_description = 'Mark as read'
    
    def mark_as_dismissed(self, request, queryset):
        for notification in queryset:
            notification.mark_dismissed()
        self.message_user(request, f'{queryset.count()} notification(s) dismissed.')
    mark_as_dismissed.short_description = 'Dismiss notifications'


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'condition', 'threshold', 'enabled_badge', 'last_triggered', 'trigger_count')
    list_filter = ('enabled', 'condition')
    search_fields = ('name', 'description')
    list_editable = ('enabled',)
    
    fieldsets = (
        ('Rule Configuration', {
            'fields': ('name', 'description', 'condition', 'threshold', 'window_minutes')
        }),
        ('Alert Channels', {
            'fields': ('alert_channels', 'enabled')
        }),
        ('Rate Limiting', {
            'fields': ('cooldown_minutes',)
        }),
        ('Statistics', {
            'fields': ('last_triggered', 'trigger_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('last_triggered', 'trigger_count', 'created_at', 'updated_at')
    
    def enabled_badge(self, obj):
        if obj.enabled:
            return format_html('<span style="color: green; font-weight: bold;">✓ Enabled</span>')
        return format_html('<span style="color: gray;">Disabled</span>')
    enabled_badge.short_description = 'Status'


# Customize admin site header
admin.site.site_header = "Halal Korea Administration"
admin.site.site_title = "Halal Korea Admin"
admin.site.index_title = "Welcome to Halal Korea Administration"

