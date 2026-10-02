from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import escape, linebreaks
from django.utils.http import urlencode

from utils.models import AdminAction, hash_ip
from .forms import (
    AUDIENCE_MODE_ALL,
    AUDIENCE_MODE_MANUAL,
    AUDIENCE_MODE_SEGMENT,
    AUDIENCE_MODE_SINGLE,
    AUDIENCE_MODE_USERS,
    BROADCAST_AUDIENCE_MODES,
    DEFAULT_AUDIENCE_MODE,
    AdminEmailComposeForm,
    initial_audience_mode,
    parse_email_list,
    parse_id_list,
)
from .models import User
from .utils import queue_admin_emails


LARGE_SEND_THRESHOLD = 50
PREVIEW_SAMPLE_SIZE = 20
USER_SEARCH_LIMIT = 10
USER_SEARCH_MIN_QUERY = 2

# Only these fields are read when expanding a broadcast into recipients.
RECIPIENT_FIELDS = ('pk', 'email', 'username', 'first_name', 'last_name')

# Audience/form values persisted between visits so a half-written message
# survives an admin hopping over to the changelist to pick users.
DRAFT_SESSION_PREFIX = 'email_compose_draft_'
DRAFT_KEYS = (
    'audience_mode',
    'filter_is_active',
    'filter_email_verified',
    'filter_preferred_language',
    'include_staff',
    'user_id',
    'selected_user_ids',
    'additional_emails',
    'subject',
    'message',
    'send_as_html',
)

AUDIENCE_MODE_LABELS = {
    AUDIENCE_MODE_ALL: 'All users',
    AUDIENCE_MODE_SEGMENT: 'Segment',
    AUDIENCE_MODE_USERS: 'Specific users',
    AUDIENCE_MODE_SINGLE: 'Single user',
    AUDIENCE_MODE_MANUAL: 'Manual addresses',
}

EMPTY_AUDIENCE_MESSAGES = {
    AUDIENCE_MODE_ALL: 'No user has an email address yet.',
    AUDIENCE_MODE_SEGMENT: 'No users match these filters. Loosen the filters or switch audience.',
    AUDIENCE_MODE_USERS: 'No recipients — pick at least one user or enter an address.',
    AUDIENCE_MODE_SINGLE: 'No recipients — this user has no email address.',
    AUDIENCE_MODE_MANUAL: 'No recipients — enter at least one email address.',
}


def _parse_bool_filter(value):
    if value == 'true':
        return True
    if value == 'false':
        return False
    return None


