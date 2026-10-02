from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from utils.turnstile import TurnstileField
from .models import User

User = get_user_model()

BOOLEAN_FILTER_CHOICES = [
    ('', 'Any'),
    ('true', 'Yes'),
    ('false', 'No'),
]


class AdminEmailComposeForm(forms.Form):
    """Compose form for admin user emails (users + ad-hoc addresses)."""

    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email subject'}),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Write your message…',
        }),
    )
    send_as_html = forms.BooleanField(
        required=False,
        initial=False,
        label='Send message as HTML',
        help_text='If checked, the message body is treated as HTML inside the branded template.',
    )
    additional_emails = forms.CharField(
        required=False,
        label='Additional emails',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Comma- or newline-separated addresses (not required to be registered users)',
        }),
        help_text='Optional. Addresses that are not required to be registered users.',
    )
    filter_is_active = forms.ChoiceField(
        required=False,
        choices=BOOLEAN_FILTER_CHOICES,
        label='Active users',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    filter_email_verified = forms.ChoiceField(
        required=False,
        choices=BOOLEAN_FILTER_CHOICES,
        label='Email verified',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    filter_preferred_language = forms.ChoiceField(
        required=False,
        choices=[('', 'Any language')] + list(User.LANGUAGE_CHOICES),
        label='Preferred language',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    include_staff = forms.BooleanField(
        required=False,
        initial=False,
        label='Include staff users',
        help_text='When unchecked, staff accounts are excluded from filtered broadcasts.',
    )
    confirm_large_send = forms.BooleanField(
        required=False,
        initial=False,
        label='Confirm send to more than 50 recipients',
    )

    def clean_additional_emails(self):
        raw = self.cleaned_data.get('additional_emails') or ''
        if not raw.strip():
            return []

        tokens = []
        for line in raw.replace(',', '\n').splitlines():
            token = line.strip()
            if token:
                tokens.append(token)

        valid = []
        invalid = []
        seen = set()
        for token in tokens:
            try:
                validate_email(token)
            except ValidationError:
                invalid.append(token)
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            valid.append(token)

        if invalid:
            raise ValidationError(
                'Invalid email address(es): %(emails)s',
                code='invalid',
                params={'emails': ', '.join(invalid)},
            )
        return valid

class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional')
    email = forms.EmailField()
    captcha = TurnstileField(action="register")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'preferred_language']
        
    def clean_preferred_language(self):
        language = self.cleaned_data.get('preferred_language')
        if language not in dict(User.LANGUAGE_CHOICES):
            raise forms.ValidationError('Invalid language choice')
        return language


class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset via email"""
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'block w-full h-12 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 transition duration-200 ease-in-out placeholder-gray-400',
            'placeholder': 'Enter your email address'
        })
    )
    captcha = TurnstileField(action="password_reset")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Always return the email - we don't reveal if it exists or not for security
            return email.lower().strip()
        return email


class PasswordResetConfirmForm(SetPasswordForm):
    """Form for setting new password after reset"""
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full h-12 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 transition duration-200 ease-in-out placeholder-gray-400',
            'placeholder': 'Enter your new password'
        }),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full h-12 rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 transition duration-200 ease-in-out placeholder-gray-400',
            'placeholder': 'Confirm your new password'
        }),
    )