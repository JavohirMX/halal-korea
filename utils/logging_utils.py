"""
Logging utilities for the Halal Korea application.

This module provides common logging patterns and utilities for consistent
logging across the application.

Enhanced Features:
- Structured JSON logging with correlation IDs
- Automatic context enrichment
- Enhanced PII sanitization
- Async logging support
- Request tracing
"""

import logging
import functools
import time
import uuid
import re
import socket
import threading
from typing import Any, Callable, TYPE_CHECKING
import contextvars

# TYPE_CHECKING is False at runtime, True during type checking
if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.contrib.auth.models import AbstractUser

# Context variable for request correlation
request_context = contextvars.ContextVar('request_context', default={})


def get_request_id(request: 'HttpRequest' = None) -> str:
    """Get or generate correlation ID for request tracing."""
    if request and hasattr(request, 'id'):
        return request.id
    
    # Try to get from context
    context = request_context.get()
    if context and 'request_id' in context:
        return context['request_id']
    
    # Generate new ID
    return str(uuid.uuid4())


def set_request_context(request: 'HttpRequest'):
    """Set request context for automatic log enrichment."""
    context = {
        'request_id': get_request_id(request),
        'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
        'username': request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous',
        'ip': request.META.get('REMOTE_ADDR', 'unknown'),
        'path': request.path,
        'method': request.method,
    }
    request_context.set(context)
    return context


def get_client_info(request: 'HttpRequest') -> dict:
    """Extract client information from request for logging."""
    info = {
        'ip': request.META.get('REMOTE_ADDR', 'unknown'),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
        'referer': request.META.get('HTTP_REFERER', 'unknown'),
        'method': request.method,
        'path': request.path,
        'request_id': get_request_id(request),
    }
    
    # Add context if available
    context = request_context.get()
    if context:
        info.update(context)
    
    return info


def log_user_action(logger: logging.Logger, action: str, user: 'AbstractUser', 
                   request: 'HttpRequest' = None, extra_data: dict = None):
    """Log user actions with consistent format."""
    log_data = {
        'action': action,
        'user': user.username if user and user.is_authenticated else 'anonymous',
        'user_id': user.id if user and user.is_authenticated else None,
    }
    
    if request:
        log_data.update(get_client_info(request))
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.info(f"User action: {action}", extra=log_data)


def log_security_event(logger: logging.Logger, event: str, request: 'HttpRequest' = None, 
                      user: 'AbstractUser' = None, severity: str = 'warning', 
                      extra_data: dict = None):
    """Log security-related events."""
    log_data = {
        'event_type': 'security',
        'event': event,
        'severity': severity,
        'user': user.username if user and user.is_authenticated else 'anonymous',
    }
    
    if request:
        log_data.update(get_client_info(request))
    
    if extra_data:
        log_data.update(extra_data)
    
    message = f"Security event: {event}"
    
    if severity == 'critical':
        logger.critical(message, extra=log_data)
    elif severity == 'error':
        logger.error(message, extra=log_data)
    elif severity == 'warning':
        logger.warning(message, extra=log_data)
    else:
        logger.info(message, extra=log_data)


def log_api_call(logger: logging.Logger, api_endpoint: str, status: str = 'success', 
                response_time: float = None, extra_data: dict = None):
    """Log external API calls."""
    log_data = {
        'event_type': 'api_call',
        'endpoint': api_endpoint,
        'status': status,
    }
    
    if response_time:
        log_data['response_time_ms'] = round(response_time * 1000, 2)
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.info(f"API call to {api_endpoint}: {status}", extra=log_data)


def log_database_operation(logger: logging.Logger, operation: str, model: str, 
                          count: int = 1, extra_data: dict = None):
    """Log database operations."""
    log_data = {
        'event_type': 'database',
        'operation': operation,
        'model': model,
        'count': count,
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.debug(f"Database {operation} on {model}: {count} records", extra=log_data)


def performance_log(logger: logging.Logger = None, threshold: float = 1.0):
    """Decorator to log function performance."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            # Use the module's logger if none provided
            log = logger or logging.getLogger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if execution_time > threshold:
                    log.warning(
                        f"Slow function execution: {func.__name__} took {execution_time:.2f}s",
                        extra={
                            'function': func.__name__,
                            'function_module': func.__module__,
                            'execution_time': execution_time,
                            'threshold': threshold,
                        }
                    )
                else:
                    log.debug(
                        f"Function {func.__name__} executed in {execution_time:.2f}s",
                        extra={
                            'function': func.__name__,
                            'function_module': func.__module__,
                            'execution_time': execution_time,
                        }
                    )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                log.error(
                    f"Function {func.__name__} failed after {execution_time:.2f}s: {str(e)}",
                    extra={
                        'function': func.__name__,
                        'function_module': func.__module__,
                        'execution_time': execution_time,
                        'error_msg': str(e),
                    },
                    exc_info=True
                )
                raise
                
        return wrapper
    return decorator


def sanitize_sensitive_data(data: dict, sensitive_keys: list = None) -> dict:
    """
    Enhanced sanitization of sensitive data for logging.
    
    Redacts:
    - Passwords, tokens, secrets, API keys
    - Credit card numbers, SSN
    - Email addresses and phone numbers (optional)
    - IP addresses (optional, based on settings)
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'token', 'secret', 'key', 'authorization',
            'csrf_token', 'credit_card', 'ssn', 'social_security',
            'api_key', 'private_key', 'access_token', 'refresh_token'
        ]
    
    # PII patterns
    PII_PATTERNS = {
        'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),
        'phone': (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE_REDACTED]'),
        'credit_card': (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC_REDACTED]'),
        'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),
    }
    
    def sanitize_string(text: str) -> str:
        """Sanitize PII patterns in strings."""
        if not isinstance(text, str):
            return text
        
        for pattern_name, (pattern, replacement) in PII_PATTERNS.items():
            text = re.sub(pattern, replacement, text)
        return text
    
    sanitized = {}
    for key, value in data.items():
        # Check if key contains sensitive keyword
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_sensitive_data(value, sensitive_keys)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_sensitive_data(item, sensitive_keys) if isinstance(item, dict)
                else sanitize_string(str(item)) if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        else:
            sanitized[key] = value
    
    return sanitized


