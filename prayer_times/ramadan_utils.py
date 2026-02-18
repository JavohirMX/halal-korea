from datetime import date, timedelta
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

RAMADAN_CONFIG_CACHE_KEY = "ramadan_config_active"
RAMADAN_CONFIG_CACHE_TTL = 300  # 5 minutes


def get_active_ramadan_config():
    """Returns the active RamadanConfig for the current year, or None."""
    cached = cache.get(RAMADAN_CONFIG_CACHE_KEY)
    if cached is not None:
        return cached if cached != "__none__" else None

    from .models import RamadanConfig
    config = RamadanConfig.get_active_config()
    cache.set(RAMADAN_CONFIG_CACHE_KEY, config or "__none__", RAMADAN_CONFIG_CACHE_TTL)
    return config


def is_ramadan_active(target_date=None):
    """True if the given date (default today) falls within admin-configured Ramadan dates."""
    config = get_active_ramadan_config()
    if not config:
        return False
    target_date = target_date or date.today()
    return config.start_date <= target_date <= config.end_date


def get_ramadan_day_number(target_date=None):
    """Returns 1-based Ramadan day number, or None if not in Ramadan."""
    config = get_active_ramadan_config()
    if not config:
        return None
    target_date = target_date or date.today()
    if not (config.start_date <= target_date <= config.end_date):
        return None
    return (target_date - config.start_date).days + 1


def get_ramadan_date_range():
    """Returns a list of all dates in the configured Ramadan period."""
    config = get_active_ramadan_config()
    if not config:
        return []
    days = (config.end_date - config.start_date).days + 1
    return [config.start_date + timedelta(days=i) for i in range(days)]


def is_lailatul_qadr_night(day_number):
    """True for the odd nights of the last 10 days of Ramadan (21, 23, 25, 27, 29)."""
    return day_number in (21, 23, 25, 27, 29)


def get_ramadan_status():
    """
    Returns a dict describing the current Ramadan status:
    - before: Ramadan hasn't started yet (with days_until)
    - during: Currently Ramadan (with day_number, total_days)
    - after: Ramadan has ended
    - inactive: No config
    """
    config = get_active_ramadan_config()
    if not config:
        return {"status": "inactive"}

    today = date.today()

    if today < config.start_date:
        days_until = (config.start_date - today).days
        return {
            "status": "before",
            "days_until": days_until,
            "start_date": config.start_date,
            "end_date": config.end_date,
            "hijri_year": config.hijri_year,
            "total_days": config.total_days,
        }
    elif today > config.end_date:
        return {
            "status": "after",
            "hijri_year": config.hijri_year,
        }
    else:
        day_number = (today - config.start_date).days + 1
        return {
            "status": "during",
            "day_number": day_number,
            "total_days": config.total_days,
            "start_date": config.start_date,
            "end_date": config.end_date,
            "hijri_year": config.hijri_year,
            "is_lailatul_qadr": is_lailatul_qadr_night(day_number),
        }


def strip_timezone_suffix(time_str):
    """Strip the timezone suffix like ' (KST)' from AlAdhan time strings."""
    if not time_str:
        return time_str
    paren_idx = time_str.find(" (")
    if paren_idx != -1:
        return time_str[:paren_idx]
    return time_str


def calculate_fasting_duration(imsak_str, maghrib_str):
    """Calculate fasting duration between Imsak and Maghrib. Returns (hours, minutes)."""
    try:
        imsak_str = strip_timezone_suffix(imsak_str)
        maghrib_str = strip_timezone_suffix(maghrib_str)

        ih, im = map(int, imsak_str.split(":"))
        mh, mm = map(int, maghrib_str.split(":"))

        imsak_minutes = ih * 60 + im
        maghrib_minutes = mh * 60 + mm
        diff = maghrib_minutes - imsak_minutes

        if diff < 0:
            diff += 24 * 60

        return diff // 60, diff % 60
    except (ValueError, AttributeError):
        logger.warning(f"Could not calculate fasting duration: {imsak_str} -> {maghrib_str}")
        return None, None
