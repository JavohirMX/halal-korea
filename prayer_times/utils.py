import requests
from datetime import datetime

def get_prayer_times(city, country, date=None, method=None, school=1):
    """
    Fetches the prayer times for a specified city and country on a given date.

    This function retrieves prayer times from the Aladhan API based on the provided city,
    country, and optional date. If no date is provided, the current date is used. The method
    and school parameters can be adjusted to specify the calculation method and school of thought
    for the prayer times.

    Args:
        city (str): The name of the city for which to retrieve prayer times.
        country (str): The name of the country where the city is located.
        date (str, optional): The date for which to retrieve prayer times in 'dd-mm-yyyy' format. 
                              Defaults to None, which uses the current date.
        method (int, optional): The calculation method for prayer times. Defaults to None.
        school (int, optional): The school of thought for prayer times. Defaults to 1 (Hanafi).

    Returns:
        dict: A dictionary containing the prayer times and additional information from the API response.
    """
    
    if date is None:
        date = datetime.now().strftime('%d-%m-%Y')
    url = f'http://api.aladhan.com/v1/timingsByCity/{date}'
    params = {
        'city': city,
        'country': country,
        'method': method, # 0-23
        'school': school, # Shafi'i 0, Hanafi 1
    }
    response = requests.get(url, params=params)
    return response.json() 




def get_prayer_times_ll(latitude, longitude, date=None, method=None, school=1):
    """
    Fetches the prayer times for a specified latitude and longitude on a given date.

    This function retrieves prayer times from the Aladhan API based on the provided latitude,
    longitude, and optional date. If no date is provided, the current date is used. The method
    and school parameters can be adjusted to specify the calculation method and school of thought
    for the prayer times.

    Args:
        latitude (float): The latitude of the location for which to retrieve prayer times.
        longitude (float): The longitude of the location for which to retrieve prayer times.
        date (str, optional): The date for which to retrieve prayer times in 'dd-mm-yyyy' format. 
                              Defaults to None, which uses the current date.
        method (int, optional): The calculation method for prayer times. Defaults to None.
        school (int, optional): The school of thought for prayer times. Defaults to 1 (Hanafi).

    Returns:
        dict: A dictionary containing the prayer times and additional information from the API response.
    """
    
    if date is None:
        date = datetime.now().strftime('%d-%m-%Y')
    url = f'http://api.aladhan.com/v1/timings/{date}'
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'method': method, # 0-23
        'school': school, # Shafi'i 0, Hanafi 1
    }
    response = requests.get(url, params=params)
    return response.json()

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