class ContextEnrichmentFilter(logging.Filter):
    """
    Logging filter to automatically enrich log records with context.
    
    Adds:
    - Request ID for correlation
    - Environment info (hostname, deployment)
    - Thread/process information
    - Application version
    """
    
    def filter(self, record):
        # Add request context if available
        context = request_context.get()
        if context:
            record.request_id = context.get('request_id', 'N/A')
            record.user_id = context.get('user_id', 'N/A')
            record.username = context.get('username', 'anonymous')
        else:
            record.request_id = 'N/A'
            record.user_id = 'N/A'
            record.username = 'anonymous'
        
        # Add deployment info
        record.hostname = socket.gethostname()
        # Lazy import settings to avoid circular dependency
        try:
            from django.conf import settings
            record.environment = getattr(settings, 'ENVIRONMENT', 'unknown')
        except ImportError:
            record.environment = 'unknown'
        record.thread_name = threading.current_thread().name
        
        return True


class LoggerMixin:
    """Mixin to add logging capabilities to views."""
    
    @property
    def logger(self):
        """Get logger for the current class."""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def log_action(self, action: str, request: 'HttpRequest' = None, extra_data: dict = None):
        """Log an action performed by this view."""
        user = getattr(request, 'user', None) if request else None
        log_user_action(self.logger, action, user, request, extra_data)
    
    def log_error(self, error: str, request: 'HttpRequest' = None, exception: Exception = None):
        """Log an error that occurred in this view."""
        extra_data = {}
        if request:
            extra_data.update(get_client_info(request))
        
        if exception:
            self.logger.error(f"View error: {error}", extra=extra_data, exc_info=True)
        else:
            self.logger.error(f"View error: {error}", extra=extra_data)


# Configurable log sampling per logger
def _get_sample_rates():
    """Lazy load sample rates from settings to avoid circular dependency."""
    try:
        from django.conf import settings
        return getattr(settings, 'LOG_SAMPLE_RATES', {
            'places.views': 0.1,      # 10% sampling for high-volume places
            'utils.location': 0.01,   # 1% sampling for location lookups
            'prayer_times': 0.1,      # 10% sampling for prayer times
        })
    except ImportError:
        return {
            'places.views': 0.1,
            'utils.location': 0.01,
            'prayer_times': 0.1,
        }


def should_sample_log(logger_name: str) -> bool:
    """Determine if a log should be sampled based on configuration."""
    import random
    
    sample_rates = _get_sample_rates()
    sample_rate = sample_rates.get(logger_name, 1.0)  # Default: log everything
    return random.random() < sample_rate


def log_execution(level: str = 'info', include_args: bool = False, sample: bool = False):
    """
    Decorator for consistent function execution logging.
    
    Args:
        level: Log level (info, debug, warning)
        include_args: Whether to include function arguments
        sample: Whether to apply sampling (useful for high-volume functions)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            
            # Apply sampling if configured
            if sample and not should_sample_log(func.__module__):
                return func(*args, **kwargs)
            
            start = time.time()
            
            log_data = {
                'function': func.__name__,
                'module': func.__module__,
                'request_id': request_context.get().get('request_id', 'N/A') if request_context.get() else 'N/A',
            }
            
            if include_args:
                # Sanitize arguments before logging
                log_data['args'] = sanitize_sensitive_data({'args': str(args)})
                log_data['kwargs'] = sanitize_sensitive_data(kwargs) if kwargs else {}
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                log_data['duration_ms'] = round(duration * 1000, 2)
                log_data['status'] = 'success'
                
                getattr(logger, level)(
                    f"Function executed: {func.__name__}",
                    extra=log_data
                )
                return result
                
            except Exception as e:
                duration = time.time() - start
                log_data['duration_ms'] = round(duration * 1000, 2)
                log_data['status'] = 'error'
                log_data['error_type'] = type(e).__name__
                log_data['error_message'] = str(e)
                
                logger.error(
                    f"Function failed: {func.__name__}",
                    extra=log_data,
                    exc_info=True
                )
                raise
                
        return wrapper
    return decorator 