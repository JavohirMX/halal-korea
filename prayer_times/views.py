from django.shortcuts import render

# Create your views here.

def prayer_times(request):
    return render(request, 'prayer_times/prayer_times.html')
