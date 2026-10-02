"""
Admin Email hub views (compose + recent sends).

Mirrors the monitoring / data-management pattern: staff-gated views mounted
under /admin/email/ before admin.site.urls.
"""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from utils.models import AdminAction

from .models import User


def _user_admin():
    return admin.site._registry[User]


def _require_change_user(request):
    if not request.user.has_perm('users.change_user'):
        raise PermissionDenied


def _recent_email_actions(limit=20):
    return (
        AdminAction.objects.filter(action_type='email_users')
        .select_related('admin_user')
        .order_by('-timestamp')[:limit]
    )


@staff_member_required
def email_hub(request):
    """Email hub: compose tab + recent email_users AdminActions."""
    _require_change_user(request)

    tab = request.GET.get('tab', 'compose')
    if tab not in ('compose', 'recent'):
        tab = 'compose'

    recent_sends = _recent_email_actions()

    # POST always goes through compose handling (shared with Users shortcuts)
    if request.method == 'POST':
        return _user_admin().compose_email_view(
            request,
            hub_mode=True,
            recent_sends=recent_sends,
        )

    if tab == 'compose':
        return _user_admin().compose_email_view(
            request,
            hub_mode=True,
            recent_sends=recent_sends,
        )

    context = {
        **admin.site.each_context(request),
        'title': 'Email',
        'tab': 'recent',
        'recent_sends': recent_sends,
        'opts': User._meta,
        'from_hub': True,
    }
    return render(request, 'admin/email/hub.html', context)


@staff_member_required
def email_compose(request):
    """
    /admin/email/compose/ — same compose flow as the hub compose tab,
    preserving query params (user_id, ids, filters).
    """
    _require_change_user(request)

    if request.method == 'POST':
        return _user_admin().compose_email_view(
            request,
            hub_mode=True,
            recent_sends=_recent_email_actions(),
        )

    # Redirect GET to hub compose tab so chrome/tabs stay consistent
    params = request.GET.copy()
    params['tab'] = 'compose'
    return HttpResponseRedirect(f"{reverse('admin_email:hub')}?{params.urlencode()}")
