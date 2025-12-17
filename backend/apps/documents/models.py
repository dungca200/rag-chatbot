import uuid

from django.conf import settings
from django.db import models


class Document(models.Model):
    """Stores uploaded document metadata."""

    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('xlsx', 'Excel Spreadsheet'),
        ('image', 'Image'),
        ('txt', 'Text File'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, choices=FILE_TYPE_CHOICES)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    storage_path = models.CharField(max_length=500, blank=True)
    file_url = models.URLField(max_length=1000, blank=True)
    document_key = models.CharField(max_length=100, unique=True, db_index=True)
    is_vectorized = models.BooleanField(default=False)
    is_persistent = models.BooleanField(default=True)
    chunk_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents_document'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_filename} ({self.user.username})"

    @property
    def file_size_display(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
