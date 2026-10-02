"""
URL configuration for the admin Email hub.

Prefixed with 'admin/email/' in the main urls.py (before admin.site.urls).
"""
from django.urls import path

from users import admin_email_views

app_name = 'admin_email'

urlpatterns = [
    path('', admin_email_views.email_hub, name='hub'),
    path('compose/', admin_email_views.email_compose, name='compose'),
]
