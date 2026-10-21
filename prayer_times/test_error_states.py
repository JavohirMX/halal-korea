"""Keep missing-location UI distinct from server/service failures."""
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(MONITORING_ENABLED=False)
class PrayerErrorStateTests(TestCase):
    @patch('prayer_times.views.get_user_location_context')
    def test_missing_location_is_400(self, location):
        location.return_value = {
            'location': {}, 'is_in_korea': False, 'user_type': 'international'
        }
        response = self.client.get(reverse('prayer_times:get_prayer_times'))
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()['show_error_ui'])

    @patch('prayer_times.views.get_prayer_times_ll')
    @patch('prayer_times.views.get_prayer_times')
    @patch('prayer_times.views.get_user_location_context')
    def test_service_failure_is_503_not_location_failure(self, location, times, coords):
        location.return_value = {
            'location': {'city': 'Seoul', 'country': 'South Korea'},
            'is_in_korea': True, 'user_type': 'korea',
        }
        times.return_value = coords.return_value = {'code': 503, 'error': 'Service unavailable'}
        response = self.client.get(reverse('prayer_times:get_prayer_times'))
        self.assertEqual(response.status_code, 503)

    def test_browser_location_prompt_only_handles_400(self):
        source = (Path(__file__).parent / 'templates/prayer_times/prayer_times.html').read_text()
        self.assertIn('if (response.status === 400 && data && data.show_error_ui)', source)
