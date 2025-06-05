import json
from geopy.geocoders import Nominatim, GoogleV3, ArcGIS
from django.contrib.gis.geos import Point
import re
import os
from datetime import datetime
import pytz

# Initialize geocoders
nominatim = Nominatim(user_agent="halal_place_converter")

# Google Geocoding API (requires API key)
google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
google = GoogleV3(api_key=google_api_key) if google_api_key else None

# ArcGIS (free alternative, no API key needed)
arcgis = ArcGIS()

def clean_korean_address(address):
    """Clean and simplify Korean address for better geocoding."""
    # Remove floor information (층, 호수 등)
    address = re.sub(r'\s*\d+층.*', '', address)
    address = re.sub(r'\s*\d+호.*', '', address)
    address = re.sub(r'\s*지하\d*층.*', '', address)  # basement floors
    
    # Remove detailed building numbers and try broader area
    # Remove specific lot numbers like "936-3번지", "123번지"
    address = re.sub(r'\s*\d+-?\d*번지.*', '', address)
    
    # Remove building names in parentheses
    address = re.sub(r'\s*\([^)]*\)', '', address)
    
    # Remove specific building/apartment complex names
    address = re.sub(r'\s*\w+아파트.*', '', address)
    address = re.sub(r'\s*\w+빌딩.*', '', address)
    address = re.sub(r'\s*\w+타워.*', '', address)
    
    # Remove extra whitespace
    address = re.sub(r'\s+', ' ', address).strip()
    
    return address

def try_multiple_address_formats(original_address):
    """Generate multiple address formats to try for geocoding."""
    addresses_to_try = [original_address]
    
    # Try cleaned version
    cleaned = clean_korean_address(original_address)
    if cleaned != original_address and cleaned:
        addresses_to_try.append(cleaned)
    
    # Try with just city/district/dong
    parts = original_address.split()
    if len(parts) >= 4:
        # Try "경기도 안산시 단원구 원곡동" format
        simplified = ' '.join(parts[:4])
        addresses_to_try.append(simplified)
    
    if len(parts) >= 3:
        # Try "안산시 단원구 원곡동" format (without province)
        simplified = ' '.join(parts[1:4])
        addresses_to_try.append(simplified)
    
    # Try English translated versions
    korean_to_english = {
        '경기도': 'Gyeonggi-do',
        '서울특별시': 'Seoul',
        '서울시': 'Seoul', 
        '서울': 'Seoul',
        '부산광역시': 'Busan',
        '부산시': 'Busan',
        '부산': 'Busan',
        '인천광역시': 'Incheon',
        '인천시': 'Incheon',
        '인천': 'Incheon',
        '안산시': 'Ansan-si',
        '안산': 'Ansan',
        '단원구': 'Danwon-gu',
        '원곡동': 'Wongok-dong',
        '시': '-si',
        '구': '-gu',
        '동': '-dong',
        '읍': '-eup',
        '면': '-myeon'
    }
    
    # Create English version
    english_addr = original_address
    for korean, english in korean_to_english.items():
        english_addr = english_addr.replace(korean, english)
    
    english_cleaned = clean_korean_address(english_addr)
    if english_cleaned != original_address:
        addresses_to_try.append(f"{english_cleaned}, South Korea")
    
    # Try adding "South Korea" to various formats
    addresses_to_try.append(f"{original_address}, South Korea")
    addresses_to_try.append(f"{cleaned}, South Korea")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_addresses = []
    for addr in addresses_to_try:
        if addr and addr not in seen:
            seen.add(addr)
            unique_addresses.append(addr)
    
    return unique_addresses

def geocode_with_service(address, service, service_name):
    """Try geocoding with a specific service."""
    try:
        if service_name == "Google" and service:
            location = service.geocode(address, timeout=15, language='ko', region='kr')
        else:
            location = service.geocode(address, timeout=15)
        
        if location:
            print(f"  ✓ Success with {service_name}: {location.address}")
            return Point(location.longitude, location.latitude, srid=4326)
        else:
            print(f"  ✗ No results from {service_name}")
            return None
    except Exception as e:
        print(f"  ✗ Error with {service_name}: {str(e)}")
        return None

def geocode_address(address):
    """Geocode an address to get latitude and longitude with multiple fallback strategies."""
    print(f"Attempting to geocode: {address}")
    
    # Get multiple address formats to try
    addresses_to_try = try_multiple_address_formats(address)
    
    # List of geocoding services to try
    services = [
        (nominatim, "Nominatim"),
        (google, "Google") if google else None,
        (arcgis, "ArcGIS")
    ]
    # Remove None entries
    services = [s for s in services if s is not None]
    
    # Try each address format with each service
    for i, addr in enumerate(addresses_to_try):
        print(f"Trying format {i+1}: {addr}")
        
        for service, service_name in services:
            result = geocode_with_service(addr, service, service_name)
            if result:
                return result
    
    print(f"❌ All geocoding attempts failed for address: {address}")
    return None

