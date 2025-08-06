from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    path('submit/', views.submit_contact_form, name='submit_form'),
    path('form/', views.get_contact_form_html, name='get_form_html'),
    path('rate-limited/', views.rate_limited_view, name='rate_limited'),
]
