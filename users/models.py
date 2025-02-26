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
    
    created_at = models.DateTimeField(auto_now_add=True)
    favorite_places = models.ManyToManyField(
        'places.HalalPlace',
        related_name='favorited_by',
        blank=True
    )
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ko', 'Korean'),
        ('uz', 'Uzbek'),
    ]
    preferred_language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_user'  # Explicitly set the table name