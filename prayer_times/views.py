from django.shortcuts import render
from .utils import get_prayer_times
from utils.location import get_client_ip, get_ip_location
# Create your views here.

def prayer_times(request):
    ip = get_client_ip(request)
    location = get_ip_location(ip)
    data = get_prayer_times(location.get("city","Seoul"), location.get("country","South Korea"))
    context = {
        'data': data["data"],
        'location': location,
    }
    return render(request, 'prayer_times/prayer_times.html', context)
