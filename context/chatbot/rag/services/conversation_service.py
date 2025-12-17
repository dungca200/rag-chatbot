import uuid
import logging
from typing import List, Optional, Tuple, Dict
from rag.models import Conversation, ConversationMessage
from psycopg_pool import ConnectionPool

class ConversationService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def create_conversation(company_id: int) -> Tuple[Conversation, str]:
        """Create a new conversation and return it with the generated session_id."""
        session_id = str(uuid.uuid4())
        conversation = Conversation.objects.create(
            session_id=session_id,
            company_id=company_id
        )
        return conversation, session_id

    @staticmethod
    def get_or_create_conversation(company_id: int, session_id: Optional[str] = None) -> Tuple[Conversation, str, bool]:
        """Get existing conversation or create new one if session_id is not provided or invalid."""
        created = False
        if session_id:
            try:
                conversation = Conversation.objects.get(session_id=session_id, company_id=company_id)
                return conversation, session_id, created
            except Conversation.DoesNotExist:
                pass
        
        conversation, session_id = ConversationService.create_conversation(company_id)
        created = True
        return conversation, session_id, created

    @staticmethod
    def add_message(conversation: Conversation, role: str, content: str, document_key: Optional[str] = None) -> ConversationMessage:
        """Add a new message to the conversation."""
        return ConversationMessage.objects.create(
            conversation=conversation,
            role=role,
            content=content,
            document_key=document_key
        )

    @staticmethod
    def get_conversation_context(conversation: Conversation, limit: int = 5) -> List[dict]:
        """Get the last N messages from the conversation in chronological order."""
        # Order by timestamp (oldest first) to maintain conversation flow
        messages = conversation.messages.all().order_by('timestamp')
        
        # If limit is provided, take only the last 'limit' messages
        if limit > 0 and messages.count() > limit:
            # Get the last 'limit' messages while preserving chronological order
            messages = messages[messages.count() - limit:]
            
        context = []
        for message in messages:
            context.append({
                'role': message.role,
                'content': message.content,
                'document_key': message.document_key
            })
        return context

    @staticmethod
    def format_context_for_rag(context: List[dict]) -> str:
        """Format conversation context for RAG processing."""
        formatted_context = []
        
        # Remove duplicates by tracking seen message content
        seen_messages = set()
        
        for msg in context:
            # Create a unique key for this message
            message_key = f"{msg['role']}:{msg['content']}"
            
            # Skip if we've already seen this message
            if message_key in seen_messages:
                continue
                
            seen_messages.add(message_key)
            
            # Format the message with document key if present
            doc_info = f" (document: {msg['document_key']})" if msg['document_key'] else ""
            formatted_context.append(f"{msg['role'].capitalize()}{doc_info}: {msg['content']}")
        
        return "\n".join(formatted_context)

    def get_agent_conversation_context(self, session_id: str, company_id: int, limit: int = 5) -> str:
        """Get formatted conversation context for agents to use."""
        try:
            if not session_id or not company_id:
                return ""
                
            conversation, _, _ = self.get_or_create_conversation(
                company_id=int(company_id), 
                session_id=session_id
            )
            
            context_messages = self.get_conversation_context(conversation, limit=limit)
            formatted_context = self.format_context_for_rag(context_messages)
            
            return formatted_context
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {str(e)}")
            return ""

    def save_agent_message(self, session_id: str, company_id: int, content: str, role: str, document_key: Optional[str] = None) -> None:
        """Save an agent or user message to the conversation history."""
        try:
            if not session_id or not company_id:
                return
                
            conversation, _, _ = self.get_or_create_conversation(
                company_id=int(company_id), 
                session_id=session_id
            )
            
            # Check if this exact message already exists to prevent duplicates
            existing_messages = ConversationMessage.objects.filter(
                conversation=conversation,
                role=role,
                content=content
            )
            
            if existing_messages.exists():
                return
                
            self.add_message(
                conversation=conversation,
                role=role,
                content=content,
                document_key=document_key
            )
        except Exception as e:
            self.logger.error(f"Error saving conversation message: {str(e)}")