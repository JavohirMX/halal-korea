"""
Business Hours Utility Functions

Provides helper functions for calculating open/closed status,
formatting hours for display, and determining status badges.
"""

from datetime import datetime, time, timedelta
from typing import Optional, Tuple, Dict, List, Any
import pytz
import json

# Status thresholds (in minutes)
CLOSES_SOON_THRESHOLD = 60  # Show "Closes Soon" if closing within 60 min
OPENS_SOON_THRESHOLD = 120  # Show "Opens at..." if opening within 2 hours

# Day names for display
DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DAY_NAMES_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


class BusinessHoursParseError(ValueError):
    """Raised when business hours payload is invalid."""


def parse_business_hours_payload(payload: str) -> Optional[Dict[str, Any]]:
    """
    Parse and validate business hours payload JSON from the editor.

    Returns normalized dict: {"is_24_hours": bool, "notes": str, "hours": dict}
    """
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise BusinessHoursParseError("Invalid business hours data.") from exc

    if not isinstance(data, dict):
        raise BusinessHoursParseError("Invalid business hours format.")

    is_24_hours = bool(data.get("is_24_hours", False))
    notes = data.get("notes") or ""
    hours_data = data.get("hours") or {}

    if is_24_hours:
        return {
            "is_24_hours": True,
            "notes": notes,
            "hours": {},
        }

    if not isinstance(hours_data, dict) or len(hours_data) == 0:
        raise BusinessHoursParseError("Please provide at least one day of hours.")

    normalized_hours: Dict[str, Any] = {}

    for day_key, day_value in hours_data.items():
        try:
            day_num = int(day_key)
        except (TypeError, ValueError) as exc:
            raise BusinessHoursParseError("Invalid day value in hours.") from exc

        if day_num < 0 or day_num > 6:
            raise BusinessHoursParseError("Invalid day value in hours.")

        day_key_str = str(day_num)

        if day_value == "closed":
            normalized_hours[day_key_str] = "closed"
            continue

        if not isinstance(day_value, list) or len(day_value) == 0:
            raise BusinessHoursParseError(
                "Each open day needs at least one time slot."
            )

        normalized_slots = []
        for slot in day_value:
            if not isinstance(slot, dict):
                raise BusinessHoursParseError("Invalid time slot format.")

            open_time = slot.get("open")
            close_time = slot.get("close")
            if not open_time or not close_time:
                raise BusinessHoursParseError(
                    "Each time slot needs both open and close times."
                )
            try:
                datetime.strptime(open_time, "%H:%M")
                datetime.strptime(close_time, "%H:%M")
            except ValueError as exc:
                raise BusinessHoursParseError(
                    "Invalid time format. Use HH:MM."
                ) from exc

            normalized_slots.append({"open": open_time, "close": close_time})

        normalized_hours[day_key_str] = normalized_slots

    return {
        "is_24_hours": False,
        "notes": notes,
        "hours": normalized_hours,
    }


