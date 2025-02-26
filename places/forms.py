from django import forms
from .models import HalalPlace

class HalalPlaceForm(forms.ModelForm):
    # Add hidden fields for latitude and longitude
    latitude = forms.FloatField(widget=forms.HiddenInput())
    longitude = forms.FloatField(widget=forms.HiddenInput())
    
    class Meta:
        model = HalalPlace
        fields = [
            'name', 'description', 'category', 
            'address', 'phone_number', 'website',
            'google_map_link', 'kakao_map_link', 'naver_map_link',
            'latitude', 'longitude'
        ] 