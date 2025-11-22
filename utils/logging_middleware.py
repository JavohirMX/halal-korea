"""
Middleware for enhanced logging capabilities.

Features:
- Request ID injection for correlation
- Automatic context setting
- Async logging support
"""

import uuid
import logging
from django.utils.deprecation import MiddlewareMixin
from utils.logging_utils import set_request_context

logger = logging.getLogger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware that adds a unique ID to each request for log correlation.
    
    The request ID is:
    1. Generated for each new request
    2. Added to the request object as request.id
    3. Added to response headers for client tracking
    4. Automatically included in all logs via context
    """
    
    def process_request(self, request):
        """Generate and attach request ID."""
        # Check if request ID already exists (e.g., from load balancer)
        request_id = request.META.get('HTTP_X_REQUEST_ID')
        
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Attach to request
        request.id = request_id
        
        # Set request context for logging
        try:
            set_request_context(request)
        except Exception as e:
            logger.warning(f"Failed to set request context: {e}")
    
    def process_response(self, request, response):
        """Add request ID to response headers."""
        if hasattr(request, 'id'):
            response['X-Request-ID'] = request.id
        
        return response
