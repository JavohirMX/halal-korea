"""
Rosetta Access Control for Halal Korea Translation Management

This module defines who can access the Rosetta translation interface.
By default, only superusers and staff members with translation permissions
can access the translation management interface.

Author: Halal Korea Development Team
Created: 2025-01-22
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


def has_rosetta_access(user):
    """
    Determine if a user has access to Rosetta translation interface.
    
    Access is granted to:
    1. Superusers (full access)
    2. Staff members with translation permissions
    3. Users in the 'Translators' group (if exists)
    
    Args:
        user: Django user object
        
    Returns:
        bool: True if user should have access to Rosetta
    """
    if not user.is_authenticated:
        return False
    
    # Superusers always have access
    if user.is_superuser:
        return True
    
    # Staff members with specific permissions
    if user.is_staff:
        # Check for translation-related permissions
        translation_permissions = [
            'change_translation',
            'add_translation',
            'view_translation',
        ]
        
        # Check if user has any translation permissions
        for perm in translation_permissions:
            if user.has_perm(f'rosetta.{perm}'):
                return True
    
    # Check for membership in Translators group
    if user.groups.filter(name='Translators').exists():
        return True
    
    # Check for custom permission
    if user.has_perm('utils.can_manage_translations'):
        return True
    
    return False


def create_translator_permissions():
    """
    Create custom permissions for translation management.
    
    This function can be called from a data migration or management command
    to set up the necessary permissions for translation management.
    """
    # Get the content type for the utils app (or create custom content type)
    try:
        from django.contrib.auth.models import Group
        
        # Create Translators group if it doesn't exist
        translators_group, created = Group.objects.get_or_create(name='Translators')
        
        if created:
            print("Created 'Translators' group for translation management")
        
        # You can add specific permissions here as needed
        # For example, create custom permissions for translation management
        
        return translators_group
        
    except Exception as e:
        print(f"Error creating translator permissions: {e}")
        return None


def setup_translation_access():
    """
    Set up translation access for the project.
    
    This function configures the necessary groups and permissions
    for translation management in the Halal Korea project.
    """
    try:
        # Create the translators group
        translators_group = create_translator_permissions()
        
        # Additional setup can be done here
        # For example, assign specific users to the translators group
        
        print("Translation access setup completed successfully")
        
    except Exception as e:
        print(f"Error setting up translation access: {e}")


# Instructions for adding users to translation management:
"""
To grant translation access to a user:

1. Via Django Admin:
   - Go to /admin/auth/user/
   - Edit the user
   - Add them to the 'Translators' group
   - Or give them staff status with appropriate permissions

2. Via Django Shell:
   from django.contrib.auth.models import User, Group
   user = User.objects.get(username='translator_username')
   translators = Group.objects.get(name='Translators')
   user.groups.add(translators)

3. Via Management Command:
   python manage.py shell -c "
   from config.rosetta_permissions import setup_translation_access
   setup_translation_access()
   "
"""
