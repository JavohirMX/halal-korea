from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'
    verbose_name = 'Blog Management'
    
    def ready(self):
        """Initialize blog app"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Blog app initialized successfully")
