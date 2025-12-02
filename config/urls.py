"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from blog.upload_views import tinymce_upload_view
from utils.language_views import set_language, set_language_ajax, get_user_language_preferences
from config.sitemaps import sitemaps
from utils import admin_views

urlpatterns = [
    # --- Monitoring Dashboard URLs (MUST come before admin URLs) ---
    path('admin/monitoring/', admin_views.monitoring_dashboard, name='monitoring_dashboard'),
    path('admin/monitoring/performance/', admin_views.performance_dashboard, name='monitoring_performance'),
    path('admin/monitoring/security/', admin_views.security_dashboard, name='monitoring_security'),
    path('admin/monitoring/content/', admin_views.content_operations_dashboard, name='monitoring_content'),
    path('admin/monitoring/analytics/', admin_views.analytics_dashboard, name='monitoring_analytics'),
    path('admin/monitoring/logs/', admin_views.logs_dashboard, name='monitoring_logs'),
    
    # --- Monitoring API Endpoints ---
    path('admin/monitoring/api/metrics/', admin_views.api_metrics, name='monitoring_api_metrics'),
    path('admin/monitoring/api/stats/', admin_views.api_stats, name='monitoring_api_stats'),
    path('admin/monitoring/api/performance/', admin_views.api_performance, name='monitoring_api_performance'),
    path('admin/monitoring/api/charts/', admin_views.api_chart_data, name='monitoring_api_charts'),
    
    # --- Admin URLs ---
    path('admin/', admin.site.urls),

    # --- Translation & Internationalization ---
    # Translation management (admin access required)
    path('rosetta/', include('rosetta.urls')),
    # Enhanced language switching with user preference updates
    path('i18n/setlang/', set_language, name='set_language'),
    path('i18n/setlang-ajax/', set_language_ajax, name='set_language_ajax'),
    path('i18n/preferences/', get_user_language_preferences, name='user_language_preferences'),
    path('i18n/', include('django.conf.urls.i18n')),  # Keep for compatibility

    # --- Rich Text Editor (TinyMCE) ---
    path('tinymce/', include('tinymce.urls')),
    path('tinymce/upload/', tinymce_upload_view, name='tinymce_upload'),

    # --- SEO URLs ---
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),

    # --- Authentication URLs ---
    path('accounts/', include('allauth.urls')),  # Social authentication
    
    # --- App-specific URLs ---
    path('', include('places.urls')),  # Home/Places as root
    path('users/', include('users.urls')),
    path('reviews/', include('reviews.urls')),
    path('prayer/', include('prayer_times.urls')),
    path('blog/', include('blog.urls')),
    path('contact/', include('contact.urls')),
    path('feedback/', include('feedback.urls')),
]

# Static and media files are typically not prefixed
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'places.views.handler404'
