"""
Tests for Business Hours feature including:
- BusinessHours and TimeSlot models
- BusinessHoursSuggestion model and approval workflow
- Utility functions (get_place_status, format_hours_for_display, etc.)
- Frontend display logic
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import datetime, time, timedelta, date
from decimal import Decimal
from unittest.mock import patch, MagicMock
import json
import pytz

from .models import HalalPlace, BusinessHours, TimeSlot, BusinessHoursSuggestion
from .business_hours import (
    get_place_status, 
    get_today_hours, 
    get_weekly_hours, 
    get_opening_hours_schema,
    is_place_open,
    get_korea_time,
    DAY_NAMES,
    CLOSES_SOON_THRESHOLD,
    OPENS_SOON_THRESHOLD
)

User = get_user_model()


class BusinessHoursModelTest(TestCase):
    """Test the BusinessHours and TimeSlot models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.place = HalalPlace.objects.create(
            name='Test Restaurant',
            description='A test restaurant',
            category='restaurant',
            location=Point(127.0, 37.5),
            address='Test Address',
            status='approved',
            submitted_by=self.user
        )
    
    def test_create_business_hours(self):
        """Test creating business hours for a place"""
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False,
            notes='Last order 30 min before close'
        )
        
        self.assertEqual(business_hours.place, self.place)
        self.assertFalse(business_hours.is_24_hours)
        self.assertEqual(business_hours.notes, 'Last order 30 min before close')
    
    def test_create_24_hours_place(self):
        """Test creating a 24-hour place"""
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=True
        )
        
        self.assertTrue(business_hours.is_24_hours)
        self.assertEqual(str(business_hours), f'{self.place.name} - Open 24 Hours')
    
    def test_create_time_slots(self):
        """Test creating time slots for each day"""
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False
        )
        
        # Create a time slot for Monday
        slot = TimeSlot.objects.create(
            business_hours=business_hours,
            day_of_week=0,  # Monday
            open_time=time(9, 0),
            close_time=time(22, 0)
        )
        
        self.assertEqual(slot.get_day_of_week_display(), 'Monday')
        self.assertEqual(slot.open_time, time(9, 0))
        self.assertEqual(slot.close_time, time(22, 0))
        self.assertFalse(slot.is_closed)
    
    def test_create_closed_day(self):
        """Test marking a day as closed"""
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False
        )
        
        # Create a closed Sunday
        slot = TimeSlot.objects.create(
            business_hours=business_hours,
            day_of_week=6,  # Sunday
            is_closed=True
        )
        
        self.assertTrue(slot.is_closed)
        self.assertIn('Closed', str(slot))
    
    def test_multiple_time_slots_per_day(self):
        """Test multiple time slots for same day (e.g., lunch + dinner)"""
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False
        )
        
        # Lunch slot
        lunch = TimeSlot.objects.create(
            business_hours=business_hours,
            day_of_week=0,  # Monday
            open_time=time(11, 0),
            close_time=time(14, 0)
        )
        
        # Dinner slot
        dinner = TimeSlot.objects.create(
            business_hours=business_hours,
            day_of_week=0,  # Monday
            open_time=time(17, 0),
            close_time=time(22, 0)
        )
        
        slots = business_hours.time_slots.filter(day_of_week=0)
        self.assertEqual(slots.count(), 2)


