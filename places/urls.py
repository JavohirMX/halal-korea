from django.urls import path
from . import views

app_name = 'places'

urlpatterns = [
    path('', views.home, name='home'),
    path('explore/', views.explore, name='explore'),
    path('place/<int:pk>/', views.place_detail, name='place_detail'),
    path('submit/', views.submit_place, name='submit_place'),
    path('about/', views.about, name='about'),
    path('donate/', views.donate, name='donate'),
    path('legal/', views.legal, name='legal'),
    path('set-location/', views.set_location, name='set_location'),
    path('api/places/', views.get_places_json, name='places_json'),
]
