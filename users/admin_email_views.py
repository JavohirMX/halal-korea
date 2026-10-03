"""
Admin Email hub views (compose + recent sends).

Mirrors the monitoring / data-management pattern: staff-gated views mounted
under /admin/email/ before admin.site.urls. Compose logic itself lives on
UserAdmin so the Users shortcuts and the hub cannot drift apart.
"""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from utils.models import AdminAction

from .models import User


def _user_admin():
    return admin.site._registry[User]


def _require_change_user(request):
    if not request.user.has_perm('users.change_user'):
        raise PermissionDenied


def _json_staff_gate(view):
    """Staff + change_user gate that answers JSON instead of an HTML 403 page."""

    @staff_member_required
    def wrapper(request, *args, **kwargs):
        if not request.user.has_perm('users.change_user'):
            return JsonResponse({'error': 'Permission denied.'}, status=403)
        return view(request, *args, **kwargs)

    return wrapper


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

    # POST always goes through compose handling (shared with Users shortcuts)
    if tab == 'compose' or request.method == 'POST':
        return _user_admin().compose_email_view(
            request,
            hub_mode=True,
            recent_sends=_recent_email_actions(),
        )

    context = {
        **admin.site.each_context(request),
        'title': 'Email',
        'tab': 'recent',
        'recent_sends': _recent_email_actions(),
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


@_json_staff_gate
def email_preview(request):
    """POST an unsent compose payload, get the live recipient count back."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    payload, status = _user_admin().email_preview(request)
    return JsonResponse(payload, status=status)


@_json_staff_gate
def email_user_search(request):
    """GET ?q=… typeahead over username, name and email for the user chips."""
    results = _user_admin().search_users(request.GET.get('q', ''))
    return JsonResponse({'results': results, 'count': len(results)})


@_json_staff_gate
def email_render_preview(request):
    """POST subject/message to get the rendered branded HTML email preview."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    payload, status = _user_admin().render_email_preview(request)
    return JsonResponse(payload, status=status)


@_json_staff_gate
def email_test_send(request):
    """POST subject/message/test_email to send a one-off test email."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    payload, status = _user_admin().test_send_email(request)
    return JsonResponse(payload, status=status)