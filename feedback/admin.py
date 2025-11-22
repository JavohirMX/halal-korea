from django.contrib import admin
from django.db.models import Avg
from django.utils.html import format_html
from .models import FeedbackResponse


@admin.register(FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    """Admin interface for viewing and managing feedback responses"""
    
    list_display = [
        'created_at_display',
        'user_display', 
        'rating_display',
        'page_type',
        'language',
        'device_type',
        'is_reviewed',
    ]
    
    list_filter = [
        'rating',
        'page_type',
        'language',
        'device_type',
        'is_reviewed',
        'is_actionable',
        'admin_category',
        'created_at',
    ]
    
    search_fields = [
        'comment',
        'page_url',
        'user__username',
        'user__email',
        'session_id',
    ]
    
    readonly_fields = [
        'created_at',
        'user',
        'session_id',
        'rating',
        'comment',
        'page_url',
        'page_type',
        'page_title',
        'time_on_site',
        'time_on_page',
        'pages_visited',
        'scroll_depth',
        'language',
        'device_type',
        'browser',
        'screen_resolution',
        'ip_address',
        'user_agent',
        'referrer',
    ]
    
    fieldsets = (
        ('Feedback Content', {
            'fields': ('rating', 'comment', 'user', 'session_id')
        }),
        ('Page Context', {
            'fields': ('page_url', 'page_type', 'page_title')
        }),
        ('User Behavior', {
            'fields': (
                'time_on_site',
                'time_on_page',
                'pages_visited',
                'scroll_depth'
            )
        }),
        ('Technical Details', {
            'fields': (
                'language',
                'device_type',
                'browser',
                'screen_resolution',
                'referrer'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
        ('Admin Review', {
            'fields': (
                'admin_category',
                'admin_notes',
                'is_reviewed',
                'is_actionable'
            )
        }),
    )
    
    actions = ['mark_as_reviewed', 'mark_as_actionable']
    
    def created_at_display(self, obj):
        """Display formatted creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = 'Date'
    created_at_display.admin_order_field = 'created_at'
    
    def user_display(self, obj):
        """Display user or anonymous session"""
        if obj.user:
            return format_html(
                '<span style="color: #059669;">👤 {}</span>',
                obj.user.username
            )
        return format_html(
            '<span style="color: #6b7280;">👻 Anon-{}</span>',
            obj.session_id[:8]
        )
    user_display.short_description = 'User'
    
    def rating_display(self, obj):
        """Display star rating with color"""
        stars = '⭐' * obj.rating
        color = '#22c55e' if obj.rating >= 4 else '#f59e0b' if obj.rating == 3 else '#ef4444'
        return format_html(
            '<span style="color: {}; font-size: 16px;">{} ({})</span>',
            color,
            stars,
            obj.rating
        )
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'rating'
    
    def mark_as_reviewed(self, request, queryset):
        """Mark selected feedback as reviewed"""
        updated = queryset.update(is_reviewed=True)
        self.message_user(request, f'{updated} feedback(s) marked as reviewed.')
    mark_as_reviewed.short_description = 'Mark as reviewed'
    
    def mark_as_actionable(self, request, queryset):
        """Mark selected feedback as actionable"""
        updated = queryset.update(is_actionable=True)
        self.message_user(request, f'{updated} feedback(s) marked as actionable.')
    mark_as_actionable.short_description = 'Mark as actionable'
    
    def changelist_view(self, request, extra_context=None):
        """Add summary statistics to the changelist view"""
        extra_context = extra_context or {}
        
        # Calculate statistics
        total_feedback = FeedbackResponse.objects.count()
        avg_rating = FeedbackResponse.objects.aggregate(Avg('rating'))['rating__avg']
        unreviewed_count = FeedbackResponse.objects.filter(is_reviewed=False).count()
        
        extra_context['total_feedback'] = total_feedback
        extra_context['avg_rating'] = round(avg_rating, 2) if avg_rating else 0
        extra_context['unreviewed_count'] = unreviewed_count
        
        return super().changelist_view(request, extra_context=extra_context)

