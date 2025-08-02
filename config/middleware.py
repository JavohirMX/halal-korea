"""
Middleware to handle admin access control
"""
from django.http import Http404
from django.urls import resolve


class AdminAccessMiddleware:
    """
    Middleware that returns 404 for admin URLs when accessed by non-admin users.
    Only allows admin access to authenticated staff users.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this is an admin URL
        try:
            resolved = resolve(request.path_info)
            is_admin_url = (
                resolved.url_name and 
                (resolved.url_name.startswith('admin:') or 
                 request.path_info.startswith('/admin/'))
            )
        except Exception:
            is_admin_url = request.path_info.startswith('/admin/')
        
        if is_admin_url:
            # For admin URLs, check if user is authenticated and is staff
            if not request.user.is_authenticated or not request.user.is_staff:
                # Return 404 for non-admin users
                raise Http404("Page not found")
        
        response = self.get_response(request)
        return response
