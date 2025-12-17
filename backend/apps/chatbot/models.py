import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """Stores chat conversation metadata."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chatbot_conversation'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title or 'Untitled'} - {self.user.username}"

    def generate_title(self):
        """Generate title from first message if not set."""
        if not self.title:
            first_message = self.messages.filter(role='user').first()
            if first_message:
                self.title = first_message.content[:50]
                if len(first_message.content) > 50:
                    self.title += '...'
                self.save(update_fields=['title'])


class Message(models.Model):
    """Stores individual chat messages."""

    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chatbot_message'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
