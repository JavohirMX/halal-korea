import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from utils.turnstile import TurnstileField
from .models import User
from .utils import (
    DEFAULT_GREETING_TEMPLATE,
    DEFAULT_SIGNOFF,
    FROM_CHOICE_CONTACT,
    FROM_CHOICE_CUSTOM,
    FROM_CHOICE_NOREPLY,
    GREETING_CUSTOM,
    GREETING_HELLO,
    GREETING_HI,
    GREETING_NONE,
    GREETING_SALAM,
    resolve_from_email,
    resolve_greeting_template,
    validate_custom_from_address,
)

User = get_user_model()

BOOLEAN_FILTER_CHOICES = [
    ('', 'Any'),
    ('true', 'Yes'),
    ('false', 'No'),
]

# BigAutoField tops out at 2**63 - 1; anything beyond that is a malformed id,
# not a user that happens to be missing.
MAX_PK = 2**63 - 1

# Audience modes for the admin compose page. The picker is explicit so an admin
# always knows who a send will reach before confirming it.
AUDIENCE_MODE_ALL = 'all'
AUDIENCE_MODE_SEGMENT = 'segment'
AUDIENCE_MODE_USERS = 'users'
AUDIENCE_MODE_SINGLE = 'single'
AUDIENCE_MODE_MANUAL = 'manual'

# 'segment' is the safe landing default: it is a filtered send, never "everyone".
DEFAULT_AUDIENCE_MODE = AUDIENCE_MODE_SEGMENT

# Modes that fan out across the registered user base, and therefore need the
# typed-count interlock. "manual" is exempt: every address there was typed
# deliberately by the admin and it is not a blast at the user base.
BROADCAST_AUDIENCE_MODES = (
    AUDIENCE_MODE_ALL,
    AUDIENCE_MODE_SEGMENT,
    AUDIENCE_MODE_USERS,
)

AUDIENCE_MODE_CHOICES = [
    (AUDIENCE_MODE_ALL, 'All users'),
    (AUDIENCE_MODE_SEGMENT, 'Segment — filter by status, verification, language'),
    (AUDIENCE_MODE_USERS, 'Specific users — pick them by search'),
    (AUDIENCE_MODE_SINGLE, 'Single user'),
    (AUDIENCE_MODE_MANUAL, 'Manual addresses — type or paste emails'),
]

FROM_CHOICES = [
    (FROM_CHOICE_NOREPLY, 'No-reply'),
    (FROM_CHOICE_CONTACT, 'Contact'),
    (FROM_CHOICE_CUSTOM, 'Custom'),
]

GREETING_CHOICES = [
    (GREETING_HI, 'Hi {name},'),
    (GREETING_HELLO, 'Hello {name},'),
    (GREETING_SALAM, 'Assalamu alaikum {name},'),
    (GREETING_NONE, 'No greeting'),
    (GREETING_CUSTOM, 'Custom'),
]


def initial_audience_mode(user_id='', ids_param=''):
    """
    Derive the audience picker value from the legacy deep-link params.

    Keeps ?user_id=<pk> (change form) and ?ids=1,2,3 (changelist action)
    landing on the matching radio instead of the default segment.
    """
    if user_id:
        return AUDIENCE_MODE_SINGLE
    if ids_param:
        return AUDIENCE_MODE_USERS
    return DEFAULT_AUDIENCE_MODE


def parse_email_list(raw):
    """Split a comma/newline separated blob into (valid, invalid) address lists."""
    tokens = []
    for line in (raw or '').replace(',', '\n').splitlines():
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
    return valid, invalid


def parse_id_list(raw):
    """
    Split a blob of primary keys into (ids, invalid_tokens).

    Accepts commas and any whitespace as separators, so a pasted list of ids
    works the same way a pasted list of emails does. Values outside the range a
    BigAutoField can hold are reported invalid rather than passed to the ORM,
    where int too big would raise OverflowError during a preview.
    """
    if isinstance(raw, (list, tuple)):
        raw = ','.join(str(item) for item in raw)

    ids = []
    invalid = []
    seen = set()
    for token in re.split(r'[\s,]+', raw or ''):
        if not token:
            continue
        try:
            pk = int(token)
        except (TypeError, ValueError):
            invalid.append(token)
            continue
        if pk <= 0 or pk > MAX_PK:
            invalid.append(token)
            continue
        if pk in seen:
            continue
        seen.add(pk)
        ids.append(pk)
    return ids, invalid


