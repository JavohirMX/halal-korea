import requests
import logging
from django.conf import settings
from typing import Optional, Dict, Any  # noqa: F401

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Utility class for sending Telegram notifications about place submissions
    """
    
    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
        self.enabled = getattr(settings, 'TELEGRAM_NOTIFICATIONS_ENABLED', False)
        
        if self.enabled and not (self.bot_token and self.chat_id):
            logger.warning("Telegram notifications are enabled but bot token or chat ID is missing")
            self.enabled = False
    
    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send a message to the configured Telegram chat
        
        Args:
            message (str): The message to send
            parse_mode (str): Parse mode for message formatting (HTML or Markdown)
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram notifications are disabled")
            return False
            
        if not (self.bot_token and self.chat_id):
            logger.error("Telegram bot token or chat ID not configured")
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info("Telegram notification sent successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram notification: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram notification: {str(e)}")
            return False
    
    def notify_new_place_submission(self, place_data: Dict[str, Any]) -> bool:
        """
        Send a notification about a new place submission
        
        Args:
            place_data (dict): Dictionary containing place information
                Required keys: name, category, address, submitted_by_username
                Optional keys: description, website, phone_number, photos_count
                
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Extract required data
            name = place_data.get('name', 'Unknown')
            category = place_data.get('category', 'Unknown')
            address = place_data.get('address', 'Unknown')
            submitted_by = place_data.get('submitted_by_username', 'Unknown')
            
            # Optional data
            description = place_data.get('description', '')
            website = place_data.get('website', '')
            phone = place_data.get('phone_number', '')
            photos_count = place_data.get('photos_count', 0)
            place_id = place_data.get('place_id', '')
            
            # Build the message
            message_parts = [
                "🔔 <b>New Place Submission!</b>",
                "",
                f"📍 <b>Name:</b> {name}",
                f"🏷️ <b>Category:</b> {category.title()}",
                f"📍 <b>Address:</b> {address}",
                f"👤 <b>Submitted by:</b> {submitted_by}",
            ]
            
            if description:
                # Truncate description if it's too long
                truncated_desc = description[:200] + "..." if len(description) > 200 else description
                message_parts.append(f"📝 <b>Description:</b> {truncated_desc}")
            
            if website:
                message_parts.append(f"🌐 <b>Website:</b> {website}")
                
            if phone:
                message_parts.append(f"📞 <b>Phone:</b> {phone}")
                
            if photos_count > 0:
                message_parts.append(f"📷 <b>Photos:</b> {photos_count} uploaded")
            
            if place_id:
                # If you have an admin URL for reviewing submissions, add it here
                admin_url = getattr(settings, 'SITE_URL', '') + f'/admin/places/halalplace/{place_id}/change/'
                message_parts.append(f"🔗 <b>Review:</b> <a href='{admin_url}'>Admin Panel</a>")
            
            message_parts.extend([
                "",
                "⏳ <i>Status: Pending Review</i>"
            ])
            
            message = '\n'.join(message_parts)
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error formatting place submission notification: {str(e)}")
            return False


# Convenience functions for easy import
def send_new_place_notification(place_data: Dict[str, Any]) -> bool:
    """
    Convenience function to send a new place submission notification
    
    Args:
        place_data (dict): Dictionary containing place information
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    notifier = TelegramNotifier()
    return notifier.notify_new_place_submission(place_data)


def send_telegram_notification(message: str, parse_mode: str = 'HTML') -> bool:
    """
    Convenience function to send a plain text message via Telegram
    
    Args:
        message (str): The message to send
        parse_mode (str): Parse mode for message formatting (HTML or Markdown)
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    notifier = TelegramNotifier()
    return notifier.send_message(message, parse_mode) 