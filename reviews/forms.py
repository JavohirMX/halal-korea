from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is None or not (1 <= rating <= 5):
            raise forms.ValidationError('Rating must be between 1 and 5')
        return rating
        
    def clean_comment(self):
        comment = self.cleaned_data.get('comment', '').strip()
        if not comment:
            raise forms.ValidationError('Comment is required')
        return comment 