def get_google_map_link(lat, lng):
    """Generate Google Maps URL from coordinates."""
    return f"https://www.google.com/maps?q={lat},{lng}"

def get_kakao_map_link(lat, lng):
    """Generate Kakao Map URL from coordinates."""
    return f"https://map.kakao.com/link/map/{lat},{lng}"

def get_naver_map_link(lat, lng):
    """Generate Naver Map URL from coordinates."""
    return f"https://map.naver.com/v5/?c={lat},{lng},15,0,0"

def transform_data(input_file, output_file):
    """Transform input JSON to full HalalPlace model data with map links."""
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Prepare the output data
    full_data = []

    for entry in data:
        # Use category as-is (mosque or prayer_room)
        category = entry['category']
        if category not in ['mosque', 'prayer_room']:
            print(f"Invalid category {category} for {entry['name']}, skipping")
            continue
        
        # Geocode the address
        location = geocode_address(entry['address'])
        if not location:
            print(f"Skipping entry {entry['name']} due to geocoding failure")
            continue

        # Extract latitude and longitude
        lat, lng = location.y, location.x

        # Generate map links
        google_map_link = get_google_map_link(lat, lng)
        kakao_map_link = get_kakao_map_link(lat, lng)
        naver_map_link = get_naver_map_link(lat, lng)

        # Create the full data structure compatible with Django model
        full_entry = {
            'name': entry['name'],
            'description': entry['description'],
            'category': category,
            'location': f"POINT({lng} {lat})",  # Django Point format in WKT
            'address': entry['address'],
            'phone_number': None,  # Not provided in JSON
            'website': None,  # Not provided in JSON
            'google_map_link': google_map_link,
            'kakao_map_link': kakao_map_link,
            'naver_map_link': naver_map_link,
            'photo_urls': [],  # Empty list as placeholder
            'status': 'approved',  # Set to approved as requested
            # Remove created_at and updated_at - Django will auto-set these
            'submitted_by': None  # Will need to be set to actual user ID when importing
        }
        full_data.append(full_entry)

    # Write the output JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=4)

    print(f"Transformed {len(full_data)} entries and saved to {output_file}")

def transform_data_to_fixtures(input_file, output_file):
    """Transform input JSON to Django fixtures format."""
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Prepare the fixture data
    fixtures = []
    pk_counter = 1
    current_time = datetime.now(pytz.UTC).isoformat()

    for entry in data:
        # Use category as-is (mosque or prayer_room)
        category = entry['category']
        if category not in ['mosque', 'prayer_room']:
            print(f"Invalid category {category} for {entry['name']}, skipping")
            continue
        
        # Geocode the address
        location = geocode_address(entry['address'])
        if not location:
            print(f"Skipping entry {entry['name']} due to geocoding failure")
            continue

        # Extract latitude and longitude
        lat, lng = location.y, location.x

        # Generate map links
        google_map_link = get_google_map_link(lat, lng)
        kakao_map_link = get_kakao_map_link(lat, lng)
        naver_map_link = get_naver_map_link(lat, lng)

        # Create Django fixture format
        fixture = {
            "model": "places.halalplace",
            "pk": pk_counter,
            "fields": {
                'name': entry['name'],
                'description': entry['description'],
                'category': category,
                'location': f"POINT({lng} {lat})",
                'address': entry['address'],
                'phone_number': None,
                'website': None,
                'google_map_link': google_map_link,
                'kakao_map_link': kakao_map_link,
                'naver_map_link': naver_map_link,
                'photo_urls': [],
                'status': 'approved',
                'created_at': current_time,
                'updated_at': current_time,
                'submitted_by': None
            }
        }
        fixtures.append(fixture)
        pk_counter += 1

    # Write the fixture JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=4)

    print(f"Created {len(fixtures)} fixtures and saved to {output_file}")

if __name__ == '__main__':
    input_file = 'mosques.json'  # Path to your input JSON file
    output_file = 'full_mosques.json'  # Path to the output JSON file
    fixtures_file = 'mosques_fixtures.json'  # Path to Django fixtures file
    
    # Generate both formats
    transform_data(input_file, output_file)
    transform_data_to_fixtures(input_file, fixtures_file)