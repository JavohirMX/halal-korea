from django.contrib import admin

# Register your models here.
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'place', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'place__name', 'comment')
    readonly_fields = ('created_at', 'updated_at')
