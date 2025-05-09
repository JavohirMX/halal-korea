from django import forms
from .models import HalalPlace
from django.contrib.gis.geos import Point

class HalalPlaceForm(forms.ModelForm):
    # Add hidden fields for latitude and longitude that will be combined into location
    latitude = forms.FloatField(widget=forms.HiddenInput())
    longitude = forms.FloatField(widget=forms.HiddenInput())
    
    class Meta:
        model = HalalPlace
        fields = [
            'name', 'description', 'category', 
            'address', 'phone_number', 'website',
            'google_map_link', 'kakao_map_link', 'naver_map_link',
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if latitude is not None and longitude is not None:
            cleaned_data['location'] = Point(longitude, latitude)
        
        return cleaned_data 