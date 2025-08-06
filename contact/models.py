from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ContactMessage(models.Model):
    """Model to store contact form submissions"""
    
    # User info (for both authenticated and anonymous users)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    
    # Message content
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    
    # Metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
    
    def __str__(self):
        return f"{self.name} - {self.subject or 'No Subject'} ({self.created_at.strftime('%Y-%m-%d')})"
    
    def mark_as_read(self):
        """Mark the message as read"""
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    def mark_as_responded(self):
        """Mark the message as responded"""
        self.responded_at = timezone.now()
        self.save(update_fields=['responded_at'])
