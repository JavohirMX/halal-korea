import requests
from datetime import datetime
from django.core.cache import cache
from .models import PrayerTimeCache
import logging

logger = logging.getLogger(__name__)

def get_fallback_prayer_times():
    """Return fallback prayer times in case of API failure"""
    return {
        "code": 200,
        "status": "OK",
        "data": {
            "timings": {
                "Fajr": "05:00",
                "Sunrise": "07:00",
                "Dhuhr": "12:00",
                "Asr": "15:00",
                "Maghrib": "18:00",
                "Isha": "19:30"
            },
            "date": {
                "gregorian": {
                    "date": datetime.now().strftime("%d-%m-%Y"),
                    "day": datetime.now().day,
                    "month": {"en": datetime.now().strftime("%B")},
                    "year": datetime.now().year,
                    "weekday": {"en": datetime.now().strftime("%A")}
                },
                "hijri": {
                    "date": "01-01-1445",
                    "day": "1",
                    "month": {"en": "Muharram"},
                    "year": "1445",
                    "weekday": {"en": "Monday"}
                }
            }
        }
    }

def get_prayer_times(city, country, date=None, method=None, school=1):
    """
    Fetches the prayer times for a specified city and country on a given date.
    Implements caching and timeout handling.
    """
    if date is None:
        date = datetime.now().strftime('%d-%m-%Y')
        
    # Try to get from database cache first
    cached_data = PrayerTimeCache.get_cached_times(city, country, date, method, school)
    if cached_data:
        return cached_data
        
    # Try to get from memory cache
    cache_key = f"prayer_times_{city}_{country}_{date}_{method}_{school}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
        
    # If not in cache, make API call
    url = f'https://api.aladhan.com/v1/timingsByCity/{date}'
    params = {
        'city': city,
        'country': country,
        'method': method,
        'school': school,
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)  # 5 second timeout
        data = response.json()
        
        # Cache the result
        cache.set(cache_key, data, 3600)  # Cache for 1 hour
        PrayerTimeCache.set_cached_times(city, country, date, data, method, school)
        
        return data
    except (requests.Timeout, requests.RequestException) as e:
        logger.error(f"Error fetching prayer times: {str(e)}")
        return get_fallback_prayer_times()

def get_prayer_times_ll(latitude, longitude, date=None, method=None, school=1):
    """
    Fetches the prayer times for a specified latitude and longitude on a given date.
    Implements caching and timeout handling.
    """
    if date is None:
        date = datetime.now().strftime('%d-%m-%Y')
        
    # Try to get from memory cache
    cache_key = f"prayer_times_ll_{latitude}_{longitude}_{date}_{method}_{school}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
        
    # If not in cache, make API call
    url = f'https://api.aladhan.com/v1/timings/{date}'
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'method': method,
        'school': school,
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)  # 5 second timeout
        data = response.json()
        
        # Cache the result
        cache.set(cache_key, data, 3600)  # Cache for 1 hour
        
        return data
    except (requests.Timeout, requests.RequestException) as e:
        logger.error(f"Error fetching prayer times: {str(e)}")
        return get_fallback_prayer_times()