def build_existing_hours_data_from_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert editor payload into existing_hours_data format for prefill."""
    if not isinstance(payload, dict):
        return None

    existing = {
        "is_24_hours": bool(payload.get("is_24_hours", False)),
        "notes": payload.get("notes") or "",
        "slots": {},
    }

    hours = payload.get("hours") or {}
    if not isinstance(hours, dict):
        return existing

    for day_key, day_value in hours.items():
        day_key_str = str(day_key)
        if day_value == "closed":
            existing["slots"][day_key_str] = [
                {"is_closed": True, "open": "", "close": ""}
            ]
            continue

        if isinstance(day_value, list):
            slots = []
            for slot in day_value:
                if not isinstance(slot, dict):
                    continue
                slots.append(
                    {
                        "is_closed": False,
                        "open": slot.get("open") or "",
                        "close": slot.get("close") or "",
                    }
                )
            if slots:
                existing["slots"][day_key_str] = slots

    return existing


def get_korea_time() -> datetime:
    """Get current time in Korea timezone."""
    korea_tz = pytz.timezone('Asia/Seoul')
    return datetime.now(korea_tz)


def get_place_status(place) -> Dict[str, Any]:
    """
    Get the current open/closed status of a place.
    
    Returns a dict with:
        - type: 'open' | 'closed' | 'closes_soon' | 'opens_at' | 'temp_closed'
        - time: Optional time string (e.g., "22:00" for closes_soon/opens_at)
        - message: Human-readable status message
    """
    # Check for temporary closure first
    if place.temporary_closure_until:
        now = get_korea_time().date()
        if now <= place.temporary_closure_until:
            return {
                'type': 'temp_closed',
                'time': None,
                'message': f"Temporarily closed until {place.temporary_closure_until.strftime('%b %d')}"
            }
    
    # Check if place has business hours
    try:
        business_hours = place.business_hours
    except Exception:
        # No business hours set - return None to indicate unknown status
        return None
    
    if not business_hours:
        return None
    
    # Handle 24-hour places
    if business_hours.is_24_hours:
        return {
            'type': 'open',
            'time': None,
            'message': 'Open 24 Hours'
        }
    
    now = get_korea_time()
    current_day = now.weekday()  # Monday = 0
    current_time = now.time()
    
    # Get today's time slots
    today_slots = [slot for slot in business_hours.time_slots.all() if slot.day_of_week == current_day]
    
    # Check if day is explicitly closed
    if any(slot.is_closed for slot in today_slots):
        # Check if opens tomorrow within threshold
        next_opening = _get_next_opening(business_hours, current_day, current_time)
        if next_opening:
            return {
                'type': 'opens_at',
                'time': next_opening['time'].strftime('%H:%M'),
                'message': f"Opens {next_opening['day_str']} at {next_opening['time'].strftime('%H:%M')}"
            }
        return {
            'type': 'closed',
            'time': None,
            'message': 'Closed today'
        }
    
    # Check current time against time slots
    for slot in today_slots:
        if slot.open_time and slot.close_time:
            # Handle overnight closing (e.g., 22:00 - 02:00)
            if slot.close_time < slot.open_time:
                # Opens before midnight, closes after
                if current_time >= slot.open_time or current_time < slot.close_time:
                    # Check if closes soon
                    if current_time >= slot.open_time:
                        # We're in the pre-midnight part
                        minutes_until_midnight = (24 * 60) - (current_time.hour * 60 + current_time.minute)
                        minutes_until_close = minutes_until_midnight + (slot.close_time.hour * 60 + slot.close_time.minute)
                    else:
                        # We're in the post-midnight part
                        minutes_until_close = (slot.close_time.hour * 60 + slot.close_time.minute) - (current_time.hour * 60 + current_time.minute)
                    
                    if minutes_until_close <= CLOSES_SOON_THRESHOLD:
                        return {
                            'type': 'closes_soon',
                            'time': slot.close_time.strftime('%H:%M'),
                            'message': f"Closes at {slot.close_time.strftime('%H:%M')}"
                        }
                    return {
                        'type': 'open',
                        'time': slot.close_time.strftime('%H:%M'),
                        'message': f"Open until {slot.close_time.strftime('%H:%M')}"
                    }
            else:
                # Normal same-day hours
                if slot.open_time <= current_time < slot.close_time:
                    # Currently open - check if closes soon
                    close_datetime = datetime.combine(now.date(), slot.close_time)
                    now_datetime = datetime.combine(now.date(), current_time)
                    minutes_until_close = (close_datetime - now_datetime).total_seconds() / 60
                    
                    if minutes_until_close <= CLOSES_SOON_THRESHOLD:
                        return {
                            'type': 'closes_soon',
                            'time': slot.close_time.strftime('%H:%M'),
                            'message': f"Closes at {slot.close_time.strftime('%H:%M')}"
                        }
                    return {
                        'type': 'open',
                        'time': slot.close_time.strftime('%H:%M'),
                        'message': f"Open until {slot.close_time.strftime('%H:%M')}"
                    }
    
    # Not currently open - check if opens soon
    next_opening = _get_next_opening(business_hours, current_day, current_time)
    if next_opening:
        # Calculate minutes until opening
        if next_opening['is_today']:
            now_minutes = current_time.hour * 60 + current_time.minute
            open_minutes = next_opening['time'].hour * 60 + next_opening['time'].minute
            minutes_until_open = open_minutes - now_minutes
            
            if minutes_until_open <= OPENS_SOON_THRESHOLD:
                return {
                    'type': 'opens_at',
                    'time': next_opening['time'].strftime('%H:%M'),
                    'message': f"Opens at {next_opening['time'].strftime('%H:%M')}"
                }
        
        return {
            'type': 'closed',
            'time': next_opening['time'].strftime('%H:%M'),
            'message': f"Opens {next_opening['day_str']} at {next_opening['time'].strftime('%H:%M')}"
        }
    
    return {
        'type': 'closed',
        'time': None,
        'message': 'Closed'
    }


def _get_next_opening(business_hours, current_day: int, current_time: time) -> Optional[Dict]:
    """Find the next opening time within the next 7 days."""
    all_slots = list(business_hours.time_slots.all())
    for day_offset in range(7):
        check_day = (current_day + day_offset) % 7
        slots = [
            slot for slot in all_slots
            if slot.day_of_week == check_day and not slot.is_closed
        ]
        
        for slot in slots:
            if slot.open_time:
                # If same day, only consider future openings
                if day_offset == 0 and slot.open_time <= current_time:
                    continue
                
                # Found next opening
                if day_offset == 0:
                    day_str = "today"
                elif day_offset == 1:
                    day_str = "tomorrow"
                else:
                    day_str = DAY_NAMES[check_day]
                
                return {
                    'time': slot.open_time,
                    'day': check_day,
                    'day_str': day_str,
                    'is_today': day_offset == 0
                }
    
    return None


def is_place_open(place) -> bool:
    """Simple boolean check if place is currently open."""
    status = get_place_status(place)
    if status is None:
        return False
    return status['type'] in ('open', 'closes_soon')


def get_today_hours(place) -> str:
    """Get formatted hours string for today."""
    try:
        business_hours = place.business_hours
    except Exception:
        return "Hours not available"
    
    if not business_hours:
        return "Hours not available"
    
    if business_hours.is_24_hours:
        return "Open 24 Hours"
    
    now = get_korea_time()
    current_day = now.weekday()
    
    slots = [slot for slot in business_hours.time_slots.all() if slot.day_of_week == current_day]

    if not slots:
        return "Hours not set"
    
    if any(slot.is_closed for slot in slots):
        return "Closed"
    
    # Format time slots
    hours_parts = []
    for slot in slots:
        if slot.open_time and slot.close_time:
            hours_parts.append(f"{slot.open_time.strftime('%H:%M')} - {slot.close_time.strftime('%H:%M')}")
    
    if not hours_parts:
        return "Hours not set"
    
    return ", ".join(hours_parts)


def get_weekly_hours(place) -> List[Dict[str, Any]]:
    """
    Get formatted hours for all 7 days of the week.
    
    Returns a list of dicts, one per day:
        - day_num: 0-6
        - name: "Monday", "Tuesday", etc.
        - name_short: "Mon", "Tue", etc.
        - hours: Formatted hours string or "Closed"
        - is_closed: Boolean
        - is_today: Boolean
    """
    try:
        business_hours = place.business_hours
    except Exception:
        return []
    
    if not business_hours:
        return []
    
    now = get_korea_time()
    current_day = now.weekday()
    
    weekly = []
    all_slots = list(business_hours.time_slots.all())

    for day_num in range(7):
        day_data = {
            'day_num': day_num,
            'name': DAY_NAMES[day_num],
            'name_short': DAY_NAMES_SHORT[day_num],
            'is_today': day_num == current_day,
            'is_closed': False,
            'hours': ''
        }

        if business_hours.is_24_hours:
            day_data['hours'] = '24 Hours'
        else:
            slots = [slot for slot in all_slots if slot.day_of_week == day_num]
            
            if not slots:
                day_data['hours'] = 'Not set'
            elif any(slot.is_closed for slot in slots):
                day_data['is_closed'] = True
                day_data['hours'] = 'Closed'
            else:
                hours_parts = []
                for slot in slots:
                    if slot.open_time and slot.close_time:
                        hours_parts.append(f"{slot.open_time.strftime('%H:%M')} - {slot.close_time.strftime('%H:%M')}")
                day_data['hours'] = ", ".join(hours_parts) if hours_parts else 'Not set'
        
        weekly.append(day_data)
    
    return weekly


def get_opening_hours_schema(place) -> List[Dict[str, str]]:
    """
    Get business hours in schema.org OpeningHoursSpecification format.
    
    Returns a list of dicts for JSON-LD structured data.
    """
    try:
        business_hours = place.business_hours
    except Exception:
        return []
    
    if not business_hours:
        return []
    
    SCHEMA_DAY_NAMES = [
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
        'Friday', 'Saturday', 'Sunday'
    ]
    
    specs = []
    
    if business_hours.is_24_hours:
        for day_name in SCHEMA_DAY_NAMES:
            specs.append({
                'day': day_name,
                'opens': '00:00',
                'closes': '23:59'
            })
    else:
        for slot in business_hours.time_slots.all():
            if not slot.is_closed and slot.open_time and slot.close_time:
                specs.append({
                    'day': SCHEMA_DAY_NAMES[slot.day_of_week],
                    'opens': slot.open_time.strftime('%H:%M'),
                    'closes': slot.close_time.strftime('%H:%M')
                })
    
    return specs
