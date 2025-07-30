from django import forms
from django.contrib.gis.geos import Point
from .models import HalalPlace, PlaceEditSuggestion, PlaceImageSuggestion

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


class PlaceSuggestionForm(forms.Form):
    """
    Combined form for suggesting edits to a place.
    Users can suggest changes to multiple fields and upload images in one submission.
    """
    # Field edit suggestions
    suggest_name = forms.BooleanField(required=False, label="Suggest name change")
    name = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
        'placeholder': 'Enter new name'
    }))
    
    suggest_description = forms.BooleanField(required=False, label="Suggest description change")
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
        'rows': 4,
        'placeholder': 'Enter new description'
    }))
    
    suggest_category = forms.BooleanField(required=False, label="Suggest category change")
    category = forms.ChoiceField(choices=HalalPlace.CATEGORY_CHOICES, required=False, widget=forms.Select(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500'
    }))
    
    suggest_address = forms.BooleanField(required=False, label="Suggest address change")
    address = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
        'placeholder': 'Enter new address'
    }))
    
    suggest_phone_number = forms.BooleanField(required=False, label="Suggest phone number change")
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
        'placeholder': 'Enter new phone number'
    }))
    
    suggest_website = forms.BooleanField(required=False, label="Suggest website change")
    website = forms.URLField(required=False, widget=forms.URLInput(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
        'placeholder': 'Enter new website URL'
    }))
    
    suggest_google_map_link = forms.BooleanField(required=False, label="Suggest Google Map link change")
    google_map_link = forms.URLField(required=False, widget=forms.URLInput(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
        'placeholder': 'Enter new Google Map link'
    }))
    
    suggest_kakao_map_link = forms.BooleanField(required=False, label="Suggest Kakao Map link change")
    kakao_map_link = forms.URLField(required=False, widget=forms.URLInput(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
        'placeholder': 'Enter new Kakao Map link'
    }))
    
    suggest_naver_map_link = forms.BooleanField(required=False, label="Suggest Naver Map link change")
    naver_map_link = forms.URLField(required=False, widget=forms.URLInput(attrs={
        'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
        'placeholder': 'Enter new Naver Map link'
    }))
    
    suggest_location = forms.BooleanField(required=False, label="Suggest location change")
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    
    # Note: Multiple images will be handled in the view by processing request.FILES.getlist('images')
    images = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100'
        }),
        help_text="Select images to add to this place"
    )
    
    # Overall reason for suggestions
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
            'rows': 3,
            'placeholder': 'Please explain why these changes are needed...'
        }),
        help_text="Please explain why these changes or additions are needed"
    )
    
    def __init__(self, place=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.place = place
        
        # If place is provided, set current values as placeholders
        if place:
            self.fields['name'].widget.attrs['placeholder'] = f'Current: {place.name}'
            self.fields['description'].widget.attrs['placeholder'] = f'Current: {place.description[:50]}...'
            self.fields['address'].widget.attrs['placeholder'] = f'Current: {place.address}'
            if place.phone_number:
                self.fields['phone_number'].widget.attrs['placeholder'] = f'Current: {place.phone_number}'
            if place.website:
                self.fields['website'].widget.attrs['placeholder'] = f'Current: {place.website}'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if at least one suggestion is being made
        field_suggestions = any([
            cleaned_data.get('suggest_name'),
            cleaned_data.get('suggest_description'),
            cleaned_data.get('suggest_category'),
            cleaned_data.get('suggest_address'),
            cleaned_data.get('suggest_phone_number'),
            cleaned_data.get('suggest_website'),
            cleaned_data.get('suggest_google_map_link'),
            cleaned_data.get('suggest_kakao_map_link'),
            cleaned_data.get('suggest_naver_map_link'),
            cleaned_data.get('suggest_location')
        ])
        
        has_images = cleaned_data.get('images')  # Note: Multiple files will be checked in the view
        
        if not field_suggestions and not has_images:
            raise forms.ValidationError("Please suggest at least one change or upload an image.")
        
        # Validate that when a field is suggested, its value is provided
        field_mappings = [
            ('suggest_name', 'name'),
            ('suggest_description', 'description'),
            ('suggest_category', 'category'),
            ('suggest_address', 'address'),
            ('suggest_phone_number', 'phone_number'),
            ('suggest_website', 'website'),
            ('suggest_google_map_link', 'google_map_link'),
            ('suggest_kakao_map_link', 'kakao_map_link'),
            ('suggest_naver_map_link', 'naver_map_link'),
        ]
        
        for suggest_field, value_field in field_mappings:
            if cleaned_data.get(suggest_field) and not cleaned_data.get(value_field):
                raise forms.ValidationError(f"Please provide a new value for {value_field.replace('_', ' ')}.")
        
        # Validate location suggestion
        if cleaned_data.get('suggest_location'):
            if not (cleaned_data.get('latitude') and cleaned_data.get('longitude')):
                raise forms.ValidationError("Please provide both latitude and longitude for location change.")
        
        return cleaned_data
    
    def get_field_suggestions(self):
        """Return a list of field suggestions to create"""
        if not self.is_valid():
            return []
        
        suggestions = []
        cleaned_data = self.cleaned_data
        
        field_mappings = [
            ('suggest_name', 'name'),
            ('suggest_description', 'description'),
            ('suggest_category', 'category'),
            ('suggest_address', 'address'),
            ('suggest_phone_number', 'phone_number'),
            ('suggest_website', 'website'),
            ('suggest_google_map_link', 'google_map_link'),
            ('suggest_kakao_map_link', 'kakao_map_link'),
            ('suggest_naver_map_link', 'naver_map_link'),
        ]
        
        for suggest_field, value_field in field_mappings:
            if cleaned_data.get(suggest_field):
                current_value = getattr(self.place, value_field) if self.place else ""
                suggestions.append({
                    'field_name': value_field,
                    'current_value': str(current_value) if current_value else "",
                    'suggested_value': str(cleaned_data[value_field]),
                    'reason': cleaned_data['reason']
                })
        
        # Handle location suggestion specially
        if cleaned_data.get('suggest_location'):
            current_location = f"{self.place.location.y},{self.place.location.x}" if self.place and self.place.location else ""
            new_location = f"{cleaned_data['latitude']},{cleaned_data['longitude']}"
            suggestions.append({
                'field_name': 'location',
                'current_value': current_location,
                'suggested_value': new_location,
                'reason': cleaned_data['reason']
            })
        
        return suggestions


class PlaceImageSuggestionForm(forms.ModelForm):
    """Form for individual image suggestions"""
    
    class Meta:
        model = PlaceImageSuggestion
        fields = ['image', 'caption']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100'
            }),
            'caption': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500',
                'placeholder': 'Optional caption for this image'
            })
        } 