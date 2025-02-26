from django.db import models
from django.contrib.auth.models import AbstractUser

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
    
    preferred_language = models.CharField(max_length=10, choices=[
        ('EN', 'English'),
        ('KR', 'Korean'),
        ('UZ', 'Uzbek'),
    ], default='EN')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)