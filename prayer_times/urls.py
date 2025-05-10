from django.urls import path
from . import views

app_name = 'prayer_times'

urlpatterns = [
    path('', views.prayer_times, name='prayer_times'),
    path('get-prayer-times/', views.get_prayer_times_data, name='get_prayer_times'),
    path('get-location/', views.get_location_from_coords, name='get_location'),
    path('update-settings/', views.update_prayer_settings, name='update_settings'),
    path('update-location/', views.update_location, name='update_location'),
]
