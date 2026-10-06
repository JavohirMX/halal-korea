"""
Cloudflare Turnstile verification helpers.

Uses the existing `requests` dependency — no django-turnstile package.
Fails closed on network/HTTP errors (treat as invalid, log a warning).
"""

from __future__ import annotations

import logging

import requests
from django import forms
from django.conf import settings
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str | None:
    """
    Extract client IP for Turnstile siteverify.

    Mirrors the rate-limiting helpers (X-Forwarded-For first hop, else
    REMOTE_ADDR). Does not substitute a public IP for private addresses —
    Cloudflare needs the connecting client IP.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def verify_turnstile(token, remoteip=None, action=None) -> bool:
    """
    Verify a Turnstile token with Cloudflare siteverify.

    Returns True only when the response reports success (and optional
    action matches). Empty tokens, timeouts, and HTTP errors return False.
    """
    if not token:
        return False

    payload = {
        "secret": settings.TURNSTILE_SECRET,
        "response": token,
    }
    if remoteip:
        payload["remoteip"] = remoteip

    try:
        response = requests.post(
            settings.TURNSTILE_VERIFY_URL,
            data=payload,
            timeout=settings.TURNSTILE_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Turnstile siteverify failed: %s", exc)
        return False

    if not data.get("success"):
        return False

    if action is not None and "action" in data and data["action"] != action:
        return False

    return True


def require_turnstile(request, token=None, action=None) -> bool:
    """
    Verify Turnstile for non-form views.

    Pulls the token from POST ``cf-turnstile-response`` when not provided.
    """
    if token is None:
        token = request.POST.get("cf-turnstile-response")
    return verify_turnstile(
        token,
        remoteip=get_client_ip(request),
        action=action,
    )


class TurnstileWidget(forms.Widget):
    """Renders an explicit-mode Turnstile container div."""

    def __init__(self, attrs=None, action=None):
        super().__init__(attrs)
        self.action = action

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        action = final_attrs.pop("data-action", None) or self.action
        sitekey = settings.TURNSTILE_SITEKEY
        widget_id = final_attrs.get("id") or "cf-turnstile"
        # format_html escapes each interpolated value and marks the result safe.
        # Overriding render() bypasses the mark_safe() that Django's base
        # Widget.render() applies, so without this {{ form.captcha }} would emit
        # the container as escaped text and the widget would never reach the DOM.
        action_attr = format_html(' data-action="{}"', action) if action else ""
        return format_html(
            '<div class="cf-turnstile" id="{}" data-sitekey="{}"{}></div>',
            widget_id,
            sitekey,
            action_attr,
        )

    def value_from_datadict(self, data, files, name):
        # Turnstile always posts under this fixed key.
        return data.get("cf-turnstile-response")


class TurnstileField(forms.CharField):
    """
    Form field that verifies a Cloudflare Turnstile response.

    Reads POST key ``cf-turnstile-response`` and validates via siteverify.
    """

    def __init__(self, action=None, *args, **kwargs):
        kwargs.setdefault("required", True)
        kwargs.setdefault("label", "")
        self.action = action
        kwargs["widget"] = TurnstileWidget(action=action)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        if not verify_turnstile(value, action=self.action):
            raise forms.ValidationError(
                _("Please complete the security check.")
            )
        return value
