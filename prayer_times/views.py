from django.shortcuts import render
from .utils import get_prayer_times
# Create your views here.

def prayer_times(request):
    data = get_prayer_times('Seoul', 'South Korea')
    context = {
        'data': data["data"],
    }
    return render(request, 'prayer_times/prayer_times.html', context)
