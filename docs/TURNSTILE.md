# Cloudflare Turnstile Setup

This guide explains how Halal Korea uses [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/) to block bots on public forms, and how to configure it for local development and production.

## Overview

Turnstile is a CAPTCHA alternative that runs lightweight browser challenges and issues a short-lived token. Django verifies that token server-side with Cloudflare’s **siteverify** API before accepting the submission.

Important points:

- Turnstile does **not** require Cloudflare CDN or DNS — it works as a standalone embed.
- The client widget alone is **not** protection. Every protected endpoint must call siteverify (via `verify_turnstile` / `TurnstileField` / `require_turnstile`).
- This project uses **Managed** widget mode and **explicit** client rendering (`HalalTurnstile.render` / `reset`).

## Protected Surfaces

| Surface | How verification runs | Action name |
|---------|----------------------|-------------|
| Registration | `TurnstileField` on `UserRegistrationForm` | `register` |
| Login | `require_turnstile` in `login_view` POST | `login` |
| Password reset request | `TurnstileField` on `PasswordResetRequestForm` | `password_reset` |
| Resend activation (anonymous POST) | `require_turnstile` in view | `resend_activation` |
| Contact form (AJAX) | `TurnstileField` on `ContactForm` | `contact` |
| Feedback widget (JSON) | `verify_turnstile` in `submit_feedback` | `feedback` |

**Not covered (by design):**

- Authenticated GET resend-activation (already logged in + rate-limited)
- Place submit / suggest-edit / reviews (require login + email verification)

## Cloudflare Setup (Production)

1. Create a free [Cloudflare account](https://dash.cloudflare.com/sign-up) if you do not have one.
2. Open **Turnstile** in the dashboard and create a widget.
3. Choose **Managed** mode.
4. Add your **production hostname(s)** only (for example `example.com`). Adding a hostname also authorizes its subdomains. Do **not** add `localhost` to the production widget.
5. Copy the **site key** (public) and **secret key** (server-only).

Official docs: [Get started](https://developers.cloudflare.com/turnstile/get-started/), [Plans](https://developers.cloudflare.com/turnstile/plans/).

## Environment Variables

Add these to your `.env` file (see also `.env.example`):

```bash
# Cloudflare Turnstile (CAPTCHA)
# Leave unset locally to use Cloudflare always-pass dummy keys.
# Production must set real keys from the Cloudflare Turnstile dashboard.
TURNSTILE_SITEKEY=your-production-sitekey
TURNSTILE_SECRET=your-production-secret
```

| Variable | Purpose |
|----------|---------|
| `TURNSTILE_SITEKEY` | Public key rendered in the browser widget |
| `TURNSTILE_SECRET` | Private key used only in server-side siteverify |

Additional settings in `config/settings.py` (not env-driven):

- `TURNSTILE_VERIFY_URL` — `https://challenges.cloudflare.com/turnstile/v0/siteverify`
- `TURNSTILE_TIMEOUT` — HTTP timeout in seconds (default `5`)

**Never** put `TURNSTILE_SECRET` in client-side JavaScript or templates.

## Local Development

If `TURNSTILE_SITEKEY` / `TURNSTILE_SECRET` are unset, settings default to Cloudflare’s official **always-pass** dummy keys:

| Key | Dummy value |
|-----|-------------|
| Sitekey | `1x00000000000000000000AA` |
| Secret | `1x0000000000000000000000000000000AA` |

Notes:

- Dummy keys work on any domain, including `localhost`.
- Dummy tokens look like `XXXX.DUMMY.TOKEN.XXXX`.
- Production secrets **reject** dummy tokens (and test secrets reject real tokens). Keep environments separate.

## Architecture

```
Browser widget → cf-turnstile-response token
       ↓
Django view / form clean
       ↓
utils.turnstile.verify_turnstile → Cloudflare siteverify
       ↓
Accept or reject submission
```

### Key files

| File | Role |
|------|------|
| `utils/turnstile.py` | `verify_turnstile()`, `require_turnstile()`, `TurnstileField`, `get_client_ip()` |
| `utils/context_processors.py` | Exposes `TURNSTILE_SITEKEY` to all templates |
| `static/js/turnstile-helpers.js` | `window.HalalTurnstile.render` / `reset` for explicit widgets |
| `places/templates/places/base.html` | Loads Turnstile `api.js?render=explicit`, sets `window.TURNSTILE_SITEKEY`, includes helpers |
| `users/forms.py` / `users/views.py` | Register, login, password-reset, resend-activation |
| `contact/forms.py` + contact templates | Contact AJAX form + render/reset after inject |
| `feedback/views.py` + `static/js/feedback-widget.js` | JSON feedback with `cf-turnstile-response` |

Tokens expire after **5 minutes** and are **single-use**. After a failed or successful submit, the UI should call `HalalTurnstile.reset(...)` so the next attempt gets a fresh token.

Network or HTTP failures during siteverify are treated as **invalid** (fail closed) and logged as a warning.

## Production Checklist

1. Create a Managed Turnstile widget with production hostnames only.
2. Set real `TURNSTILE_SITEKEY` and `TURNSTILE_SECRET` in the deploy environment.
3. Restart / redeploy the app so settings pick up the new values.
4. Smoke-test: register, login, contact, and feedback with a real browser.
5. Confirm submissions **without** a token are rejected.
6. In the Cloudflare Turnstile dashboard, confirm siteverify validations are non-zero (client-only embeds show zero validations).

## Testing

Unit and view tests mock siteverify so CI does not call Cloudflare.

- Core: `utils.tests.test_turnstile`
- Auth / rate limits / password reset: patch `verify_turnstile` or `require_turnstile`, or POST a dummy token with mocked `requests.post`
- Contact: `contact.tests` — valid forms mock verification; missing/invalid captcha fails clean
- Feedback: `feedback.tests` — missing/invalid token → 400; valid mocked token accepted

Example pattern:

```python
from unittest.mock import patch
from django.test import override_settings

@override_settings(
    TURNSTILE_SITEKEY="1x00000000000000000000AA",
    TURNSTILE_SECRET="1x0000000000000000000000000000000AA",
)
@patch("utils.turnstile.verify_turnstile", return_value=True)
def test_something(self, mock_verify):
    ...
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Form always fails security check | Missing `cf-turnstile-response`, expired/spent token, or siteverify error | Ensure widget rendered; call `HalalTurnstile.reset` after failures; check server logs for siteverify warnings |
| Widget never appears | Script blocked or sitekey missing | Confirm `api.js` loads from `challenges.cloudflare.com`; check `TURNSTILE_SITEKEY` / `window.TURNSTILE_SITEKEY` |
| Works locally, fails in production | Hostname not allowlisted, or still using dummy keys | Add production hostname to the widget; set real env secrets |
| `timeout-or-duplicate` from Cloudflare | Token reused or older than 5 minutes | Reset the widget before retrying |
| Analytics show zero validations | Backend never calls siteverify | Ensure views/forms use `verify_turnstile` / `TurnstileField` / `require_turnstile` |

## Related Docs

- [CONTACT_FORM.md](CONTACT_FORM.md) — contact form rate limiting and AJAX flow
- [PASSWORD_RESET_IMPLEMENTATION.md](PASSWORD_RESET_IMPLEMENTATION.md) — password reset flow
- [EXTERNAL_LOGIN_SETUP.md](EXTERNAL_LOGIN_SETUP.md) — social login (not Turnstile-protected today)
