import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.html import conditional_escape, format_html

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    'critical': '🚨',
    'warning': '⚠️',
    'info': 'ℹ️',
}

SEVERITY_BADGE = {
    'critical': 'CRITICAL',
    'warning': 'WARNING',
    'info': 'INFO',
}


def _normalize_severity(severity: Optional[str]) -> str:
    """Map rule/alert severities onto critical/warning/info."""
    if not severity:
        return 'info'
    severity = severity.lower()
    if severity in ('critical', 'high'):
        return 'critical' if severity == 'critical' else 'warning'
    if severity in ('warning', 'medium'):
        return 'warning'
    if severity in ('info', 'low'):
        return 'info'
    return 'info'


def _environment_slug() -> str:
    return getattr(settings, 'ENVIRONMENT', 'development') or 'development'


def _format_timestamp(when: Optional[datetime] = None) -> str:
    """Timezone-aware timestamp labeled with local tz abbreviation (e.g. KST)."""
    when = when or timezone.now()
    if timezone.is_naive(when):
        when = timezone.make_aware(when, timezone.get_current_timezone())
    local = timezone.localtime(when)
    tz_name = local.tzname() or 'UTC'
    return f"{local.strftime('%Y-%m-%d %H:%M')} {tz_name}"


def _build_hashtags(
    category: str,
    severity: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    tags = ['#halalkorea', f'#{category}']
    if severity:
        tags.append(f'#{_normalize_severity(severity)}')
    env = environment or _environment_slug()
    # Hashtags can't have spaces/hyphens — collapse to alphanumeric
    env_tag = ''.join(ch for ch in env.lower() if ch.isalnum() or ch == '_')
    if env_tag:
        tags.append(f'#{env_tag}')
    return ' '.join(tags)


def format_telegram_message(
    title: str,
    body_lines: Optional[Sequence[str]] = None,
    *,
    severity: str = 'info',
    category: str = 'monitoring',
    link: Optional[str] = None,
    link_text: str = 'Open dashboard',
    timestamp: Optional[datetime] = None,
    escape_body: bool = True,
) -> str:
    """
    Build a consistent HTML Telegram message with severity badge, environment,
    timestamp, optional admin link, and hashtag footer.

    Args:
        title: Message title (plain text; escaped).
        body_lines: Bullet / detail lines (escaped unless escape_body=False).
        severity: critical | warning | info (also accepts high/medium/low).
        category: Hashtag category (monitoring, places, contact, …).
        link: Absolute or site-relative URL for the deep link.
        link_text: Anchor text for the link.
        timestamp: Optional datetime; defaults to now.
        escape_body: Escape body lines for HTML safety.
    """
    sev = _normalize_severity(severity)
    emoji = SEVERITY_EMOJI.get(sev, 'ℹ️')
    badge = SEVERITY_BADGE.get(sev, 'INFO')
    env = _environment_slug()
    ts = _format_timestamp(timestamp)

    safe_title = conditional_escape(title)
    safe_env = conditional_escape(env)
    safe_ts = conditional_escape(ts)
    header = (
        f"{emoji} <b>{safe_title}</b>\n"
        f"<code>{badge}</code> · {safe_env} · {safe_ts}"
    )

    parts: List[str] = [header, '']

    if body_lines:
        for line in body_lines:
            if line is None:
                continue
            text = str(line)
            if escape_body:
                text = str(conditional_escape(text))
            # Preserve leading blank lines / preformatted bullets
            if text.startswith('•') or text.startswith('-') or text.startswith(' '):
                parts.append(text)
            elif text == '':
                parts.append('')
            else:
                parts.append(f'• {text}')

    if link:
        site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        href = link if link.startswith(('http://', 'https://')) else f'{site_url}{link}'
        if href:
            parts.append('')
            parts.append(
                str(format_html(
                    '🔗 <a href="{}">{}</a>',
                    href,
                    link_text,
                ))
            )

    parts.append('')
    parts.append(_build_hashtags(category, sev, env))

    return '\n'.join(parts)


class TelegramNotifier:
    """
    Utility class for sending Telegram notifications about place submissions
    """

    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
        self.enabled = getattr(settings, 'TELEGRAM_NOTIFICATIONS_ENABLED', False)
        # Local Telegram Bot API URL (removes 50MB limit for file uploads)
        self.api_base_url = getattr(settings, 'TELEGRAM_API_BASE_URL', 'http://telegram-bot-api:8081')

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

        url = f"{self.api_base_url}/bot{self.bot_token}/sendMessage"

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
            name = place_data.get('name', 'Unknown')
            category = place_data.get('category', 'Unknown')
            address = place_data.get('address', 'Unknown')
            submitted_by = place_data.get('submitted_by_username', 'Unknown')

            description = place_data.get('description', '')
            website = place_data.get('website', '')
            phone = place_data.get('phone_number', '')
            photos_count = place_data.get('photos_count', 0)
            place_id = place_data.get('place_id', '')

            body_lines = [
                f"📍 Name: {name}",
                f"🏷️ Category: {str(category).title()}",
                f"📍 Address: {address}",
                f"👤 Submitted by: {submitted_by}",
            ]

            if description:
                truncated_desc = description[:200] + "..." if len(description) > 200 else description
                body_lines.append(f"📝 Description: {truncated_desc}")

            if website:
                body_lines.append(f"🌐 Website: {website}")

            if phone:
                body_lines.append(f"📞 Phone: {phone}")

            if photos_count > 0:
                body_lines.append(f"📷 Photos: {photos_count} uploaded")

            body_lines.append('')
            body_lines.append('⏳ Status: Pending Review')

            link = None
            if place_id:
                link = f'/admin/places/halalplace/{place_id}/change/'

            message = format_telegram_message(
                'New Place Submission!',
                body_lines,
                severity='info',
                category='places',
                link=link,
                link_text='Review in Admin',
            )

            return self.send_message(message)

        except Exception as e:
            logger.error(f"Error formatting place submission notification: {str(e)}")
            return False

    def notify_contact_message(self, contact_data: Dict[str, Any]) -> bool:
        """
        Send a notification about a new contact form submission

        Args:
            contact_data (dict): Dictionary containing contact information
                Required keys: name, email, message
                Optional keys: subject, user_type, user_id

        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            name = contact_data.get('name', 'Unknown')
            email = contact_data.get('email', 'Unknown')
            message = contact_data.get('message', '')

            subject = contact_data.get('subject', '')
            user_type = contact_data.get('user_type', 'Anonymous')
            user_id = contact_data.get('user_id', '')

            body_lines = [
                f"👤 Name: {name}",
                f"📧 Email: {email}",
                f"🆔 User Type: {user_type}",
            ]

            if user_id:
                body_lines.append(f"🔢 User ID: {user_id}")

            if subject:
                body_lines.append(f"📋 Subject: {subject}")

            truncated_message = message[:500] + "..." if len(message) > 500 else message
            body_lines.append('')
            body_lines.append(f"💬 Message: {truncated_message}")
            body_lines.append('')
            body_lines.append('📧 Please reply to the user\'s email address')

            notification_message = format_telegram_message(
                'New Contact Message!',
                body_lines,
                severity='info',
                category='contact',
            )

            return self.send_message(notification_message)

        except Exception as e:
            logger.error(f"Error formatting contact message notification: {str(e)}")
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


# Alias used by AlertRule Telegram path (and any older callers)
send_telegram_message = send_telegram_notification


def send_contact_message_notification(contact_data: Dict[str, Any]) -> bool:
    """
    Convenience function to send a contact form submission notification

    Args:
        contact_data (dict): Dictionary containing contact information

    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    notifier = TelegramNotifier()
    return notifier.notify_contact_message(contact_data)