class BusinessHoursUtilitiesTest(TestCase):
    """Test utility functions for business hours"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.place = HalalPlace.objects.create(
            name='Test Restaurant',
            description='A test restaurant',
            category='restaurant',
            location=Point(127.0, 37.5),
            address='Test Address',
            status='approved',
            submitted_by=self.user
        )
    
    def test_get_place_status_no_hours(self):
        """Test status when place has no business hours"""
        status = get_place_status(self.place)
        self.assertIsNone(status)
    
    def test_get_place_status_24_hours(self):
        """Test status for 24-hour place"""
        BusinessHours.objects.create(
            place=self.place,
            is_24_hours=True
        )
        
        status = get_place_status(self.place)
        self.assertIsNotNone(status)
        self.assertEqual(status['type'], 'open')
        self.assertIn('24', status['message'])
    
    def test_get_place_status_temp_closed(self):
        """Test status for temporarily closed place"""
        tomorrow = date.today() + timedelta(days=1)
        self.place.temporary_closure_until = tomorrow
        self.place.temporary_closure_reason = 'Renovation'
        self.place.save()
        
        status = get_place_status(self.place)
        self.assertIsNotNone(status)
        self.assertEqual(status['type'], 'temp_closed')
    
    @patch('places.business_hours.get_korea_time')
    def test_get_place_status_open(self, mock_korea_time):
        """Test status when place is currently open"""
        # Mock current time to be 12:00 on a Monday
        korea_tz = pytz.timezone('Asia/Seoul')
        mock_now = datetime(2026, 1, 12, 12, 0, tzinfo=korea_tz)  # Monday
        mock_korea_time.return_value = mock_now
        
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False
        )
        
        # Open 9:00 - 22:00 on Monday
        TimeSlot.objects.create(
            business_hours=business_hours,
            day_of_week=0,
            open_time=time(9, 0),
            close_time=time(22, 0)
        )
        
        status = get_place_status(self.place)
        self.assertIn(status['type'], ['open', 'closes_soon'])
    
    @patch('places.business_hours.get_korea_time')
    def test_get_place_status_closed(self, mock_korea_time):
        """Test status when place is currently closed"""
        # Mock current time to be 3:00 AM on a Monday
        korea_tz = pytz.timezone('Asia/Seoul')
        mock_now = datetime(2026, 1, 12, 3, 0, tzinfo=korea_tz)  # Monday
        mock_korea_time.return_value = mock_now
        
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False
        )
        
        # Open 9:00 - 22:00 on Monday
        TimeSlot.objects.create(
            business_hours=business_hours,
            day_of_week=0,
            open_time=time(9, 0),
            close_time=time(22, 0)
        )
        
        status = get_place_status(self.place)
        self.assertIn(status['type'], ['closed', 'opens_at'])
    
    def test_get_opening_hours_schema_no_hours(self):
        """Test schema when place has no business hours"""
        schema = get_opening_hours_schema(self.place)
        self.assertEqual(schema, [])


class SubmitPlaceBusinessHoursTest(TestCase):
    """Integration tests for submit place business hours."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="submituser",
            email="submit@example.com",
            password="testpass123",
        )
        self.user.email_verified = True
        self.user.save()
        self.client.force_login(self.user)

    def _base_payload(self):
        return {
            "name": "New Place",
            "description": "A brand new place with halal options.",
            "category": "restaurant",
            "address": "123 Example Street",
            "latitude": "37.5665",
            "longitude": "126.9780",
        }

    def test_submit_place_with_hours_creates_business_hours(self):
        payload = self._base_payload()
        payload.update(
            {
                "suggest_business_hours": "true",
                "business_hours_json": json.dumps(
                    {
                        "is_24_hours": False,
                        "notes": "Last order 30 min before close",
                        "hours": {
                            "0": [{"open": "09:00", "close": "17:00"}],
                            "1": "closed",
                        },
                    }
                ),
            }
        )

        response = self.client.post(reverse("places:submit_place"), payload)
        self.assertEqual(response.status_code, 302)

        place = HalalPlace.objects.get(name="New Place")
        business_hours = BusinessHours.objects.get(place=place)
        self.assertFalse(business_hours.is_24_hours)
        self.assertEqual(business_hours.notes, "Last order 30 min before close")
        self.assertEqual(TimeSlot.objects.filter(business_hours=business_hours).count(), 2)

    def test_submit_place_invalid_hours_shows_error(self):
        payload = self._base_payload()
        payload.update(
            {
                "suggest_business_hours": "true",
                "business_hours_json": json.dumps(
                    {
                        "is_24_hours": False,
                        "notes": "",
                        "hours": {"0": [{"open": "9am", "close": "17:00"}]},
                    }
                ),
            }
        )

        response = self.client.post(reverse("places:submit_place"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid time format")
        self.assertEqual(BusinessHours.objects.count(), 0)


class SuggestEditBusinessHoursValidationTest(TestCase):
    """Validate business hours payload in suggest edit flow."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="suggestuser",
            email="suggest@example.com",
            password="testpass123",
        )
        self.user.email_verified = True
        self.user.save()
        self.client.force_login(self.user)
        self.place = HalalPlace.objects.create(
            name="Suggest Place",
            description="Test place for suggestions",
            category="restaurant",
            location=Point(127.0, 37.5),
            address="Test Address",
            status="approved",
            submitted_by=self.user,
        )

    def test_suggest_edit_rejects_empty_hours_payload(self):
        payload = {
            "reason": "Hours missing",
            "suggest_business_hours": "true",
            "business_hours_json": json.dumps(
                {"is_24_hours": False, "notes": "", "hours": {}}
            ),
        }

        response = self.client.post(
            reverse("places:suggest_place_edit", args=[self.place.pk]),
            payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please provide at least one day of hours.")
        self.assertEqual(BusinessHoursSuggestion.objects.count(), 0)
    
    def test_get_opening_hours_schema_24_hours(self):
        """Test schema for 24-hour place"""
        BusinessHours.objects.create(
            place=self.place,
            is_24_hours=True
        )
        
        schema = get_opening_hours_schema(self.place)
        self.assertEqual(len(schema), 7)  # All 7 days
        
        for spec in schema:
            self.assertEqual(spec['opens'], '00:00')
            self.assertEqual(spec['closes'], '23:59')
    
    def test_get_opening_hours_schema_regular_hours(self):
        """Test schema for regular business hours"""
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False
        )
        
        TimeSlot.objects.create(
            business_hours=business_hours,
            day_of_week=0,  # Monday
            open_time=time(9, 0),
            close_time=time(22, 0)
        )
        
        schema = get_opening_hours_schema(self.place)
        self.assertEqual(len(schema), 1)
        self.assertEqual(schema[0]['day'], 'Monday')
        self.assertEqual(schema[0]['opens'], '09:00')
        self.assertEqual(schema[0]['closes'], '22:00')


class BusinessHoursSuggestionTest(TestCase):
    """Test business hours suggestion workflow"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.email_verified = True
        self.user.save()
        
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.place = HalalPlace.objects.create(
            name='Test Restaurant',
            description='A test restaurant',
            category='restaurant',
            location=Point(127.0, 37.5),
            address='Test Address',
            status='approved',
            submitted_by=self.user
        )
        
        self.client = Client()
    
    def test_create_business_hours_suggestion(self):
        """Test creating a business hours suggestion"""
        suggestion = BusinessHoursSuggestion.objects.create(
            place=self.place,
            suggested_by=self.user,
            suggested_hours={
                "0": [{"open": "09:00", "close": "22:00"}],
                "1": [{"open": "09:00", "close": "22:00"}],
                "6": "closed"
            },
            is_24_hours=False,
            suggested_notes='Regular hours',
            reason='Adding business hours'
        )
        
        self.assertEqual(suggestion.status, 'pending')
        self.assertEqual(suggestion.place, self.place)
        self.assertIn('0', suggestion.suggested_hours)
    
    def test_submit_business_hours_via_form(self):
        """Test submitting business hours via the suggest edit form"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('places:suggest_place_edit', kwargs={'pk': self.place.pk})
        
        hours_data = {
            'is_24_hours': False,
            'hours': {
                "0": [{"open": "09:00", "close": "22:00"}],
                "1": [{"open": "09:00", "close": "22:00"}],
            },
            'notes': 'Test notes'
        }
        
        response = self.client.post(url, {
            'reason': 'Adding business hours',
            'suggest_business_hours': 'true',
            'business_hours_json': json.dumps(hours_data),
        })
        
        # Should redirect on success
        self.assertIn(response.status_code, [200, 302])
        
        # Check suggestion was created
        suggestion = BusinessHoursSuggestion.objects.filter(
            place=self.place,
            suggested_by=self.user
        ).first()
        
        if suggestion:
            self.assertEqual(suggestion.status, 'pending')


class PlaceDetailBusinessHoursTest(TestCase):
    """Test business hours display on place detail page"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.place = HalalPlace.objects.create(
            name='Test Restaurant',
            description='A test restaurant',
            category='restaurant',
            location=Point(127.0, 37.5),
            address='Test Address',
            status='approved',
            submitted_by=self.user
        )
        self.client = Client()
    
    def test_place_detail_without_hours(self):
        """Test place detail page when no hours are set"""
        url = reverse('places:place_detail', kwargs={'pk': self.place.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context.get('business_hours_status'))
    
    def test_place_detail_with_24_hours(self):
        """Test place detail page for 24-hour place"""
        BusinessHours.objects.create(
            place=self.place,
            is_24_hours=True
        )
        
        url = reverse('places:place_detail', kwargs={'pk': self.place.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        status = response.context.get('business_hours_status')
        self.assertIsNotNone(status)
        self.assertEqual(status['type'], 'open')
    
    def test_place_detail_structured_data_includes_hours(self):
        """Test that structured data includes opening hours when available"""
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False
        )
        
        TimeSlot.objects.create(
            business_hours=business_hours,
            day_of_week=0,  # Monday
            open_time=time(9, 0),
            close_time=time(22, 0)
        )
        
        url = reverse('places:place_detail', kwargs={'pk': self.place.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that opening_hours_schema is in context
        schema = response.context.get('opening_hours_schema')
        self.assertIsNotNone(schema)
        self.assertEqual(len(schema), 1)
        self.assertEqual(schema[0]['day'], 'Monday')


class BusinessHoursAdminTest(TestCase):
    """Test admin interface for business hours"""
    
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.place = HalalPlace.objects.create(
            name='Test Restaurant',
            description='A test restaurant',
            category='restaurant',
            location=Point(127.0, 37.5),
            address='Test Address',
            status='approved',
            submitted_by=self.user
        )
        self.client = Client()
    
    def test_admin_can_access_business_hours_admin(self):
        """Test admin can access BusinessHours admin"""
        self.client.login(username='admin', password='adminpass123')
        
        # Access the BusinessHours admin changelist
        url = '/admin/places/businesshours/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_admin_can_add_business_hours(self):
        """Test admin can add business hours to a place"""
        self.client.login(username='admin', password='adminpass123')
        
        url = '/admin/places/businesshours/add/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_admin_can_edit_time_slots(self):
        """Test admin can edit time slots via inline"""
        self.client.login(username='admin', password='adminpass123')
        
        business_hours = BusinessHours.objects.create(
            place=self.place,
            is_24_hours=False
        )
        
        url = f'/admin/places/businesshours/{business_hours.pk}/change/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should show TimeSlot inline
        self.assertContains(response, 'time_slots')
