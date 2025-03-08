from django.urls import path
from . import views

app_name = 'prayer_times'

urlpatterns = [
    path('', views.prayer_times, name='prayer_times'),
]
