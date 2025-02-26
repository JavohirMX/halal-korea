from django.urls import path
from . import views

app_name = 'places'

urlpatterns = [
    path('', views.home, name='home'),
    path('explore/', views.explore, name='explore'),
    path('place/<int:pk>/', views.place_detail, name='place_detail'),
    path('submit/', views.submit_place, name='submit_place'),
    path('about/', views.about, name='about'),
]
