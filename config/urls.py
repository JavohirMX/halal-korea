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
from blog.upload_views import tinymce_upload_view
from utils.language_views import set_language, set_language_ajax, get_user_language_preferences

urlpatterns = [
    path('admin/', admin.site.urls),
    # Enhanced language switching with user preference updates
    path('i18n/setlang/', set_language, name='set_language'),
    path('i18n/setlang-ajax/', set_language_ajax, name='set_language_ajax'),
    path('i18n/preferences/', get_user_language_preferences, name='user_language_preferences'),
    path('i18n/', include('django.conf.urls.i18n')),  # Keep for compatibility
    path('tinymce/', include('tinymce.urls')),
    path('tinymce/upload/', tinymce_upload_view, name='tinymce_upload'),
    path('', include('places.urls')),
    path('users/', include('users.urls')),
    path('reviews/', include('reviews.urls')),
    path('prayer/', include('prayer_times.urls')),
    path('blog/', include('blog.urls')),
    path('contact/', include('contact.urls')),
]

# Static and media files are typically not prefixed
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'places.views.handler404'