def _as_bool(value):
    """Checkbox semantics for QueryDict strings, initial values and cleaned booleans."""
    return value in ('1', 'true', 'on', True)


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'preferred_language', 'email_verified', 'is_active', 'created_at', 'updated_at')
    list_filter = ('preferred_language', 'is_staff', 'is_active', 'email_verified')
    search_fields = ('username', 'email')
    ordering = ('-created_at',)
    actions = ['email_selected_users']
    change_form_template = 'admin/users/user/change_form.html'
    change_list_template = 'admin/users/user/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'compose-email/',
                self.admin_site.admin_view(self.compose_email_redirect),
                name='users_user_compose_email',
            ),
        ]
        return custom_urls + urls

    # --- Entry points -----------------------------------------------------

    def compose_email_redirect(self, request):
        """
        The Users changelist/change-form "Compose email" shortcuts live here.

        The Email hub under /admin/email/ is the one real compose page, so this
        just forwards there with the recipient context (user_id / ids) intact.
        """
        params = request.GET.copy()
        params['tab'] = 'compose'
        return HttpResponseRedirect(f"{reverse('admin_email:hub')}?{params.urlencode()}")

    def email_selected_users(self, request, queryset):
        ids = ','.join(str(pk) for pk in queryset.values_list('pk', flat=True))
        url = reverse('admin_email:hub')
        return HttpResponseRedirect(f'{url}?{urlencode({"tab": "compose", "ids": ids})}')

    email_selected_users.short_description = 'Email selected users'

    # --- Compose ----------------------------------------------------------

    def compose_email_view(self, request, hub_mode=False, recent_sends=None):
        if not request.user.has_perm('users.change_user'):
            raise PermissionDenied

        if request.method == 'POST':
            payload = request.POST.copy()
            # Legacy deep links carry the selection in `ids`; normalise it into
            # the field the form binds so both paths resolve identically.
            if not payload.get('selected_user_ids'):
                payload['selected_user_ids'] = payload.get('ids', '')
            form = AdminEmailComposeForm(payload, initial=self._initial_from_source(payload))
        else:
            if request.GET.get('discard'):
                self._discard_draft(request)
                return HttpResponseRedirect(f"{reverse('admin_email:hub')}?tab=compose")
            form = AdminEmailComposeForm(initial=self._initial_from_request(request))

        if request.method == 'POST' and form.is_valid():
            response = self._handle_send(request, form)
            if response is not None:
                return response

        # Preview for GET and re-rendered POST forms
        if form.is_bound and not form.is_valid():
            selection = self._recipient_selection_from_bound_data(form)
        elif form.is_bound:
            selection = self._recipient_selection_from_form(form)
        else:
            selection = self._recipient_selection_from_initial(form)

        try:
            recipients, skipped, ad_hoc_added = self._resolve_recipients(**selection)
        except Http404:
            recipients, skipped, ad_hoc_added = [], 0, 0

        total = len(recipients)
        needs_confirmation = self._needs_confirmation(selection['audience_mode'], total)
        self._save_draft(request, form)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Email' if hub_mode else 'Compose email',
            'opts': self.model._meta,
            'form': form,
            'audience_mode': selection['audience_mode'],
            'audience_mode_label': AUDIENCE_MODE_LABELS.get(selection['audience_mode'], selection['audience_mode']),
            'user_id': selection['user_id'],
            'selected_users': self._selected_user_rows(selection),
            'recipient_count': total,
            'skipped_count': skipped,
            'ad_hoc_count': ad_hoc_added,
            'filters_meta': selection['filters_meta'],
            'preview_recipients': recipients[:PREVIEW_SAMPLE_SIZE],
            'preview_sample_size': PREVIEW_SAMPLE_SIZE,
            'needs_confirmation': needs_confirmation,
            'large_send_threshold': LARGE_SEND_THRESHOLD,
            'has_view_permission': self.has_view_permission(request),
            'has_change_permission': self.has_change_permission(request),
            'from_hub': hub_mode,
            'tab': 'compose',
            'recent_sends': recent_sends or [],
            'compose_js_config': {
                'previewUrl': reverse('admin_email:preview'),
                'searchUrl': reverse('admin_email:user_search'),
                'confirmThreshold': LARGE_SEND_THRESHOLD,
                'sampleSize': PREVIEW_SAMPLE_SIZE,
                'defaultMode': DEFAULT_AUDIENCE_MODE,
            },
        }
        template = 'admin/email/hub.html' if hub_mode else 'admin/users/compose_email.html'
        return render(request, template, context)

    def _handle_send(self, request, form):
        """
        Queue the email and return a redirect, or None to re-render with errors.
        """
        selection = self._recipient_selection_from_form(form)
        try:
            recipients, skipped, ad_hoc_added = self._resolve_recipients(**selection)
        except Http404:
            # The deep-linked user was deleted between render and submit.
            form.add_error('user_id', 'That user no longer exists. Pick another audience.')
            return None
        total = len(recipients)
        mode = selection['audience_mode']

        if total == 0:
            messages.error(request, EMPTY_AUDIENCE_MESSAGES.get(mode, 'No recipients to email.'))
            return None

        if self._needs_confirmation(mode, total):
            typed = (form.cleaned_data.get('confirm_send_count') or '').strip()
            if typed != str(total):
                form.add_error(
                    'confirm_send_count',
                    f'Type {total} to confirm sending to {total} recipients.',
                )
                return None

        body_plain = form.cleaned_data['message']
        if form.cleaned_data.get('send_as_html'):
            body_html = body_plain
        else:
            body_html = linebreaks(escape(body_plain))

        result = queue_admin_emails(
            recipients,
            form.cleaned_data['subject'],
            body_plain,
            body_html=body_html,
        )
        result['skipped'] = result.get('skipped', 0) + skipped

        self._log_admin_action(
            request,
            subject=form.cleaned_data['subject'],
            result=result,
            filters_meta=selection['filters_meta'],
            ad_hoc_count=ad_hoc_added,
            mode=mode,
            recipient_count=total,
        )

        self._discard_draft(request)
        messages.success(
            request,
            (
                f"Queued {result['sent']} email(s). "
                f"Skipped {result['skipped']}, failed {result['failed']}."
            ),
        )
        return HttpResponseRedirect(f"{reverse('admin_email:hub')}?tab=recent")

    def _needs_confirmation(self, audience_mode, total):
        """Broad modes over the threshold require typing the exact recipient count."""
        if audience_mode not in BROADCAST_AUDIENCE_MODES:
            return False
        return total > LARGE_SEND_THRESHOLD

    # --- Form -> selection mapping ---------------------------------------

    def _initial_from_source(self, source):
        """Form-shaped initial values from a GET/POST QueryDict."""
        user_id = source.get('user_id', '')
        ids_param = source.get('ids', '')
        return {
            'audience_mode': (
                source.get('audience_mode') or initial_audience_mode(user_id, ids_param)
            ),
            'filter_is_active': source.get('filter_is_active', ''),
            'filter_email_verified': source.get('filter_email_verified', ''),
            'filter_preferred_language': source.get('filter_preferred_language', ''),
            'include_staff': _as_bool(source.get('include_staff')),
            'user_id': user_id,
            'selected_user_ids': source.get('selected_user_ids', '') or ids_param,
            'additional_emails': source.get('additional_emails', ''),
            'subject': source.get('subject', ''),
            'message': source.get('message', ''),
            'send_as_html': _as_bool(source.get('send_as_html')),
        }

    def _initial_from_request(self, request):
        initial = self._initial_from_source(request.GET)
        if any(request.GET.get(key) for key in DRAFT_KEYS):
            return initial

        # Bare GET: fall back to the saved draft so in-progress work is not lost.
        draft = request.session.get(f'{DRAFT_SESSION_PREFIX}{request.user.pk}') or {}
        for key in DRAFT_KEYS:
            value = draft.get(key)
            if value is None or value == '' or value is False:
                continue
            initial[key] = value
        return initial

    def _filters_from_mapping(self, mapping, *, include_staff):
        return {
            'filter_is_active': mapping.get('filter_is_active', '') or '',
            'filter_email_verified': mapping.get('filter_email_verified', '') or '',
            'filter_preferred_language': mapping.get('filter_preferred_language', '') or '',
            'include_staff': include_staff,
        }

    def _filters_from_form(self, form):
        data = form.cleaned_data
        return self._filters_from_mapping(
            data,
            include_staff=bool(data.get('include_staff')),
        )

    def _recipient_selection_from_form(self, form):
        """Recipient kwargs from a validated form."""
        data = form.cleaned_data
        return {
            'audience_mode': data.get('audience_mode') or DEFAULT_AUDIENCE_MODE,
            'user_id': data.get('user_id') or '',
            'selected_user_ids': data.get('selected_user_ids') or [],
            'filters_meta': self._filters_from_form(form),
            'additional_emails': data.get('additional_emails') or [],
        }

    def _recipient_selection_from_bound_data(self, form):
        """Recipient kwargs from a bound form that failed validation."""
        return self._selection_from_mapping(form.data)

    def _recipient_selection_from_initial(self, form):
        """Recipient kwargs for an unbound form (first render)."""
        return self._selection_from_mapping(form.initial)

    def _selection_from_mapping(self, mapping):
        """
        Recipient kwargs straight from a QueryDict or initial dict.

        Used for previews, where the payload may not have passed validation yet —
        so every value is parsed leniently rather than assumed clean.
        """
        valid_emails, _ = parse_email_list(mapping.get('additional_emails', ''))
        ids, _ = parse_id_list(mapping.get('selected_user_ids', '') or mapping.get('ids', ''))
        user_id = str(mapping.get('user_id', '')).strip()
        return {
            'audience_mode': (
                mapping.get('audience_mode')
                or initial_audience_mode(user_id, mapping.get('ids', ''))
            ),
            'user_id': int(user_id) if user_id.isdigit() else user_id,
            'selected_user_ids': ids,
            'filters_meta': self._filters_from_mapping(
                mapping,
                include_staff=_as_bool(mapping.get('include_staff')),
            ),
            'additional_emails': valid_emails,
        }

    def _selected_user_rows(self, selection):
        """User rows behind the chips, so the template can label them."""
        ids = selection.get('selected_user_ids') or []
        if selection['audience_mode'] == AUDIENCE_MODE_SINGLE:
            ids = [selection['user_id']] if selection['user_id'] else []
        if not ids:
            return []

        users = User.objects.filter(pk__in=ids).only(
            'pk', 'username', 'email', 'first_name', 'last_name'
        )
        rows = {u.pk: u for u in users}

        ordered = []
        for pk in ids:
            user = rows.get(pk)
            if user is None:
                continue
            ordered.append(
                {
                    'id': user.pk,
                    'name': user.full_name,
                    'email': user.email or '',
                    'has_email': bool(user.email),
                }
            )
        return ordered

    # --- Draft persistence ------------------------------------------------

    def _save_draft(self, request, form):
        """Persist the compose state so it survives navigating away mid-draft."""
        source = form.data if form.is_bound else form.initial

        draft = {key: source.get(key, '') for key in DRAFT_KEYS}
        # ?ids= is the legacy name for the same selection.
        draft['selected_user_ids'] = source.get('selected_user_ids', '') or source.get('ids', '')
        # Unchecked boxes are absent from a POST body, so normalise to real bools.
        draft['include_staff'] = _as_bool(source.get('include_staff'))
        draft['send_as_html'] = _as_bool(source.get('send_as_html'))

        request.session[f'{DRAFT_SESSION_PREFIX}{request.user.pk}'] = draft
        request.session.modified = True

    def _discard_draft(self, request):
        request.session.pop(f'{DRAFT_SESSION_PREFIX}{request.user.pk}', None)
        request.session.modified = True

    # --- Recipient resolution --------------------------------------------

    def _apply_broadcast_filters(self, queryset, filters):
        filters = filters or {}
        is_active = _parse_bool_filter(filters.get('filter_is_active', ''))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        email_verified = _parse_bool_filter(filters.get('filter_email_verified', ''))
        if email_verified is not None:
            queryset = queryset.filter(email_verified=email_verified)

        language = filters.get('filter_preferred_language') or ''
        if language:
            queryset = queryset.filter(preferred_language=language)

        if not filters.get('include_staff'):
            queryset = queryset.filter(is_staff=False)

        return queryset

    def _users_to_recipients(self, users):
        recipients = []
        skipped = 0
        for user in users:
            email = (user.email or '').strip()
            if not email:
                skipped += 1
                continue
            recipients.append({'email': email, 'name': user.full_name})
        return recipients, skipped

    def _merge_recipients(self, user_recipients, ad_hoc_emails):
        """Union user recipients and ad-hoc emails, de-duplicated by lowercased email."""
        merged = []
        seen = set()
        for item in user_recipients:
            key = item['email'].lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        ad_hoc_added = 0
        for email in ad_hoc_emails or []:
            key = email.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append({'email': email, 'name': None})
            ad_hoc_added += 1
        return merged, ad_hoc_added

    def _resolve_recipients(
        self,
        *,
        audience_mode,
        user_id='',
        selected_user_ids=None,
        filters_meta=None,
        additional_emails=None,
    ):
        """
        Expand an audience selection into recipients.

        Returns (recipients, skipped_users_without_email, ad_hoc_addresses_added).
        """
        filters_meta = filters_meta or {}
        additional_emails = additional_emails or []

        if audience_mode == AUDIENCE_MODE_SINGLE:
            users = [get_object_or_404(User, pk=user_id)] if user_id else User.objects.none()
        elif audience_mode == AUDIENCE_MODE_USERS:
            ids = selected_user_ids or []
            users = (
                User.objects.filter(pk__in=ids).only(*RECIPIENT_FIELDS)
                if ids
                else User.objects.none()
            )
        elif audience_mode == AUDIENCE_MODE_ALL:
            users = User.objects.only(*RECIPIENT_FIELDS)
        elif audience_mode == AUDIENCE_MODE_SEGMENT:
            users = self._apply_broadcast_filters(
                User.objects.only(*RECIPIENT_FIELDS),
                filters_meta,
            )
        else:  # AUDIENCE_MODE_MANUAL — addresses only, no user lookup
            users = User.objects.none()

        user_recipients, skipped = self._users_to_recipients(users)
        merged, ad_hoc_added = self._merge_recipients(user_recipients, additional_emails)
        return merged, skipped, ad_hoc_added

    def search_users(self, query, limit=USER_SEARCH_LIMIT):
        """Typeahead lookup over the fields an admin is likely to remember."""
        query = (query or '').strip()
        if len(query) < USER_SEARCH_MIN_QUERY:
            return []

        users = (
            User.objects.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
            .only('pk', 'username', 'email', 'first_name', 'last_name', 'is_active', 'email_verified')
            .order_by('username')[:limit]
        )
        return [
            {
                'id': user.pk,
                'username': user.username,
                'name': user.full_name,
                'email': user.email or '',
                'is_active': user.is_active,
                'email_verified': user.email_verified,
            }
            for user in users
        ]

    def email_preview(self, request):
        """
        Resolve recipients for an unsent payload so the compose page can show a
        live count. Shares _resolve_recipients with the send path, so the
        previewed count is the count that gets sent.
        """
        form = AdminEmailComposeForm(request.POST)
        if form.is_valid():
            selection = self._recipient_selection_from_form(form)
        else:
            selection = self._recipient_selection_from_bound_data(form)

        try:
            recipients, skipped, ad_hoc_added = self._resolve_recipients(**selection)
        except Http404:
            return {
                'audience_mode': selection['audience_mode'],
                'count': 0,
                'skipped': 0,
                'ad_hoc_count': 0,
                'needs_confirmation': False,
                'threshold': LARGE_SEND_THRESHOLD,
                'sample': [],
                'error': 'Unknown user.',
            }, 400

        total = len(recipients)
        return {
            'audience_mode': selection['audience_mode'],
            'count': total,
            'skipped': skipped,
            'ad_hoc_count': ad_hoc_added,
            'needs_confirmation': self._needs_confirmation(selection['audience_mode'], total),
            'threshold': LARGE_SEND_THRESHOLD,
            'sample': recipients[:PREVIEW_SAMPLE_SIZE],
            'total_samples': len(recipients),
        }, 200

    def _log_admin_action(self, request, *, subject, result, filters_meta, ad_hoc_count, mode, recipient_count):
        try:
            content_type = ContentType.objects.get_for_model(User)
            AdminAction.objects.create(
                admin_user=request.user,
                action_type='email_users',
                content_type=content_type,
                object_id=None,
                object_repr=f'Email users ({mode}): {subject}'[:200],
                changes={
                    'subject': subject,
                    'mode': mode,
                    'audience_mode': mode,
                    'audience_label': AUDIENCE_MODE_LABELS.get(mode, mode),
                    'recipient_count': recipient_count,
                    'sent': result.get('sent', 0),
                    'skipped': result.get('skipped', 0),
                    'failed': result.get('failed', 0),
                    'filters': filters_meta,
                    'ad_hoc_count': ad_hoc_count,
                },
                ip_hash=hash_ip(_client_ip(request)) or '',
            )
        except Exception:
            # Audit logging must not block the admin flow
            pass