from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model."""
    file_size_display = serializers.ReadOnlyField()

    class Meta:
        model = Document
        fields = [
            'id', 'filename', 'original_filename', 'file_type',
            'file_size', 'file_size_display', 'document_key',
            'is_vectorized', 'is_persistent', 'chunk_count',
            'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload."""
    file = serializers.FileField()
    persist_embeddings = serializers.BooleanField(default=True)
