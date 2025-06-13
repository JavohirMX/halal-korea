# Logging System Documentation

## Overview

This project implements a comprehensive logging system for the Halal Korea Django application. The logging system is designed to provide detailed insights into application behavior, security events, performance metrics, and debugging information.

## Logging Configuration

The logging system is configured in `config/settings.py` with the following features:

### Log Levels

- **DEBUG**: Detailed information for debugging (only in development)
- **INFO**: General information about application flow
- **WARNING**: Potential issues that don't stop execution
- **ERROR**: Error conditions that affect functionality
- **CRITICAL**: Serious errors that may cause application failure

### Log Files

All log files are stored in the `logs/` directory (created automatically):

1. **`django.log`** - General application logs (10MB, 5 backups)
2. **`django_errors.log`** - Error-level logs only (10MB, 5 backups)
3. **`security.log`** - Security-related events in JSON format (5MB, 3 backups)
4. **`api.log`** - External API calls and responses (5MB, 3 backups)
5. **`database.log`** - Database warnings and errors (5MB, 3 backups)

### Log Handlers

- **Console Handler**: Outputs to console during development
- **File Handlers**: Rotating file handlers for persistent logging
- **Email Handler**: Sends critical errors to admins in production
- **Security Handler**: Special handler for security events

### Loggers by App

Each Django app has its own logger with appropriate handlers:

- **places**: Application logs, error logs
- **users**: Application logs, error logs, security logs
- **reviews**: Application logs, error logs
- **prayer_times**: Application logs, API logs, error logs
- **utils**: Application logs, error logs

## Using the Logging System

### Basic Logging

```python
import logging

logger = logging.getLogger(__name__)

# Different log levels
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical system error")
```

### Using Logging Utilities

The `utils/logging_utils.py` module provides helper functions for common logging patterns:

```python
from utils.logging_utils import (
    log_user_action, log_security_event, log_api_call,
    log_database_operation, performance_log
)

# Log user actions
log_user_action(logger, "user_login", user, request)

# Log security events
log_security_event(logger, "failed_login_attempt", request, user, "warning")

# Log API calls
log_api_call(logger, "https://api.example.com", "success", 0.5)

# Log database operations
log_database_operation(logger, "SELECT", "HalalPlace", 25)
```

### Performance Logging

Use the `@performance_log` decorator to monitor function execution time:

```python
from utils.logging_utils import performance_log

@performance_log(threshold=1.0)  # Log if takes longer than 1 second
def slow_database_query():
    # Your code here
    pass
```

### Security Logging

The system automatically logs security-related events:

- Failed login attempts
- User registration
- Authentication events
- Suspicious activities

### Data Sanitization

Sensitive data is automatically sanitized before logging:

```python
from utils.logging_utils import sanitize_sensitive_data

data = {
    'username': 'user',
    'password': 'secret',  # Will be redacted
    'email': 'user@example.com'
}

sanitized = sanitize_sensitive_data(data)
logger.info("User data", extra={'data': sanitized})
```

## LoggerMixin for Views

Use the `LoggerMixin` class for consistent logging in class-based views:

```python
from utils.logging_utils import LoggerMixin

class MyView(LoggerMixin, View):
    def get(self, request):
        self.log_action("page_viewed", request)
        # Your view logic
```

## Testing the Logging System

Test the logging system using the management command:

```bash
# Test all logging features
python manage.py test_logging

# Test specific log levels
python manage.py test_logging --level info
python manage.py test_logging --level error
python manage.py test_logging --level security
```

## Production Considerations

### Environment Variables

Ensure proper configuration for production:

- `DJANGO_DEBUG=False` - Disables debug logging in production
- Email settings for admin notifications
- Proper log file permissions

### Log Rotation

Log files automatically rotate when they reach size limits:
- Main logs: 10MB with 5 backups
- Specialized logs: 5MB with 3 backups

### Monitoring

Consider setting up log monitoring tools to:
- Alert on critical errors
- Monitor log file sizes
- Analyze security events
- Track performance trends

### Security

- Log files contain sensitive information - secure appropriately
- Sensitive data is automatically sanitized
- Security events are logged in JSON format for easy parsing

## Log Format Examples

### Standard Log Entry
```
INFO 2024-01-15 10:30:45 places.views 12345 67890 Home page accessed by user: john_doe
```

### Error Log Entry
```
ERROR 2024-01-15 10:30:45 users.views 12345 67890 Failed login attempt for username: admin from IP: 192.168.1.100
```

### Security Log Entry (JSON)
```json
{
  "level": "WARNING",
  "time": "2024-01-15 10:30:45",
  "module": "users.views",
  "message": "Security event: Multiple failed login attempts",
  "event_type": "security",
  "user": "anonymous",
  "ip": "192.168.1.100"
}
```

## Best Practices

1. **Use appropriate log levels** - Don't use ERROR for warnings
2. **Include context** - Add relevant data using the `extra` parameter
3. **Sanitize sensitive data** - Use the sanitization utilities
4. **Log user actions** - Track important user activities
5. **Monitor performance** - Use performance logging for slow operations
6. **Security logging** - Log all authentication and authorization events

## Troubleshooting

### Common Issues

1. **Log files not created**: Check write permissions on the `logs/` directory
2. **No console output**: Ensure `DEBUG=True` in development
3. **Missing logs**: Check logger configuration and log levels
4. **Large log files**: Verify rotation settings are working

### Debugging Logging

Enable Django's internal logging debugging:

```python
# In settings.py for troubleshooting
LOGGING['loggers']['django']['level'] = 'DEBUG'
```

## Integration Examples

### View Logging
```python
def submit_place(request):
    logger.info(f"Place submission by {request.user.username}")
    try:
        # Process form
        logger.info(f"Place '{place.name}' submitted successfully")
    except Exception as e:
        logger.error(f"Place submission failed: {str(e)}", exc_info=True)
```

### API Logging
```python
def fetch_prayer_times(city):
    start_time = time.time()
    try:
        response = requests.get(api_url)
        response_time = time.time() - start_time
        log_api_call(logger, api_url, 'success', response_time)
        return response.json()
    except Exception as e:
        log_api_call(logger, api_url, 'error', extra_data={'error': str(e)})
        raise
```

This logging system provides comprehensive monitoring and debugging capabilities for the Halal Korea application while maintaining security and performance. 