"""
Template helpers for social authentication buttons.

The login/register templates offer Google/GitHub sign-in, but a provider
without configured credentials (no SocialApp and no settings-backed APP)
makes {% provider_login_url %} raise and 500 the whole page. These tags
let templates render buttons only for providers that are actually usable.
"""

from django import template
from allauth.socialaccount.adapter import get_adapter

register = template.Library()


@register.simple_tag(takes_context=True)
def provider_configured(context, provider_id):
    """True when the given allauth provider has at least one app configured."""
    request = context.get("request")
    try:
        get_adapter().get_provider(request, provider_id)
        return True
    except Exception:
        return False
