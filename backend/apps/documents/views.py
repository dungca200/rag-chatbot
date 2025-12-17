import logging
import os
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Document
from .serializers import DocumentSerializer, FileUploadSerializer
from apps.chatbot.tools import process_and_vectorize_file

logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.xlsm', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def get_file_type(filename: str) -> str:
    """Get file type from extension."""
    ext = Path(filename).suffix.lower()
    type_map = {
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.xlsx': 'xlsx',
        '.xlsm': 'xlsx',
        '.txt': 'txt',
    }
    if ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
        return 'image'
    return type_map.get(ext, 'other')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_document(request):
    """
    Upload and process a document.

    POST /api/documents/upload/
    Form data:
        - file: The file to upload
        - persist_embeddings: bool (default: true)
    """
    serializer = FileUploadSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = serializer.validated_data['file']
    persist = serializer.validated_data.get('persist_embeddings', True)

    # Validate file extension
    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return Response({
            "success": False,
            "message": f"File type not allowed: {ext}"
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate file size
    if uploaded_file.size > MAX_FILE_SIZE:
        return Response({
            "success": False,
            "message": f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # Process and vectorize
        result = process_and_vectorize_file(
            file_path=tmp_path,
            user_id=str(request.user.id),
            persist_embeddings=persist
        )

        # Clean up temp file
        os.unlink(tmp_path)

        if not result.get('success'):
            return Response({
                "success": False,
                "message": result.get('error', 'Processing failed')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create Document record
        document = Document.objects.create(
            user=request.user,
            filename=f"{result['document_key']}{ext}",
            original_filename=uploaded_file.name,
            file_type=get_file_type(uploaded_file.name),
            file_size=uploaded_file.size,
            document_key=result['document_key'],
            is_vectorized=result.get('vectorized', False),
            is_persistent=persist,
            chunk_count=result.get('chunk_count', 0),
            metadata=result.get('metadata', {})
        )

        return Response({
            "success": True,
            "document_id": str(document.id),
            "document_key": document.document_key,
            "filename": document.original_filename,
            "chunk_count": document.chunk_count,
            "vectorized": document.is_vectorized
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return Response({
            "success": False,
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_documents(request):
    """
    List user's documents.

    GET /api/documents/
    """
    documents = Document.objects.filter(user=request.user)
    serializer = DocumentSerializer(documents, many=True)

    return Response({
        "success": True,
        "documents": serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_document(request, document_id):
    """
    Get a specific document.

    GET /api/documents/{id}/
    """
    try:
        document = Document.objects.get(id=document_id, user=request.user)
    except Document.DoesNotExist:
        return Response({
            "success": False,
            "message": "Document not found"
        }, status=status.HTTP_404_NOT_FOUND)

    serializer = DocumentSerializer(document)
    return Response({
        "success": True,
        "document": serializer.data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_document(request, document_id):
    """
    Delete a document.

    DELETE /api/documents/{id}/
    """
    try:
        document = Document.objects.get(id=document_id, user=request.user)
    except Document.DoesNotExist:
        return Response({
            "success": False,
            "message": "Document not found"
        }, status=status.HTTP_404_NOT_FOUND)

    document_key = document.document_key
    document.delete()

    # TODO: Also delete vectors from Supabase using document_key

    return Response({
        "success": True,
        "message": f"Document {document_key} deleted"
    })
