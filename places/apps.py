from django.apps import AppConfig


class PlacesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'places'
    
    def ready(self):
        # Import signals to register them
        import places.signals  # noqa: F401
