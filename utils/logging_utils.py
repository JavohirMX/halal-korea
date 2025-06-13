"""
Logging utilities for the Halal Korea application.

This module provides common logging patterns and utilities for consistent
logging across the application.
"""

import logging
import functools
import time
from typing import Any, Callable
from django.http import HttpRequest
from django.contrib.auth.models import AbstractUser


def get_client_info(request: HttpRequest) -> dict:
    """Extract client information from request for logging."""
    return {
        'ip': request.META.get('REMOTE_ADDR', 'unknown'),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
        'referer': request.META.get('HTTP_REFERER', 'unknown'),
        'method': request.method,
        'path': request.path,
    }


def log_user_action(logger: logging.Logger, action: str, user: AbstractUser, 
                   request: HttpRequest = None, extra_data: dict = None):
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


def log_security_event(logger: logging.Logger, event: str, request: HttpRequest = None, 
                      user: AbstractUser = None, severity: str = 'warning', 
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
    """Sanitize sensitive data for logging."""
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'token', 'secret', 'key', 'authorization',
            'csrf_token', 'credit_card', 'ssn', 'social_security'
        ]
    
    sanitized = {}
    for key, value in data.items():
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_sensitive_data(value, sensitive_keys)
        else:
            sanitized[key] = value
    
    return sanitized


class LoggerMixin:
    """Mixin to add logging capabilities to views."""
    
    @property
    def logger(self):
        """Get logger for the current class."""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def log_action(self, action: str, request: HttpRequest = None, extra_data: dict = None):
        """Log an action performed by this view."""
        user = getattr(request, 'user', None) if request else None
        log_user_action(self.logger, action, user, request, extra_data)
    
    def log_error(self, error: str, request: HttpRequest = None, exception: Exception = None):
        """Log an error that occurred in this view."""
        extra_data = {}
        if request:
            extra_data.update(get_client_info(request))
        
        if exception:
            self.logger.error(f"View error: {error}", extra=extra_data, exc_info=True)
        else:
            self.logger.error(f"View error: {error}", extra=extra_data) 