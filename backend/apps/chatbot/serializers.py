from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""
    file = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'sources', 'file', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_file(self, obj):
        """Extract file info from metadata."""
        return obj.metadata.get('file') if obj.metadata else None


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model."""
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'document_key', 'message_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for Conversation with messages."""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'document_key', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class FileInfoSerializer(serializers.Serializer):
    """Serializer for file attachment info."""
    name = serializers.CharField()
    size = serializers.IntegerField()
    type = serializers.CharField()
    url = serializers.URLField(required=False, allow_blank=True)


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat request."""
    message = serializers.CharField(max_length=10000)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    document_key = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    persist_embeddings = serializers.BooleanField(default=False)
    file_info = FileInfoSerializer(required=False, allow_null=True)
