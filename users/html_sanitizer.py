"""
HTML sanitisation for admin-authored email bodies.

When an admin ticks "Send as HTML" the body is dropped straight into the
branded email template with `|safe`. Without this, any staff account with
users.change_user can mail arbitrary markup — tracking pixels, spoofed
branding, phishing links — to the whole user base from the site's own
reputation, so the content has to be reduced to a known-safe subset before it
reaches the template.

Uses nh3 (Rust ammonia), which allowlists rather than blocklists: anything not
named is dropped, so a novel tag or attribute cannot slip through.
"""
import logging

import nh3

logger = logging.getLogger(__name__)

# Deliberately narrow. Formatting and links only — no embedding, no layout.
ALLOWED_TAGS = {
    'p', 'br', 'b', 'strong', 'i', 'em', 'u', 's',
    'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4',
    'blockquote', 'pre', 'code',
    'a', 'span', 'div',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
}

ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title'},
    '*': {'style'},
}

# Inline styling that cannot reposition or disguise content in the client.
ALLOWED_STYLE_PROPERTIES = {
    'color', 'background-color', 'font-size', 'font-weight', 'font-style',
    'text-align', 'text-decoration', 'line-height', 'margin', 'padding',
    'border', 'width', 'height',
}

ALLOWED_URL_SCHEMES = {'http', 'https', 'mailto'}

# Remove the tag *and its contents*. A bare allowlist would strip <script> but
# leave its source text visible in the message body.
CLEAN_CONTENT_TAGS = {
    'script', 'style', 'iframe', 'object', 'embed', 'form', 'input',
    'button', 'select', 'textarea', 'link', 'meta', 'svg', 'math', 'base',
    'noscript', 'title', 'head',
}


def sanitize_email_html(raw_html):
    """
    Reduce admin-authored HTML to a safe subset for email delivery.

    Never raises: on failure it returns an empty string so a broken body cannot
    block a send or leak unsanitised markup.
    """
    if not raw_html:
        return ''

    try:
        return nh3.clean(
            raw_html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            filter_style_properties=ALLOWED_STYLE_PROPERTIES,
            url_schemes=ALLOWED_URL_SCHEMES,
            clean_content_tags=CLEAN_CONTENT_TAGS,
            # Relative links are meaningless in an email and can be used to
            # probe that the mail was opened.
            url_relative='deny',
            link_rel='noopener noreferrer',
            strip_comments=True,
        )
    except Exception:
        logger.exception('Failed to sanitise admin email HTML; dropping the body')
        return ''