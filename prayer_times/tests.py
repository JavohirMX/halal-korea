from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import PrayerTimeCache
from .utils import get_prayer_times, get_prayer_times_ll, get_fallback_prayer_times
import json
from datetime import date

# Create your tests here.

class PrayerTimeCacheModelTest(TestCase):
    def setUp(self):
        self.test_data = {
            'city': 'Seoul',
            'country': 'South Korea',
            'date': date.today(),
            'prayer_times': {
                'fajr': '05:00',
                'sunrise': '06:00',
                'dhuhr': '12:00',
                'asr': '15:00',
                'maghrib': '18:00',
                'isha': '19:00'
            },
            'calculation_method': 3,
            'asr_method': 1
        }
        self.cache = PrayerTimeCache.objects.create(**self.test_data)

    def test_cache_creation(self):
        """Test that prayer time cache can be created"""
        self.assertEqual(self.cache.city, 'Seoul')
        self.assertEqual(self.cache.country, 'South Korea')
        self.assertEqual(self.cache.calculation_method, 3)
        self.assertEqual(self.cache.asr_method, 1)

    def test_get_cached_times(self):
        """Test retrieving cached prayer times"""
        cached_times = PrayerTimeCache.get_cached_times(
            'Seoul', 'South Korea', date.today()
        )
        self.assertEqual(cached_times, self.test_data['prayer_times'])

    def test_cache_expiration(self):
        """Test that cache expires after 24 hours"""
        # Create a cache entry with old timestamp
        old_cache = PrayerTimeCache.objects.create(
            city='Busan',
            country='South Korea',
            date=date.today(),
            prayer_times={'fajr': '05:00'},
            last_updated=timezone.now() - timedelta(hours=25)
        )
        
        # Force the cache to be considered expired
        old_cache.last_updated = timezone.now() - timedelta(hours=26)
        old_cache.save()
        
        cached_times = PrayerTimeCache.get_cached_times(
            'Busan', 'South Korea', date.today()
        )
        self.assertIsNone(cached_times)

class PrayerTimesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.prayer_times_url = reverse('prayer_times:prayer_times')
        self.get_prayer_times_data_url = reverse('prayer_times:get_prayer_times')
        self.update_settings_url = reverse('prayer_times:update_settings')
        self.update_location_url = reverse('prayer_times:update_location')
        
    def test_prayer_times_view(self):
        """Test prayer times view"""
        response = self.client.get(self.prayer_times_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prayer_times/prayer_times.html')
        
    def test_get_prayer_times(self):
        """Test getting prayer times data"""
        # Test with default parameters
        response = self.client.get(self.get_prayer_times_data_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('data', data)
        self.assertIn('timings', data['data'])
        
        # Test with specific date in DD-MM-YYYY format
        date_str = '11-05-2025'  # Using DD-MM-YYYY format
        response = self.client.get(f'{self.get_prayer_times_data_url}?date={date_str}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('data', data)
        self.assertIn('date', data['data'])
        self.assertEqual(data['data']['date']['gregorian']['date'], date_str)
        
    def test_update_settings(self):
        """Test updating prayer times settings"""
        data = {
            'calculation_method': 2,
            'asr_method': 1
        }
        response = self.client.post(
            self.update_settings_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
    def test_update_location(self):
        """Test updating location"""
        data = {
            'city': 'Seoul',
            'country': 'South Korea'
        }
        response = self.client.post(
            self.update_location_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
    def test_cache_expiration(self):
        """Test prayer times cache expiration"""
        # Create a test cache entry
        date_str = '11-05-2025'  # Using DD-MM-YYYY format
        prayer_times = {
            'code': 200,
            'status': 'OK',
            'data': {
                'timings': {
                    'Fajr': '05:00',
                    'Sunrise': '06:00',
                    'Dhuhr': '12:00',
                    'Asr': '15:00',
                    'Maghrib': '18:00',
                    'Isha': '19:00'
                }
            }
        }
        PrayerTimeCache.set_cached_times(
            city='Seoul',
            country='South Korea',
            date=date_str,
            prayer_times=prayer_times,
            calculation_method=3,  # Explicitly set calculation method
            asr_method=1
        )
        
        # Get the cache entry and verify it exists
        cache = PrayerTimeCache.objects.get(
            city='Seoul',
            country='South Korea',
            date=datetime.strptime(date_str, '%d-%m-%Y').date()
        )
        
        # Set last_updated to more than 23 hours ago (matching model's expiration time)
        cache.last_updated = timezone.now() - timedelta(hours=24)  # Using 24 hours to ensure expiration
        cache.save()
        
        # Force a small delay to ensure the save is complete
        timezone.now()
        
        # Verify cache is expired
        cached_times = PrayerTimeCache.get_cached_times(
            city='Seoul',
            country='South Korea',
            date=date_str
        )
        self.assertIsNone(cached_times, "Cache should be expired and return None")
        
        # Verify the cache entry was deleted
        with self.assertRaises(PrayerTimeCache.DoesNotExist):
            PrayerTimeCache.objects.get(
                city='Seoul',
                country='South Korea',
                date=datetime.strptime(date_str, '%d-%m-%Y').date()
            )
        
    def test_get_prayer_times_ll(self):
        """Test getting prayer times by latitude/longitude"""
        # Test with valid coordinates
        date_str = '11-05-2025'  # Using DD-MM-YYYY format
        times = get_prayer_times_ll(37.5665, 126.9780, date_str)
        self.assertIsNotNone(times)
        
        # Check if we got fallback times (which is fine for testing)
        if 'data' in times and 'timings' in times['data']:
            self.assertIn('Fajr', times['data']['timings'])
            self.assertIn('Sunrise', times['data']['timings'])
            self.assertIn('Dhuhr', times['data']['timings'])
            self.assertIn('Asr', times['data']['timings'])
            self.assertIn('Maghrib', times['data']['timings'])
            self.assertIn('Isha', times['data']['timings'])
        else:
            # If we got an error response, it should still have the basic structure
            self.assertIn('code', times)
            self.assertIn('status', times)
        
        # Test with invalid coordinates
        times = get_prayer_times_ll(200, 200, date_str)
        self.assertIsNotNone(times)  # Should return fallback times
        self.assertIn('data', times)
        self.assertIn('timings', times['data'])
        self.assertIn('Fajr', times['data']['timings'])

class PrayerTimesUtilsTest(TestCase):
    def test_get_prayer_times(self):
        """Test getting prayer times for a city"""
        # Create a test cache entry
        date_str = '11-05-2025'  # Using DD-MM-YYYY format
        PrayerTimeCache.objects.create(
            city='Seoul',
            country='South Korea',
            date=datetime.strptime(date_str, '%d-%m-%Y').date(),
            prayer_times={
                'fajr': '05:00',
                'sunrise': '06:00',
                'dhuhr': '12:00',
                'asr': '15:00',
                'maghrib': '18:00',
                'isha': '19:00'
            }
        )
        result = get_prayer_times('Seoul', 'South Korea', date_str)
        self.assertIn('data', result)
        self.assertIn('timings', result['data'])

    def test_get_prayer_times_ll(self):
        """Test getting prayer times using coordinates"""
        date_str = '11-05-2025'  # Using DD-MM-YYYY format
        result = get_prayer_times_ll(37.5665, 126.9780, date_str)  # Seoul coordinates
        self.assertIn('data', result)
        self.assertIn('timings', result['data'])

    def test_get_fallback_prayer_times(self):
        """Test getting fallback prayer times"""
        result = get_fallback_prayer_times()
        self.assertIn('data', result)
        self.assertIn('timings', result['data'])
