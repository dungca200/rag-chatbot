from rest_framework import serializers

class ChatbotRequestSerializer(serializers.Serializer):
    """Serializer for validating incoming chatbot request data."""
    company_id = serializers.IntegerField(required=False, allow_null=True)
    query = serializers.CharField(required=True)
    document_key = serializers.CharField(required=False, allow_null=True)
    session_id = serializers.CharField(required=False, allow_null=True)
    thread_id = serializers.CharField(required=False, allow_null=True)

    def validate_query(self, value):
        """Ensure the query is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Query cannot be empty.")
        return value
    
    def validate(self, data):
        """
        Handle backward compatibility between session_id and thread_id.
        If both are provided, thread_id takes precedence.
        """
        session_id = data.get('session_id')
        thread_id = data.get('thread_id')
        
        if thread_id:
            # If thread_id is provided, use it
            data['session_id'] = thread_id
        elif session_id:
            # If only session_id is provided, use it as thread_id too
            data['thread_id'] = session_id
            
        return data

class LogEntrySerializer(serializers.Serializer):
    """Serializer for log entries in multi-part query responses."""
    arrangement = serializers.IntegerField()
    query = serializers.CharField()
    company_id = serializers.CharField(allow_null=True)

class ChatbotResponseSerializer(serializers.Serializer):
    """Serializer for the chatbot response data."""
    response = serializers.CharField()
    company_id = serializers.CharField(allow_null=True)
    rag_resources = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True
    )
    document_table_resources = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True
    )
    invoice_details_resources = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True
    )
    web_search_resources = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True
    )
    session_id = serializers.CharField(allow_null=True)
    thread_id = serializers.CharField(allow_null=True)
    summary = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True
    )
    logs = serializers.ListField(
        child=LogEntrySerializer(),
        allow_empty=True,
        required=False
    )

class MetadataSerializer(serializers.Serializer):
    """Serializer for document metadata."""
    class Meta:
        additional_properties = True

class ClassificationResultSerializer(serializers.Serializer):
    """Serializer for document classification results."""
    document_type = serializers.CharField(default="Unknown")
    metadata = MetadataSerializer(required=False)
    summary = serializers.CharField(required=False)

class DocumentClassifierResponseSerializer(serializers.Serializer):
    """Serializer for the document classifier response data."""
    response = serializers.CharField()
    company_id = serializers.CharField(allow_null=True)
    resources = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True
    )
    session_id = serializers.CharField(allow_null=True)
    thread_id = serializers.CharField(allow_null=True)
    classification_result = ClassificationResultSerializer(required=False)
    summary = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False
    )

class SuccessResponseSerializer(serializers.Serializer):
    """Serializer for the full successful response."""
    message = serializers.CharField()
    data = serializers.JSONField()

class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""
    message = serializers.CharField()
    errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False
    )