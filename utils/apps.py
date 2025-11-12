from django.apps import AppConfig


class UtilsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'utils'
    verbose_name = 'Utilities'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        try:
            import utils.monitoring_signals  # noqa
        except ImportError:
            pass 