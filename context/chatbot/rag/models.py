from django.db import models


class Conversation(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    company_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['company_id']),
        ]


class ConversationMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)  # 'user' or 'assistant'
    content = models.TextField()
    document_key = models.CharField(max_length=500, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['document_key']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
