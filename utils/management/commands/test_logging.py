"""
Management command to test the logging system.
"""

import logging
import time
from django.core.management.base import BaseCommand
from utils.logging_utils import (
    log_api_call, log_database_operation, performance_log, 
    sanitize_sensitive_data
)


class Command(BaseCommand):
    help = 'Test the logging system and demonstrate its features'

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            '--level',
            type=str,
            default='all',
            help='Log level to test (debug, info, warning, error, critical, all)',
        )

    def handle(self, *args, **options):
        level = options['level'].lower()
        
        self.stdout.write(
            self.style.SUCCESS('Starting logging system test...')
        )

        if level in ['debug', 'all']:
            self.test_debug_logging()

        if level in ['info', 'all']:
            self.test_info_logging()

        if level in ['warning', 'all']:
            self.test_warning_logging()

        if level in ['error', 'all']:
            self.test_error_logging()

        if level in ['critical', 'all']:
            self.test_critical_logging()

        if level in ['api', 'all']:
            self.test_api_logging()

        if level in ['database', 'all']:
            self.test_database_logging()

        if level in ['performance', 'all']:
            self.test_performance_logging()

        if level in ['security', 'all']:
            self.test_security_logging()

        self.stdout.write(
            self.style.SUCCESS('Logging system test completed!')
        )

    def test_debug_logging(self):
        """Test debug level logging."""
        self.logger.debug("This is a debug message - testing detailed application flow")
        self.logger.debug("Debug: User session data processed", extra={
            'session_id': 'test_session_123',
            'processing_time': 0.05
        })

    def test_info_logging(self):
        """Test info level logging."""
        self.logger.info("This is an info message - testing general information")
        self.logger.info("Application startup completed", extra={
            'startup_time': 2.3,
            'modules_loaded': 12
        })

    def test_warning_logging(self):
        """Test warning level logging."""
        self.logger.warning("This is a warning message - testing potential issues")
        self.logger.warning("Slow database query detected", extra={
            'query_time': 1.5,
            'query': 'SELECT * FROM places_halalplace WHERE status=approved'
        })

    def test_error_logging(self):
        """Test error level logging."""
        self.logger.error("This is an error message - testing error conditions")
        try:
            # Simulate an error
            raise ValueError("Test error for logging demonstration")
        except ValueError as e:
            self.logger.error(f"Simulated error caught: {str(e)}", exc_info=True)

    def test_critical_logging(self):
        """Test critical level logging."""
        self.logger.critical("This is a critical message - testing system failures")
        self.logger.critical("Database connection lost", extra={
            'database': 'main',
            'retry_attempts': 3,
            'last_error': 'Connection timeout'
        })

    def test_api_logging(self):
        """Test API call logging."""
        start_time = time.time()
        time.sleep(0.1)  # Simulate API call
        response_time = time.time() - start_time
        
        log_api_call(
            self.logger,
            'http://api.aladhan.com/v1/timings',
            'success',
            response_time,
            {'city': 'Seoul', 'country': 'South Korea'}
        )

        log_api_call(
            self.logger,
            'https://api.example.com/data',
            'error',
            extra_data={'error_code': 500, 'error_message': 'Internal Server Error'}
        )

    def test_database_logging(self):
        """Test database operation logging."""
        log_database_operation(
            self.logger,
            'SELECT',
            'HalalPlace',
            25,
            {'filters': 'status=approved', 'location': 'Seoul'}
        )

        log_database_operation(
            self.logger,
            'INSERT',
            'Review',
            1,
            {'place_id': 123, 'user_id': 456}
        )

    @performance_log(threshold=0.05)
    def slow_function(self):
        """Simulate a slow function."""
        time.sleep(0.1)
        return "completed"

    @performance_log(threshold=2.0)
    def fast_function(self):
        """Simulate a fast function."""
        time.sleep(0.01)
        return "completed"

    def test_performance_logging(self):
        """Test performance logging decorator."""
        self.slow_function()
        self.fast_function()

    def test_security_logging(self):
        """Test security-related logging and data sanitization."""
        # Test data sanitization
        sensitive_data = {
            'username': 'testuser',
            'password': 'secret123',
            'email': 'test@example.com',
            'csrf_token': 'abc123xyz',
            'api_key': 'super_secret_key',
            'user_preferences': {
                'theme': 'dark',
                'password_hint': 'my_secret_hint'
            }
        }

        sanitized = sanitize_sensitive_data(sensitive_data)
        self.logger.info("User data processed", extra={
            'original_keys': list(sensitive_data.keys()),
            'sanitized_data': sanitized
        })

        # Test security event logging
        from utils.logging_utils import log_security_event
        
        security_logger = logging.getLogger('security')
        
        log_security_event(
            security_logger,
            'Multiple failed login attempts',
            severity='warning',
            extra_data={
                'username': 'admin',
                'ip': '192.168.1.100',
                'attempts': 5
            }
        )

        log_security_event(
            security_logger,
            'Suspicious file upload attempt',
            severity='error',
            extra_data={
                'uploaded_filename': 'malicious.php',
                'file_size': 1024,
                'blocked': True
            }
        ) 