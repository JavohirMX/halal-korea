"""
Management command to diagnose and test email configuration.

Usage:
    python manage.py test_email --check-ports
    python manage.py test_email --to hi@example.com
    python manage.py test_email --to hi@example.com --subject "Test"
"""
import socket
import ssl
import sys
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Test and diagnose email connectivity and send test emails."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            dest="recipient",
            help="Recipient email address for test message.",
        )
        parser.add_argument(
            "--subject",
            default="Halal Korea - Email Diagnostic Test",
            help="Subject line for test email.",
        )
        parser.add_argument(
            "--check-ports",
            action="store_true",
            help="Probe connectivity to Brevo SMTP and HTTPS API ports.",
        )

    def handle(self, *args, **options):
        recipient = options.get("recipient")
        check_ports = options.get("check_ports")

        self.stdout.write(self.style.MIGRATE_HEADING("=== Halal Korea Email Diagnostic ==="))
        self._print_current_config()

        if check_ports or not recipient:
            self._probe_ports()

        if recipient:
            self._send_test_email(recipient, options.get("subject"))

    def _print_current_config(self):
        backend = getattr(settings, "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
        host = getattr(settings, "EMAIL_HOST", "N/A")
        port = getattr(settings, "EMAIL_PORT", "N/A")
        tls = getattr(settings, "EMAIL_USE_TLS", False)
        use_ssl = getattr(settings, "EMAIL_USE_SSL", False)
        timeout = getattr(settings, "EMAIL_TIMEOUT", 15)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@halal-korea.com")
        api_key = getattr(settings, "BREVO_API_KEY", "") or getattr(settings, "EMAIL_HOST_PASSWORD", "")
        has_api_key = bool(api_key.strip())
        masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else ("Set" if has_api_key else "Missing")

        self.stdout.write(f"EMAIL_BACKEND     : {backend}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {from_email}")
        if "brevo_api" in backend.lower():
            self.stdout.write(f"BREVO_API_KEY     : {masked_key}")
            self.stdout.write(f"HTTP Timeout      : {timeout}s")
        else:
            self.stdout.write(f"EMAIL_HOST        : {host}")
            self.stdout.write(f"EMAIL_PORT        : {port}")
            self.stdout.write(f"EMAIL_USE_TLS     : {tls}")
            self.stdout.write(f"EMAIL_USE_SSL     : {use_ssl}")
            self.stdout.write(f"EMAIL_TIMEOUT     : {timeout}s")
            self.stdout.write(f"Password/API Key  : {masked_key}")
        self.stdout.write("")

    def _probe_ports(self):
        self.stdout.write(self.style.MIGRATE_HEADING("--- Network Port Probing ---"))
        targets = [
            ("smtp-relay.brevo.com", 587, "SMTP + STARTTLS (standard)"),
            ("smtp-relay.brevo.com", 2525, "SMTP + STARTTLS (alternative)"),
            ("smtp-relay.brevo.com", 465, "SMTP + SSL (SMTPS)"),
            ("api.brevo.com", 443, "HTTPS REST API (port 443)"),
        ]

        for host, port, desc in targets:
            self.stdout.write(f"Testing {host}:{port} ({desc})... ", ending="")
            sys.stdout.flush()
            try:
                sock = socket.create_connection((host, port), timeout=5)
                sock.close()
                self.stdout.write(self.style.SUCCESS("✓ OPEN"))
            except socket.timeout:
                self.stdout.write(self.style.ERROR("✗ TIMEOUT (likely blocked by host firewall)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ FAILED: {e}"))

        self.stdout.write("")

    def _send_test_email(self, recipient, subject):
        self.stdout.write(self.style.MIGRATE_HEADING(f"--- Sending Test Email to {recipient} ---"))
        plain_message = (
            "This is a test email sent from the Halal Korea diagnostic management command.\n"
            "If you are reading this, your email configuration is working properly!\n"
        )
        html_message = (
            "<html><body>"
            "<h2>Halal Korea - Email System Test</h2>"
            "<p>This is a test email sent from the Halal Korea diagnostic command.</p>"
            "<p><strong>Status:</strong> Your email configuration is working properly!</p>"
            "</body></html>"
        )

        try:
            sent = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False,
            )
            if sent:
                self.stdout.write(self.style.SUCCESS(f"✓ Test email successfully sent to {recipient}!"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ send_mail returned 0 (message not dispatched)."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to send email: {e}"))
            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("Troubleshooting tips:"))
            self.stdout.write("- If ports 587/2525/465 timed out, DigitalOcean has blocked outgoing SMTP.")
            self.stdout.write("- Switch to Brevo HTTPS API in your .env:")
            self.stdout.write("    EMAIL_BACKEND=utils.email_backends.brevo_api.BrevoAPIBackend")
            self.stdout.write("    BREVO_API_KEY=your-brevo-api-key")
