from django.contrib import admin
from .models import HalalPlace

@admin.register(HalalPlace)
class HalalPlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'address', 'created_at', 'updated_at')
    list_filter = ('category',)
    search_fields = ('name', 'description', 'address')
    readonly_fields = ('created_at', 'updated_at')

