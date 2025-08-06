from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('resend-activation/', views.resend_activation_email, name='resend_activation'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.profile, name='user_profile'),
    path('profile/', views.profile, name='profile'),
    path('favorite/toggle/<int:place_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('toggle-favorite/<int:place_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('rate-limited/', views.rate_limited_view, name='rate_limited'),
]
