"""Redirect-target validation tests for the enhanced set_language view.

Regression coverage for #7: every exit path of set_language must refuse
off-site or protocol-relative `next` values and fall back to '/'.
"""
from unittest import mock

from django.test import TestCase
from django.urls import reverse


class SetLanguageRedirectValidationTests(TestCase):
    url_name = 'set_language'

    def _post(self, language='en', next_url='/places/'):
        return self.client.post(
            reverse(self.url_name),
            {'language': language, 'next': next_url},
        )

    def test_valid_language_onsite_next_redirects_to_next(self):
        response = self._post('en', '/places/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/places/')

    def test_valid_language_offsite_next_falls_back_to_home(self):
        response = self._post('en', 'https://evil.example.com/phish')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_valid_language_protocol_relative_next_falls_back_to_home(self):
        response = self._post('en', '//evil.example.com/phish')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_invalid_language_onsite_next_still_redirects_to_next(self):
        response = self._post('fr', '/places/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/places/')

    def test_invalid_language_offsite_next_falls_back_to_home(self):
        response = self._post('fr', 'https://evil.example.com/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_invalid_language_protocol_relative_next_falls_back_to_home(self):
        response = self._post('fr', '//evil.example.com/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_exception_fallback_validates_offsite_next(self):
        """If the view blows up mid-flow, the fallback redirect is still validated."""
        with mock.patch('utils.language_views.translation.activate',
                        side_effect=RuntimeError('boom')):
            response = self._post('en', 'https://evil.example.com/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_get_request_not_allowed(self):
        response = self.client.get(reverse(self.url_name))
        self.assertEqual(response.status_code, 405)
