from django.contrib import admin
from .models import RamadanConfig


@admin.register(RamadanConfig)
class RamadanConfigAdmin(admin.ModelAdmin):
    list_display = ('year', 'hijri_year', 'start_date', 'end_date', 'total_days', 'is_active', 'updated_at')
    list_filter = ('is_active', 'year')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'total_days')
    fieldsets = (
        (None, {
            'fields': ('year', 'hijri_year', 'start_date', 'end_date', 'total_days', 'is_active')
        }),
        ('Details', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_days(self, obj):
        return obj.total_days
    total_days.short_description = "Total Days"
