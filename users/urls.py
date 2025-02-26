from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>/', views.profile, name='profile_detail'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('favorite/toggle/<int:place_id>/', views.toggle_favorite, name='toggle_favorite'),
]