""" Example response for get_prayer_times
{
"code": 200,
"status": "OK",
"data": {
    "timings": {
    "Fajr": "06:03",
    "Sunrise": "08:06",
    "Dhuhr": "12:04",
    "Asr": "13:44",
    "Sunset": "16:03",
    "Maghrib": "16:03",
    "Isha": "17:59",
    "Imsak": "05:53",
    "Midnight": "00:04",
    "Firstthird": "21:24",
    "Lastthird": "02:45"
    },
    "date": {
    "readable": "01 Jan 2025",
    "timestamp": "1735714800",
    "hijri": {
        "date": "01-07-1446",
        "format": "DD-MM-YYYY",
        "day": "1",
        "weekday": {
        "en": "Al Arba'a",
        "ar": "الاربعاء"
        },
        "month": {
        "number": 7,
        "en": "Rajab",
        "ar": "رَجَب",
        "days": 30
        },
        "year": "1446",
        "designation": {
        "abbreviated": "AH",
        "expanded": "Anno Hegirae"
        },
        "holidays": [
        "Beginning of the holy months"
        ],
        "adjustedHolidays": [],
        "method": "HJCoSA"
    },
    "gregorian": {
        "date": "01-01-2025",
        "format": "DD-MM-YYYY",
        "day": "01",
        "weekday": {
        "en": "Wednesday"
        },
        "month": {
        "number": 1,
        "en": "January"
        },
        "year": "2025",
        "designation": {
        "abbreviated": "AD",
        "expanded": "Anno Domini"
        },
        "lunarSighting": false
    }
    },
    "meta": {
    "latitude": 51.5194682,
    "longitude": -0.1360365,
    "timezone": "UTC",
    "method": {
        "id": 3,
        "name": "Muslim World League",
        "params": {
        "Fajr": 18,
        "Isha": 17
        },
        "location": {
        "latitude": 51.5194682,
        "longitude": -0.1360365
        }
    },
    "latitudeAdjustmentMethod": "ANGLE_BASED",
    "midnightMode": "STANDARD",
    "school": "STANDARD",
    "offset": {
        "Imsak": 0,
        "Fajr": 0,
        "Sunrise": 0,
        "Dhuhr": 0,
        "Asr": 0,
        "Sunset": 0,
        "Maghrib": 0,
        "Isha": 0,
        "Midnight": 0
    }
    }
}
}
"""
""" Example response for get_prayer_times_ll
{
  "code": 200,
  "status": "OK",
  "data": {
    "timings": {
      "Fajr": "06:03",
      "Sunrise": "08:06",
      "Dhuhr": "12:04",
      "Asr": "13:44",
      "Sunset": "16:03",
      "Maghrib": "16:03",
      "Isha": "17:59",
      "Imsak": "05:53",
      "Midnight": "00:04",
      "Firstthird": "21:24",
      "Lastthird": "02:45"
    },
    "date": {
      "readable": "01 Jan 2025",
      "timestamp": "1735714800",
      "hijri": {
        "date": "01-07-1446",
        "format": "DD-MM-YYYY",
        "day": "1",
        "weekday": {
          "en": "Al Arba'a",
          "ar": "الاربعاء"
        },
        "month": {
          "number": 7,
          "en": "Rajab",
          "ar": "رَجَب",
          "days": 30
        },
        "year": "1446",
        "designation": {
          "abbreviated": "AH",
          "expanded": "Anno Hegirae"
        },
        "holidays": [
          "Beginning of the holy months"
        ],
        "adjustedHolidays": [],
        "method": "HJCoSA"
      },
      "gregorian": {
        "date": "01-01-2025",
        "format": "DD-MM-YYYY",
        "day": "01",
        "weekday": {
          "en": "Wednesday"
        },
        "month": {
          "number": 1,
          "en": "January"
        },
        "year": "2025",
        "designation": {
          "abbreviated": "AD",
          "expanded": "Anno Domini"
        },
        "lunarSighting": false
      }
    },
    "meta": {
      "latitude": 51.5194682,
      "longitude": -0.1360365,
      "timezone": "UTC",
      "method": {
        "id": 3,
        "name": "Muslim World League",
        "params": {
          "Fajr": 18,
          "Isha": 17
        },
        "location": {
          "latitude": 51.5194682,
          "longitude": -0.1360365
        }
      },
      "latitudeAdjustmentMethod": "ANGLE_BASED",
      "midnightMode": "STANDARD",
      "school": "STANDARD",
      "offset": {
        "Imsak": 0,
        "Fajr": 0,
        "Sunrise": 0,
        "Dhuhr": 0,
        "Asr": 0,
        "Sunset": 0,
        "Maghrib": 0,
        "Isha": 0,
        "Midnight": 0
      }
    }
  }
}
"""
 

if __name__ == '__main__':
    city = 'Seoul'
    country = 'South Korea'
    data = get_prayer_times(city, country)
    print(data)