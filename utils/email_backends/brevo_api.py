"""
Brevo (Sendinblue) HTTPS REST API Email Backend.

Sends transactional emails via Brevo v3 API (POST https://api.brevo.com/v3/smtp/email)
over HTTPS (port 443). This bypasses ISP and cloud host SMTP port blocks (such as
DigitalOcean's egress block on ports 25, 465, 587, and 2525).
"""
import base64
import email.utils
from email.mime.base import MIMEBase
import logging
import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address

logger = logging.getLogger(__name__)

BREVO_API_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


class BrevoAPIBackend(BaseEmailBackend):
    """
    Transactional email backend that communicates with Brevo REST API over HTTPS.
    """

    def __init__(self, api_key=None, endpoint=None, timeout=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = (
                getattr(settings, "BREVO_API_KEY", None)
                or getattr(settings, "EMAIL_HOST_PASSWORD", None)
                or ""
            ).strip()
        self.endpoint = endpoint or getattr(settings, "BREVO_API_ENDPOINT", BREVO_API_ENDPOINT)
        self.timeout = timeout or getattr(settings, "EMAIL_TIMEOUT", 15)

    def _parse_address(self, address_str):
        """Parse a RFC 2822 address string into Brevo's {email, name} structure."""
        if not address_str:
            return None
        display_name, email_address = email.utils.parseaddr(address_str)
        email_address = email_address.strip()
        if not email_address:
            return None
        data = {"email": email_address}
        if display_name.strip():
            data["name"] = display_name.strip()
        return data

    def _build_payload(self, message):
        """Convert a Django EmailMessage into a Brevo v3 API payload dict."""
        # Sender
        from_email = message.from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@halal-korea.com")
        sender = self._parse_address(from_email)
        if not sender:
            sender = {"email": from_email.strip()}

        # To recipients
        to_list = [self._parse_address(addr) for addr in (message.to or []) if self._parse_address(addr)]
        if not to_list:
            return None

        payload = {
            "sender": sender,
            "to": to_list,
            "subject": message.subject or "",
        }

        # CC / BCC
        if getattr(message, "cc", None):
            cc_list = [self._parse_address(addr) for addr in message.cc if self._parse_address(addr)]
            if cc_list:
                payload["cc"] = cc_list

        if getattr(message, "bcc", None):
            bcc_list = [self._parse_address(addr) for addr in message.bcc if self._parse_address(addr)]
            if bcc_list:
                payload["bcc"] = bcc_list

        # Reply-To
        if getattr(message, "reply_to", None) and len(message.reply_to) > 0:
            parsed_reply = self._parse_address(message.reply_to[0])
            if parsed_reply:
                payload["replyTo"] = parsed_reply

        # Content (Plain text / HTML)
        html_content = None
        text_content = message.body or ""

        if getattr(message, "content_subtype", None) == "html":
            html_content = message.body
            text_content = ""
        elif hasattr(message, "alternatives"):
            for content, mimetype in message.alternatives:
                if mimetype == "text/html":
                    html_content = content
                    break

        if html_content:
            payload["htmlContent"] = html_content
        if text_content:
            payload["textContent"] = text_content

        # Custom headers
        if getattr(message, "extra_headers", None):
            payload["headers"] = dict(message.extra_headers)

        # Attachments
        if getattr(message, "attachments", None):
            attachments_payload = []
            for attachment in message.attachments:
                try:
                    if isinstance(attachment, MIMEBase):
                        filename = attachment.get_filename() or "attachment"
                        raw_payload = attachment.get_payload(decode=True)
                        content_b64 = base64.b64encode(raw_payload).decode("ascii")
                    elif isinstance(attachment, tuple) and len(attachment) >= 2:
                        filename = attachment[0] or "attachment"
                        raw_content = attachment[1]
                        if isinstance(raw_content, str):
                            content_b64 = base64.b64encode(raw_content.encode("utf-8")).decode("ascii")
                        else:
                            content_b64 = base64.b64encode(raw_content).decode("ascii")
                    else:
                        continue
                    attachments_payload.append({
                        "name": filename,
                        "content": content_b64,
                    })
                except Exception as att_err:
                    logger.warning("Failed to encode attachment for Brevo email: %s", att_err)
            if attachments_payload:
                payload["attachment"] = attachments_payload

        return payload

    def send_messages(self, email_messages):
        """Send one or more EmailMessage objects via the Brevo REST API."""
        if not email_messages:
            return 0

        if not self.api_key:
            error_msg = (
                "Brevo API key is not configured. Set BREVO_API_KEY or "
                "EMAIL_HOST_PASSWORD in your environment."
            )
            logger.error(error_msg)
            if not self.fail_silently:
                raise ValueError(error_msg)
            return 0

        sent_count = 0
        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json",
        }

        for message in email_messages:
            try:
                payload = self._build_payload(message)
                if not payload:
                    continue

                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code in (200, 201, 202):
                    sent_count += 1
                    resp_json = response.json() if response.content else {}
                    message_id = resp_json.get("messageId", "")
                    logger.info("Successfully sent email via Brevo API to %s (messageId=%s)", message.to, message_id)
                else:
                    error_detail = response.text
                    logger.error(
                        "Brevo API error (status %d): %s while sending to %s",
                        response.status_code,
                        error_detail,
                        message.to,
                    )
                    if not self.fail_silently:
                        response.raise_for_status()

            except Exception as e:
                logger.error("Exception sending email via Brevo API: %s", e)
                if not self.fail_silently:
                    raise

        return sent_count
