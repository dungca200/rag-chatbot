import json
import logging

from django.http import StreamingHttpResponse
from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import Conversation, Message
from .serializers import (
    ChatRequestSerializer,
    ConversationSerializer,
    ConversationDetailSerializer,
    MessageSerializer
)
from .graph.workflow import process_user_query

User = get_user_model()

logger = logging.getLogger(__name__)


def sse_message(event: str, data: dict) -> str:
    """Format a Server-Sent Events message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def stream_chat_response(user, message, conversation_id=None, document_key=None, persist_embeddings=False):
    """Generator that streams chat response via SSE."""

    # Get or create conversation
    if conversation_id:
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=user)
        except Conversation.DoesNotExist:
            yield sse_message("error", {"message": "Conversation not found"})
            return
    else:
        conversation = Conversation.objects.create(user=user)
        yield sse_message("conversation", {"id": str(conversation.id)})

    # Fetch previous messages for context (last 10)
    previous_messages = Message.objects.filter(
        conversation=conversation
    ).order_by('created_at')[:10]

    chat_history = [
        {"role": msg.role, "content": msg.content}
        for msg in previous_messages
    ]

    # Save user message
    user_message = Message.objects.create(
        conversation=conversation,
        role='user',
        content=message
    )

    yield sse_message("message", {
        "id": str(user_message.id),
        "role": "user",
        "content": message
    })

    # Process through workflow
    try:
        yield sse_message("status", {"message": "Processing..."})

        result = process_user_query(
            query=message,
            user_id=str(user.id),
            thread_id=str(conversation.id),
            document_key=document_key,
            persist_embeddings=persist_embeddings,
            chat_history=chat_history
        )

        response_content = result.get("response", "")
        sources = result.get("sources", [])
        agent = result.get("agent", "unknown")

        # Stream the response (in production, this would be token-by-token)
        # For now, stream in chunks to demonstrate SSE
        chunk_size = 50
        for i in range(0, len(response_content), chunk_size):
            chunk = response_content[i:i + chunk_size]
            yield sse_message("token", {"content": chunk})

        # Save assistant message
        assistant_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=response_content,
            sources=sources,
            metadata={"agent": agent}
        )

        yield sse_message("message", {
            "id": str(assistant_message.id),
            "role": "assistant",
            "content": response_content,
            "sources": sources,
            "agent": agent
        })

        # Generate title if needed
        conversation.generate_title()

        yield sse_message("done", {
            "conversation_id": str(conversation.id),
            "title": conversation.title
        })

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        yield sse_message("error", {"message": str(e)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_stream(request):
    """
    SSE streaming chat endpoint.

    POST /api/chat/
    {
        "message": "Hello",
        "conversation_id": "uuid" (optional),
        "document_key": "key" (optional),
        "persist_embeddings": false
    }
    """
    serializer = ChatRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    response = StreamingHttpResponse(
        stream_chat_response(
            user=request.user,
            message=data['message'],
            conversation_id=data.get('conversation_id'),
            document_key=data.get('document_key'),
            persist_embeddings=data.get('persist_embeddings', False)
        ),
        content_type='text/event-stream'
    )

    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'

    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_sync(request):
    """
    Synchronous chat endpoint (non-streaming).

    POST /api/chat/sync/
    """
    serializer = ChatRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user = request.user

    # Get or create conversation
    conversation_id = data.get('conversation_id')
    if conversation_id:
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=user)
        except Conversation.DoesNotExist:
            return Response({
                "success": False,
                "message": "Conversation not found"
            }, status=status.HTTP_404_NOT_FOUND)
    else:
        conversation = Conversation.objects.create(user=user)

    # Save user message
    Message.objects.create(
        conversation=conversation,
        role='user',
        content=data['message']
    )

    # Process through workflow
    result = process_user_query(
        query=data['message'],
        user_id=str(user.id),
        thread_id=str(conversation.id),
        document_key=data.get('document_key'),
        persist_embeddings=data.get('persist_embeddings', False)
    )

    response_content = result.get("response", "")
    sources = result.get("sources", [])

    # Save assistant message
    Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=response_content,
        sources=sources,
        metadata={"agent": result.get("agent", "unknown")}
    )

    # Generate title if needed
    conversation.generate_title()

    return Response({
        "success": True,
        "conversation_id": str(conversation.id),
        "response": response_content,
        "sources": sources,
        "agent": result.get("agent")
    })


# BE-032: Conversation History APIs

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_conversations(request):
    """
    List user's conversations.

    GET /api/chat/conversations/
    """
    conversations = Conversation.objects.filter(user=request.user)
    serializer = ConversationSerializer(conversations, many=True)

    return Response({
        "success": True,
        "conversations": serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation(request, conversation_id):
    """
    Get a conversation with messages.

    GET /api/chat/conversations/{id}/
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response({
            "success": False,
            "message": "Conversation not found"
        }, status=status.HTTP_404_NOT_FOUND)

    serializer = ConversationDetailSerializer(conversation)
    return Response({
        "success": True,
        "conversation": serializer.data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_conversation(request, conversation_id):
    """
    Delete a conversation.

    DELETE /api/chat/conversations/{id}/
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response({
            "success": False,
            "message": "Conversation not found"
        }, status=status.HTTP_404_NOT_FOUND)

    conversation.delete()
    return Response({
        "success": True,
        "message": "Conversation deleted"
    })


# BE-034: Admin APIs

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_stats(request):
    """
    Get admin dashboard stats.

    GET /api/admin/stats/
    """
    from apps.documents.models import Document

    total_users = User.objects.count()
    total_conversations = Conversation.objects.count()
    total_messages = Message.objects.count()
    total_documents = Document.objects.count()

    # Recent activity
    recent_users = User.objects.order_by('-date_joined')[:5].values('id', 'username', 'email', 'date_joined')
    recent_conversations = Conversation.objects.order_by('-created_at')[:5].values('id', 'title', 'created_at')

    return Response({
        "success": True,
        "stats": {
            "total_users": total_users,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_documents": total_documents
        },
        "recent_users": list(recent_users),
        "recent_conversations": list(recent_conversations)
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_users(request):
    """
    List all users (admin only).

    GET /api/admin/users/
    """
    users = User.objects.annotate(
        conversation_count=Count('conversations'),
        document_count=Count('documents')
    ).values(
        'id', 'username', 'email', 'is_staff', 'is_active',
        'date_joined', 'conversation_count', 'document_count'
    )

    return Response({
        "success": True,
        "users": list(users)
    })
