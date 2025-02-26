from django.contrib import admin
from .models import User

# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'preferred_language', 'created_at', 'updated_at')
    list_filter = ('preferred_language', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('-created_at',)
