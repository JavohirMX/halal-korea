from django.urls import path
from . import views

app_name = 'prayer_times'

urlpatterns = [
    path('', views.prayer_times, name='prayer_times'),
    path('get-prayer-times/', views.get_prayer_times_data, name='get_prayer_times'),
    path('get-location/', views.get_location_from_coords, name='get_location'),
    path('update-settings/', views.update_prayer_settings, name='update_settings'),
    path('update-location/', views.update_location, name='update_location'),
    path('clear-location/', views.clear_location, name='clear_location'),
    # Ramadan
    path('ramadan/', views.ramadan_timetable, name='ramadan_timetable'),
    path('ramadan/calendar-data/', views.get_ramadan_calendar_data, name='ramadan_calendar_data'),
    path('ramadan/download/', views.download_ramadan_image, name='ramadan_download_image'),
]
