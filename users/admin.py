from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import escape, linebreaks
from django.utils.http import urlencode

from utils.models import AdminAction, hash_ip
from .forms import AdminEmailComposeForm
from .models import User
from .utils import queue_admin_emails


LARGE_SEND_THRESHOLD = 50


def _parse_bool_filter(value):
    if value == 'true':
        return True
    if value == 'false':
        return False
    return None


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
                self.admin_site.admin_view(self.compose_email_view),
                name='users_user_compose_email',
            ),
        ]
        return custom_urls + urls

    def email_selected_users(self, request, queryset):
        ids = ','.join(str(pk) for pk in queryset.values_list('pk', flat=True))
        url = reverse('admin:users_user_compose_email')
        return HttpResponseRedirect(f'{url}?{urlencode({"ids": ids})}')

    email_selected_users.short_description = 'Email selected users'

    def compose_email_view(self, request):
        if not request.user.has_perm('users.change_user'):
            raise PermissionDenied

        user_id = request.GET.get('user_id') or request.POST.get('user_id') or ''
        ids_param = request.GET.get('ids') or request.POST.get('ids') or ''
        mode = self._resolve_mode(user_id, ids_param)

        initial = {
            'filter_is_active': request.GET.get('filter_is_active', ''),
            'filter_email_verified': request.GET.get('filter_email_verified', ''),
            'filter_preferred_language': request.GET.get('filter_preferred_language', ''),
            'include_staff': request.GET.get('include_staff') in ('1', 'true', 'on'),
        }

        form = AdminEmailComposeForm(request.POST or None, initial=initial if request.method == 'GET' else None)

        if request.method == 'POST' and form.is_valid():
            recipients, skipped_users, filters_meta, ad_hoc_count = self._resolve_recipients(
                mode=mode,
                user_id=user_id,
                ids_param=ids_param,
                form=form,
            )
            total = len(recipients)

            if total == 0:
                messages.error(
                    request,
                    'No recipients to email. Add users or additional email addresses.',
                )
            elif total > LARGE_SEND_THRESHOLD and not form.cleaned_data.get('confirm_large_send'):
                form.add_error(
                    'confirm_large_send',
                    f'This send targets {total} recipients. Check the confirmation box to proceed.',
                )
            else:
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
                result['skipped'] = result.get('skipped', 0) + skipped_users

                self._log_admin_action(
                    request,
                    subject=form.cleaned_data['subject'],
                    result=result,
                    filters_meta=filters_meta,
                    ad_hoc_count=ad_hoc_count,
                    mode=mode,
                    recipient_count=total,
                )

                messages.success(
                    request,
                    (
                        f"Queued {result['sent']} email(s). "
                        f"Skipped {result['skipped']}, failed {result['failed']}."
                    ),
                )
                return HttpResponseRedirect(reverse('admin:users_user_changelist'))

        # Preview for GET and re-rendered POST forms
        preview_filters = initial
        additional_emails = []
        if request.method == 'POST' and form.is_bound:
            preview_filters = self._filters_from_bound_data(form)
            if form.is_valid() or 'additional_emails' in getattr(form, 'cleaned_data', {}):
                additional_emails = form.cleaned_data.get('additional_emails', [])

        preview_recipients, preview_skipped, filters_meta, ad_hoc_count = self._resolve_recipients(
            mode=mode,
            user_id=user_id,
            ids_param=ids_param,
            form=None,
            preview_filters=preview_filters,
            additional_emails=additional_emails,
        )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Compose email',
            'opts': self.model._meta,
            'form': form,
            'mode': mode,
            'user_id': user_id,
            'ids': ids_param,
            'recipient_count': len(preview_recipients),
            'skipped_count': preview_skipped,
            'ad_hoc_count': ad_hoc_count,
            'filters_meta': filters_meta,
            'preview_recipients': preview_recipients[:20],
            'large_send_threshold': LARGE_SEND_THRESHOLD,
            'has_view_permission': self.has_view_permission(request),
            'has_change_permission': self.has_change_permission(request),
        }
        return render(request, 'admin/users/compose_email.html', context)

    def _resolve_mode(self, user_id, ids_param):
        if user_id:
            return 'single'
        if ids_param:
            return 'selected'
        return 'broadcast'

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

    def _filters_from_form(self, form):
        if form is None or not hasattr(form, 'cleaned_data'):
            return {}
        return {
            'filter_is_active': form.cleaned_data.get('filter_is_active', ''),
            'filter_email_verified': form.cleaned_data.get('filter_email_verified', ''),
            'filter_preferred_language': form.cleaned_data.get('filter_preferred_language', ''),
            'include_staff': bool(form.cleaned_data.get('include_staff')),
        }

    def _filters_from_bound_data(self, form):
        data = form.data
        return {
            'filter_is_active': data.get('filter_is_active', ''),
            'filter_email_verified': data.get('filter_email_verified', ''),
            'filter_preferred_language': data.get('filter_preferred_language', ''),
            'include_staff': data.get('include_staff') in ('1', 'true', 'on', True),
        }

    def _preview_recipients(self, *, mode, user_id, ids_param, filters):
        return self._resolve_recipients(
            mode=mode,
            user_id=user_id,
            ids_param=ids_param,
            form=None,
            preview_filters=filters,
            additional_emails=[],
        )

    def _resolve_recipients(
        self,
        *,
        mode,
        user_id,
        ids_param,
        form=None,
        preview_filters=None,
        additional_emails=None,
    ):
        filters_meta = {}
        user_recipients = []
        skipped = 0

        if form is not None and hasattr(form, 'cleaned_data') and form.is_valid():
            additional_emails = form.cleaned_data.get('additional_emails') or []
            filters_meta = self._filters_from_form(form)
        elif preview_filters is not None:
            filters_meta = {
                'filter_is_active': preview_filters.get('filter_is_active', ''),
                'filter_email_verified': preview_filters.get('filter_email_verified', ''),
                'filter_preferred_language': preview_filters.get('filter_preferred_language', ''),
                'include_staff': bool(preview_filters.get('include_staff')),
            }
            additional_emails = additional_emails or []
        else:
            additional_emails = additional_emails or []

        if mode == 'single' and user_id:
            user = get_object_or_404(User, pk=user_id)
            user_recipients, skipped = self._users_to_recipients([user])
        elif mode == 'selected' and ids_param:
            try:
                id_list = [int(x) for x in ids_param.split(',') if x.strip()]
            except ValueError:
                id_list = []
            users = User.objects.filter(pk__in=id_list)
            user_recipients, skipped = self._users_to_recipients(users)
        elif mode == 'broadcast':
            qs = User.objects.all()
            qs = self._apply_broadcast_filters(qs, filters_meta)
            user_recipients, skipped = self._users_to_recipients(qs)

        merged, ad_hoc_added = self._merge_recipients(user_recipients, additional_emails)
        # ad_hoc_count should reflect how many ad-hoc addresses were provided (valid),
        # not only newly added after de-dupe — plan says metadata ad-hoc count.
        ad_hoc_count = len(additional_emails or [])
        return merged, skipped, filters_meta, ad_hoc_count

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
