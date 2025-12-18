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
from core.clients.supabase_client import delete_documents_by_key, upload_file_to_storage, delete_file_from_storage

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

        # Upload to Supabase Storage for later viewing
        content_type_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xlsm': 'application/vnd.ms-excel.sheet.macroEnabled.12',
            '.txt': 'text/plain',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')

        # Try to upload to storage (optional - continues even if fails)
        file_url = ''
        storage_path = ''
        try:
            storage_result = upload_file_to_storage(
                file_path=tmp_path,
                file_name=uploaded_file.name,
                user_id=str(request.user.id),
                content_type=content_type
            )
            logger.info(f"Storage upload result: {storage_result}")
            if storage_result:
                file_url = storage_result.get('file_url', '')
                storage_path = storage_result.get('storage_path', '')
                logger.info(f"Got file_url: {file_url}")
        except Exception as storage_error:
            logger.warning(f"Storage upload failed (continuing without): {storage_error}")

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
            storage_path=storage_path,
            file_url=file_url,
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
            "file_url": document.file_url,
            "file_type": document.file_type,
            "file_size": document.file_size,
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
    List user's persistent documents (excludes session-only uploads).

    GET /api/documents/
    """
    # Only show persistent documents (is_persistent=True)
    documents = Document.objects.filter(user=request.user, is_persistent=True)
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
    Delete a document and its vectors from Supabase.

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
    user_id = str(request.user.id)
    storage_path = document.storage_path

    # Delete vectors from Supabase
    vector_result = delete_documents_by_key(document_key, user_id)
    if not vector_result.get("success"):
        logger.warning(f"Failed to delete vectors for {document_key}: {vector_result.get('error')}")

    # Delete file from storage (if exists)
    if storage_path:
        try:
            delete_file_from_storage(storage_path)
        except Exception as e:
            logger.warning(f"Failed to delete file from storage: {e}")

    # Delete Django record
    document.delete()

    return Response({
        "success": True,
        "message": f"Document {document_key} deleted",
        "vectors_deleted": vector_result.get("deleted_count", 0)
    })