class AdminEmailComposeForm(forms.Form):
    """Compose form for admin user emails (users + ad-hoc addresses)."""

    audience_mode = forms.ChoiceField(
        choices=AUDIENCE_MODE_CHOICES,
        required=False,
        initial=DEFAULT_AUDIENCE_MODE,
        label='Who should receive this email?',
        widget=forms.RadioSelect,
        help_text='Pick exactly one audience. Everything below adapts to your choice.',
    )
    from_choice = forms.ChoiceField(
        choices=FROM_CHOICES,
        required=False,
        initial=FROM_CHOICE_NOREPLY,
        label='From',
        widget=forms.RadioSelect,
        help_text='Brevo rejects a sender that is not verified on the account.',
    )
    custom_from_email = forms.CharField(
        required=False,
        label='Custom address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'id': 'id_custom_from_email',
            'placeholder': 'name@example.com',
            'autocomplete': 'off',
            'inputmode': 'email',
        }),
        help_text='Sent as Halal Korea <this address>. One address only.',
    )
    greeting_choice = forms.ChoiceField(
        choices=GREETING_CHOICES,
        required=False,
        initial=GREETING_HI,
        label='Greeting',
        widget=forms.RadioSelect,
        help_text='{name} becomes the recipient’s name, or “there” when there is no name.',
    )
    custom_greeting = forms.CharField(
        required=False,
        initial=DEFAULT_GREETING_TEMPLATE,
        label='Custom greeting',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_custom_greeting',
            'placeholder': 'Hi {name},',
        }),
    )
    signoff = forms.CharField(
        required=False,
        initial=DEFAULT_SIGNOFF,
        label='Closing',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'id': 'id_signoff',
            'rows': 3,
        }),
        help_text='Leave this empty to omit the closing.',
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email subject'}),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control compose-message',
            'rows': 10,
            'placeholder': 'Write your message…',
        }),
    )
    send_as_html = forms.BooleanField(
        required=False,
        initial=False,
        label='Send message as HTML',
        help_text=(
            'Formatting only. The body is sanitised before sending: scripts, '
            'images, iframes, forms, event handlers, relative links and most '
            'inline styles are stripped, and links are limited to http/https/mailto.'
        ),
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
    selected_user_ids = forms.CharField(
        required=False,
        label='Selected users',
        widget=forms.HiddenInput(attrs={'id': 'id_selected_user_ids'}),
    )
    user_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_user_id'}),
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
    confirm_send_count = forms.CharField(
        required=False,
        label='Confirm recipient count',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Type the recipient count to confirm',
            'autocomplete': 'off',
            'inputmode': 'numeric',
        }),
        help_text='Large sends must be confirmed by typing the exact number of recipients.',
    )

    def clean_from_choice(self):
        return self.cleaned_data.get('from_choice') or FROM_CHOICE_NOREPLY

    def clean_greeting_choice(self):
        return self.cleaned_data.get('greeting_choice') or GREETING_HI

    def clean_signoff(self):
        # A missing field keeps today's closing. A submitted blank closing is omitted.
        if 'signoff' not in self.data:
            return DEFAULT_SIGNOFF
        return self.cleaned_data.get('signoff') or ''

    def resolved_sender_kwargs(self):
        """Concrete from address, greeting template, and closing for a valid form."""
        data = self.cleaned_data
        greeting_choice = data.get('greeting_choice') or GREETING_HI
        custom_greeting = data.get('custom_greeting') if greeting_choice == GREETING_CUSTOM else None
        signoff = data['signoff'] if 'signoff' in data else DEFAULT_SIGNOFF
        return {
            'from_email': resolve_from_email(
                data.get('from_choice') or FROM_CHOICE_NOREPLY,
                data.get('custom_from_email'),
            ),
            'greeting_template': resolve_greeting_template(greeting_choice, custom_greeting),
            'signoff': signoff,
        }

    def clean_additional_emails(self):
        valid, invalid = parse_email_list(self.cleaned_data.get('additional_emails'))
        if invalid:
            raise ValidationError(
                'Invalid email address(es): %(emails)s',
                code='invalid',
                params={'emails': ', '.join(invalid)},
            )
        return valid

    def clean_selected_user_ids(self):
        raw = self.cleaned_data.get('selected_user_ids')
        ids, invalid = parse_id_list(raw)
        mode = self.data.get('audience_mode') or self.initial.get('audience_mode') or DEFAULT_AUDIENCE_MODE
        if invalid and mode == AUDIENCE_MODE_USERS:
            raise ValidationError(
                'Invalid user id(s): %(ids)s',
                code='invalid',
                params={'ids': ', '.join(invalid)},
            )
        return ids

    def clean_user_id(self):
        raw = (self.cleaned_data.get('user_id') or '').strip()
        if not raw:
            return ''
        mode = self.data.get('audience_mode') or self.initial.get('audience_mode') or DEFAULT_AUDIENCE_MODE
        try:
            return int(raw)
        except (TypeError, ValueError):
            if mode == AUDIENCE_MODE_SINGLE:
                raise ValidationError('Invalid user id.', code='invalid')
            return ''

    def clean(self):
        cleaned = super().clean()
        # Fall back to the deep-link-derived default so legacy POSTs (which never
        # send audience_mode) keep resolving to the mode their URL implied.
        mode = (
            cleaned.get('audience_mode')
            or self.initial.get('audience_mode')
            or DEFAULT_AUDIENCE_MODE
        )
        cleaned['audience_mode'] = mode

        def require(field, message):
            # _errors is already populated by _clean_fields at this point; reading
            # self.errors here would re-enter full_clean.
            if cleaned.get(field) or (self._errors and field in self._errors):
                return
            self.add_error(field, message)

        if mode == AUDIENCE_MODE_MANUAL:
            require('additional_emails', 'Enter at least one email address.')
        elif mode == AUDIENCE_MODE_USERS:
            require('selected_user_ids', 'Choose at least one user.')
        elif mode == AUDIENCE_MODE_SINGLE:
            require('user_id', 'Choose a user to email.')

        from_choice = cleaned.get('from_choice') or FROM_CHOICE_NOREPLY
        cleaned['from_choice'] = from_choice
        if from_choice == FROM_CHOICE_CUSTOM and not (self._errors and 'from_choice' in self._errors):
            error = validate_custom_from_address(cleaned.get('custom_from_email'))
            if error:
                self.add_error('custom_from_email', error)
            else:
                cleaned['custom_from_email'] = (cleaned.get('custom_from_email') or '').strip()

        cleaned['greeting_choice'] = cleaned.get('greeting_choice') or GREETING_HI
        return cleaned

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