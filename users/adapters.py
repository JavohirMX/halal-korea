"""
Custom Django AllAuth adapters for Halal Korea
Handles account merging, profile data import, and social authentication logic
"""

import logging
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from allauth.account.utils import user_email, user_username
import requests
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter to integrate with existing user system
    """
    
    def is_open_for_signup(self, request):
        """
        Allow signups (integrate with existing registration system)
        """
        return True
    
    def save_user(self, request, user, form, commit=True):
        """
        Save user with integration to existing system
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Set email as verified for social accounts (handled in social adapter)
        # Regular signups will use existing email verification system
        
        if commit:
            user.save()
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for auto-merging accounts and profile data import
    """
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Allow social signups
        """
        return True
    
    def pre_social_login(self, request, sociallogin):
        """
        Handle account merging before social login
        Auto-merge accounts with matching email addresses
        """
        if sociallogin.is_existing:
            return
        
        # Get email from social account
        email = user_email(sociallogin.user)
        if not email:
            logger.warning(f"No email provided by {sociallogin.account.provider} for user")
            return
        
        try:
            # Check if user with this email already exists
            existing_user = User.objects.get(email__iexact=email)
            
            # Check if this social account is already connected to another user
            if SocialAccount.objects.filter(
                provider=sociallogin.account.provider,
                uid=sociallogin.account.uid
            ).exclude(user=existing_user).exists():
                logger.warning(f"Social account {sociallogin.account.provider}:{sociallogin.account.uid} already connected to different user")
                return
            
            # Auto-merge: connect social account to existing user
            sociallogin.connect(request, existing_user)
            logger.info(f"Auto-merged {sociallogin.account.provider} account with existing user {existing_user.username}")
            
        except User.DoesNotExist:
            # No existing user with this email, proceed with normal signup
            pass
        except Exception as e:
            logger.error(f"Error during account merging: {str(e)}")
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save user with social account data and profile picture
        """
        user = sociallogin.user
        
        # Import basic profile data
        self._import_profile_data(sociallogin, user)
        
        # Set email as verified for trusted providers
        if sociallogin.account.provider in ['google', 'github']:
            user.email_verified = True
            logger.info(f"Email auto-verified for {sociallogin.account.provider} user {user.username}")
        
        user.save()
        
        # Import profile picture after user is saved
        self._import_profile_picture(sociallogin, user)
        
        return user
    
    def _import_profile_data(self, sociallogin, user):
        """
        Import profile data from social providers
        """
        provider = sociallogin.account.provider
        extra_data = sociallogin.account.extra_data
        
        try:
            # Import name data
            if provider == 'google':
                user.first_name = extra_data.get('given_name', '')[:30]
                user.last_name = extra_data.get('family_name', '')[:30]
            elif provider == 'github':
                name = extra_data.get('name', '')
                if name:
                    name_parts = name.split(' ', 1)
                    user.first_name = name_parts[0][:30]
                    if len(name_parts) > 1:
                        user.last_name = name_parts[1][:30]
            
            # Set username if not already set
            if not user.username:
                username = user_username(sociallogin.user)
                if username:
                    user.username = username
            
            logger.info(f"Imported profile data from {provider} for user {user.username}")
            
        except Exception as e:
            logger.error(f"Error importing profile data from {provider}: {str(e)}")
    
    def _import_profile_picture(self, sociallogin, user):
        """
        Import profile picture from social providers
        """
        provider = sociallogin.account.provider
        extra_data = sociallogin.account.extra_data
        picture_url = None
        
        try:
            # Get profile picture URL based on provider
            if provider == 'google':
                picture_url = extra_data.get('picture')
            elif provider == 'github':
                picture_url = extra_data.get('avatar_url')
            
            if picture_url:
                # Store the URL for immediate use
                user.social_avatar_url = picture_url
                user.save()
                
                # Download and save the image
                self._download_and_save_avatar(user, picture_url, provider)
                
                logger.info(f"Imported profile picture from {provider} for user {user.username}")
            
        except Exception as e:
            logger.error(f"Error importing profile picture from {provider}: {str(e)}")
    
    def _download_and_save_avatar(self, user, picture_url, provider):
        """
        Download and save profile picture from URL
        """
        try:
            response = requests.get(picture_url, timeout=10)
            response.raise_for_status()
            
            # Open image and convert to RGB (handles various formats)
            image = Image.open(BytesIO(response.content))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize image to reasonable size (max 400x400)
            image.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            # Save as JPEG
            output = BytesIO()
            image.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            # Generate filename
            filename = f"{user.username}_{provider}_avatar.jpg"
            
            # Save to user's profile_picture field
            user.profile_picture.save(
                filename,
                ContentFile(output.getvalue()),
                save=True
            )
            
            logger.info(f"Downloaded and saved avatar for user {user.username} from {provider}")
            
        except Exception as e:
            logger.error(f"Error downloading avatar from {provider} for user {user.username}: {str(e)}")
    
    def populate_username(self, request, user):
        """
        Generate username for social accounts
        """
        username = user_username(user)
        if not username:
            # Generate username from email or social account data
            email = user_email(user)
            if email:
                username = email.split('@')[0]
            else:
                username = f"user_{user.pk}"
        
        # Ensure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        
        user_username(user, username)
        return username
