from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject_preview', 'user_type', 'created_at', 'is_read', 'response_status']
    list_filter = ['is_read', 'responded_at', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        (_('Contact Information'), {
            'fields': ('user', 'name', 'email')
        }),
        (_('Message'), {
            'fields': ('subject', 'message')
        }),
        (_('Metadata'), {
            'fields': ('ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_read', 'responded_at')
        }),
    )
    
    def subject_preview(self, obj):
        """Show a preview of the subject"""
        if obj.subject:
            return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
        return _('(No subject)')
    subject_preview.short_description = _('Subject')
    
    def user_type(self, obj):
        """Show if the message is from a registered user or anonymous"""
        if obj.user:
            return format_html(
                '<span style="color: green;">👤 {}</span>',
                _('Registered User')
            )
        return format_html(
            '<span style="color: orange;">❓ {}</span>',
            _('Anonymous')
        )
    user_type.short_description = _('User Type')
    
    def response_status(self, obj):
        """Show response status"""
        if obj.responded_at:
            return format_html(
                '<span style="color: green;">✅ {}</span>',
                _('Responded')
            )
        elif obj.is_read:
            return format_html(
                '<span style="color: orange;">👁️ {}</span>',
                _('Read')
            )
        return format_html(
            '<span style="color: red;">✉️ {}</span>',
            _('Unread')
        )
    response_status.short_description = _('Status')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    actions = ['mark_as_read', 'mark_as_responded']
    
    def mark_as_read(self, request, queryset):
        """Mark selected messages as read"""
        updated = queryset.update(is_read=True)
        self.message_user(
            request,
            _(f'{updated} message(s) marked as read.')
        )
    mark_as_read.short_description = _('Mark selected messages as read')
    
    def mark_as_responded(self, request, queryset):
        """Mark selected messages as responded"""
        updated = 0
        for message in queryset:
            message.mark_as_responded()
            updated += 1
        
        self.message_user(
            request,
            _(f'{updated} message(s) marked as responded.')
        )
    mark_as_responded.short_description = _('Mark selected messages as responded')
