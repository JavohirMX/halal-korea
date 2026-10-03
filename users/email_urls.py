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
    path('api/preview/', admin_email_views.email_preview, name='preview'),
    path('api/users/', admin_email_views.email_user_search, name='user_search'),
    path('api/render-preview/', admin_email_views.email_render_preview, name='render_preview'),
    path('api/test-send/', admin_email_views.email_test_send, name='test_send'),
]
