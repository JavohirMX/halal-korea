from django.contrib import admin
from .models import HalalPlace

@admin.register(HalalPlace)
class HalalPlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'status', 'address', 'created_at', 'updated_at')
    list_filter = ('category', 'status')
    search_fields = ('name', 'description', 'address')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)
