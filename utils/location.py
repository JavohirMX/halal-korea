import requests

def get_client_ip(request):
    """Extracts the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
        
     # If running locally, get public IP
    if ip in ["127.0.0.1", "localhost"]:
        try:
            ip = requests.get("https://api64.ipify.org?format=json").json().get("ip")
        except requests.RequestException:
            ip = "UNKNOWN"
            
    return ip

def get_ip_location(ip):
    """Fetches location details for the given IP address using an external API."""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}')
        data = response.json()
        if data["status"] == "success":
            return {
                "ip": ip,
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "isp": data.get("isp"),
            }
    except requests.RequestException:
        return {"error": "Could not retrieve location data"}
    return {"error": "Invalid IP or failed lookup"}

if __name__ == '__main__':
    ip = '175.114.21.96'
    location = get_ip_location(ip)
    
    print(location)