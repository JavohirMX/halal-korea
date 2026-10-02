"""Tests for admin user email helpers and compose UI."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from utils.models import AdminAction

User = get_user_model()


def _sync_submit(fn, *args, **kwargs):
    """Run ThreadPoolExecutor.submit synchronously for deterministic tests."""
    return fn(*args, **kwargs)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AdminEmailHelperTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='pass12345',
            first_name='Alice',
            last_name='Lee',
        )

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_send_admin_email_to_address(self, _mock_submit):
        from users.utils import send_admin_email_to_address

        ok = send_admin_email_to_address(
            'guest@example.com',
            'Hello',
            'Plain body',
            display_name='Guest',
        )
        self.assertTrue(ok)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['guest@example.com'])
        self.assertEqual(mail.outbox[0].subject, 'Hello')
        self.assertIn('Guest', mail.outbox[0].body)
        self.assertIn('Plain body', mail.outbox[0].body)

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_send_admin_email_to_address_invalid(self, _mock_submit):
        from users.utils import send_admin_email_to_address

        self.assertFalse(send_admin_email_to_address('not-an-email', 'S', 'B'))
        self.assertEqual(len(mail.outbox), 0)

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_send_admin_email_user_wrapper(self, _mock_submit):
        from users.utils import send_admin_email

        ok = send_admin_email(self.user, 'Hi Alice', 'Message for you')
        self.assertTrue(ok)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alice@example.com'])
        self.assertIn('Alice Lee', mail.outbox[0].body)

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_queue_admin_emails_dedupe_and_skip(self, _mock_submit):
        from users.utils import queue_admin_emails

        result = queue_admin_emails(
            [
                {'email': 'a@example.com', 'name': 'A'},
                {'email': 'A@example.com', 'name': 'A2'},
                {'email': '', 'name': 'Blank'},
                {'email': 'b@example.com'},
            ],
            'Subject',
            'Body',
        )
        self.assertEqual(result['sent'], 2)
        self.assertEqual(result['skipped'], 2)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(len(mail.outbox), 2)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AdminComposeEmailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
        )
        self.staff_no_perm = User.objects.create_user(
            username='staffer',
            email='staffer@example.com',
            password='staffpass123',
            is_staff=True,
        )
        self.u1 = User.objects.create_user(
            username='u1',
            email='u1@example.com',
            password='pass12345',
            email_verified=True,
            preferred_language='en',
            is_active=True,
        )
        self.u2 = User.objects.create_user(
            username='u2',
            email='u2@example.com',
            password='pass12345',
            email_verified=False,
            preferred_language='ko',
            is_active=True,
        )
        self.u3_blank = User.objects.create_user(
            username='u3',
            email='',
            password='pass12345',
            is_active=True,
        )
        self.compose_url = reverse('admin:users_user_compose_email')

    def _login_admin(self):
        self.client.login(username='admin', password='adminpass123')

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_single_user_mode(self, _mock_submit):
        self._login_admin()
        response = self.client.post(
            f'{self.compose_url}?user_id={self.u1.pk}',
            {
                'user_id': str(self.u1.pk),
                'subject': 'Single subject',
                'message': 'Hello single',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['u1@example.com'])
        action = AdminAction.objects.filter(action_type='email_users').latest('timestamp')
        self.assertEqual(action.changes['mode'], 'single')
        self.assertEqual(action.changes['sent'], 1)
        self.assertEqual(action.changes['subject'], 'Single subject')

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_selected_users_mode(self, _mock_submit):
        self._login_admin()
        ids = f'{self.u1.pk},{self.u2.pk}'
        response = self.client.post(
            f'{self.compose_url}?ids={ids}',
            {
                'ids': ids,
                'subject': 'Selected subject',
                'message': 'Hello selected',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ['u1@example.com', 'u2@example.com'])
        action = AdminAction.objects.filter(action_type='email_users').latest('timestamp')
        self.assertEqual(action.changes['mode'], 'selected')

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_filtered_broadcast_mode(self, _mock_submit):
        self._login_admin()
        response = self.client.post(
            self.compose_url,
            {
                'subject': 'Filter subject',
                'message': 'Hello filtered',
                'filter_email_verified': 'true',
                'filter_is_active': 'true',
                'filter_preferred_language': 'en',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['u1@example.com'])
        action = AdminAction.objects.filter(action_type='email_users').latest('timestamp')
        self.assertEqual(action.changes['mode'], 'broadcast')
        self.assertEqual(action.changes['filters']['filter_email_verified'], 'true')

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_adhoc_only_mode(self, _mock_submit):
        self._login_admin()
        # Broadcast with filters that match nobody + ad-hoc emails
        response = self.client.post(
            self.compose_url,
            {
                'subject': 'Adhoc subject',
                'message': 'Hello guests',
                'filter_email_verified': 'true',
                'filter_preferred_language': 'uz',
                'additional_emails': 'guest1@example.com\nguest2@example.com',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ['guest1@example.com', 'guest2@example.com'])
        action = AdminAction.objects.filter(action_type='email_users').latest('timestamp')
        self.assertEqual(action.changes['ad_hoc_count'], 2)

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_combined_user_and_adhoc_dedupe(self, _mock_submit):
        self._login_admin()
        response = self.client.post(
            f'{self.compose_url}?user_id={self.u1.pk}',
            {
                'user_id': str(self.u1.pk),
                'subject': 'Combined',
                'message': 'Hello',
                'additional_emails': 'u1@example.com, other@example.com',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ['other@example.com', 'u1@example.com'])

    def test_invalid_additional_email_rejected(self):
        self._login_admin()
        response = self.client.post(
            self.compose_url,
            {
                'subject': 'Bad',
                'message': 'Body',
                'additional_emails': 'good@example.com, not-valid',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, 'Invalid email')
        self.assertFalse(AdminAction.objects.filter(action_type='email_users').exists())

    def test_permission_denied_without_change_user(self):
        self.client.login(username='staffer', password='staffpass123')
        response = self.client.get(self.compose_url)
        self.assertEqual(response.status_code, 403)

    def test_permission_allowed_with_change_user(self):
        perm = Permission.objects.get(codename='change_user', content_type__app_label='users')
        self.staff_no_perm.user_permissions.add(perm)
        self.client.login(username='staffer', password='staffpass123')
        response = self.client.get(self.compose_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Compose email')

    def test_email_selected_users_action_redirects(self):
        self._login_admin()
        changelist = reverse('admin:users_user_changelist')
        response = self.client.post(
            changelist,
            {
                'action': 'email_selected_users',
                '_selected_action': [str(self.u1.pk), str(self.u2.pk)],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('compose-email', response.url)
        self.assertIn('ids=', response.url)

    def test_change_form_has_send_email_link(self):
        self._login_admin()
        url = reverse('admin:users_user_change', args=[self.u1.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send email')
        self.assertContains(response, f'user_id={self.u1.pk}')

    def test_changelist_has_compose_link(self):
        self._login_admin()
        response = self.client.get(reverse('admin:users_user_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Compose email')

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_blank_user_email_skipped(self, _mock_submit):
        self._login_admin()
        ids = f'{self.u1.pk},{self.u3_blank.pk}'
        response = self.client.post(
            f'{self.compose_url}?ids={ids}',
            {
                'ids': ids,
                'subject': 'Skip blank',
                'message': 'Hello',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        action = AdminAction.objects.filter(action_type='email_users').latest('timestamp')
        self.assertEqual(action.changes['sent'], 1)
        self.assertGreaterEqual(action.changes['skipped'], 1)

    def test_compose_uses_theme_token_css(self):
        self._login_admin()
        response = self.client.get(self.compose_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin/css/compose_email.css')
        self.assertNotContains(response, '#f0fdf4')
        self.assertNotContains(response, '#64748b')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AdminEmailHubTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
        )
        self.staff_no_perm = User.objects.create_user(
            username='staffer',
            email='staffer@example.com',
            password='staffpass123',
            is_staff=True,
        )
        self.u1 = User.objects.create_user(
            username='u1',
            email='u1@example.com',
            password='pass12345',
            email_verified=True,
            preferred_language='en',
            is_active=True,
        )
        self.hub_url = reverse('admin_email:hub')
        self.compose_hub_url = reverse('admin_email:compose')

    def _login_admin(self):
        self.client.login(username='admin', password='adminpass123')

    def test_hub_requires_login(self):
        response = self.client.get(self.hub_url)
        # staff_member_required redirects to login; some setups surface 404
        self.assertIn(response.status_code, [302, 404])
        self.assertNotEqual(response.status_code, 200)

    def test_hub_permission_denied_without_change_user(self):
        self.client.login(username='staffer', password='staffpass123')
        response = self.client.get(self.hub_url)
        self.assertEqual(response.status_code, 403)

    def test_hub_ok_with_change_user(self):
        perm = Permission.objects.get(codename='change_user', content_type__app_label='users')
        self.staff_no_perm.user_permissions.add(perm)
        self.client.login(username='staffer', password='staffpass123')
        response = self.client.get(self.hub_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Compose')
        self.assertContains(response, 'Recent sends')
        self.assertContains(response, 'admin/css/compose_email.css')

    def test_hub_compose_tab_renders_form(self):
        self._login_admin()
        response = self.client.get(f'{self.hub_url}?tab=compose')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send email')
        self.assertContains(response, 'name="subject"')

    def test_hub_recent_tab_shows_email_actions(self):
        self._login_admin()
        AdminAction.objects.create(
            admin_user=self.admin,
            action_type='email_users',
            object_repr='Email users (broadcast): Hello',
            changes={
                'subject': 'Hello hub',
                'mode': 'broadcast',
                'recipient_count': 3,
                'sent': 3,
                'skipped': 0,
                'failed': 0,
            },
            ip_hash='abcd1234',
        )
        response = self.client.get(f'{self.hub_url}?tab=recent')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hello hub')
        self.assertContains(response, 'admin')
        self.assertContains(response, '3')

    @patch('users.utils._email_executor.submit', side_effect=_sync_submit)
    def test_hub_compose_sends_and_redirects_to_recent(self, _mock_submit):
        self._login_admin()
        response = self.client.post(
            f'{self.hub_url}?tab=compose&user_id={self.u1.pk}',
            {
                'user_id': str(self.u1.pk),
                'subject': 'Hub subject',
                'message': 'Hello from hub',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/email/', response.url)
        self.assertIn('tab=recent', response.url)
        self.assertEqual(len(mail.outbox), 1)
        action = AdminAction.objects.filter(action_type='email_users').latest('timestamp')
        self.assertEqual(action.changes['subject'], 'Hub subject')

    def test_compose_path_redirects_to_hub_preserving_params(self):
        self._login_admin()
        response = self.client.get(f'{self.compose_hub_url}?user_id={self.u1.pk}')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/email/', response.url)
        self.assertIn('tab=compose', response.url)
        self.assertIn(f'user_id={self.u1.pk}', response.url)

    def test_users_shortcuts_still_present(self):
        self._login_admin()
        changelist = self.client.get(reverse('admin:users_user_changelist'))
        self.assertEqual(changelist.status_code, 200)
        self.assertContains(changelist, 'Compose email')
        change = self.client.get(reverse('admin:users_user_change', args=[self.u1.pk]))
        self.assertEqual(change.status_code, 200)
        self.assertContains(change, 'Send email')
        self.assertContains(change, f'user_id={self.u1.pk}')
