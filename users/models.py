from django.contrib.auth.models import AbstractUser
from django.db import models

# User model
class User(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    
    # Name fields
    first_name = models.CharField(max_length=30, blank=True, help_text="User's first name")
    last_name = models.CharField(max_length=30, blank=True, help_text="User's last name")
    
    created_at = models.DateTimeField(auto_now_add=True)
    favorite_places = models.ManyToManyField(
        'places.HalalPlace',
        related_name='favorited_by',
        blank=True
    )
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ko', '한국어'),
        ('uz', "O'zbek"),
    ]
    preferred_language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    email_verified = models.BooleanField(default=False, help_text="Whether the user has verified their email address")
    
    # Social authentication fields
    profile_picture = models.ImageField(
        upload_to='users/profile_pictures/', 
        blank=True, 
        null=True,
        help_text="User's profile picture from social providers or uploaded manually"
    )
    social_avatar_url = models.URLField(
        blank=True, 
        null=True,
        help_text="URL to user's avatar from social providers"
    )
    
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def avatar_url(self):
        """Return the user's avatar URL (profile picture or social avatar)."""
        if self.profile_picture:
            return self.profile_picture.url
        elif self.social_avatar_url:
            return self.social_avatar_url
        return None

    def get_social_accounts(self):
        """Get all linked social accounts for this user."""
        try:
            from allauth.socialaccount.models import SocialAccount
            return SocialAccount.objects.filter(user=self)
        except ImportError:
            return []

    class Meta:
        db_table = 'users_user'  # Explicitly set the table name