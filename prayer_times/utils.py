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
 

if __name__ == '__main__':
    city = 'Seoul'
    country = 'South Korea'
    data = get_prayer_times(city, country)
    print(data)