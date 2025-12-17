import logging
from typing import Dict, Optional, Literal

from pydantic import BaseModel, Field

from core.clients.gemini_client import get_chat_model

logger = logging.getLogger(__name__)


# Agent types for routing
AgentType = Literal["rag", "conversation", "document", "web_search"]


class IntentClassification(BaseModel):
    """Schema for intent classification output."""
    agent: AgentType = Field(
        description="The agent to handle this query"
    )
    rationale: str = Field(
        description="Brief explanation of why this agent was selected"
    )


CLASSIFICATION_PROMPT = """You are an intent classifier for a RAG chatbot. Analyze the user query and determine which agent should handle it.

Available agents:
- rag: For questions about user's documents OR follow-up questions that refer to previously discussed document content
- web_search: For general knowledge questions, facts, current events, definitions, explanations that are NOT about user's documents
- conversation: For greetings, smalltalk, personal chat, help requests, questions about the bot itself
- document: For file upload/processing requests

{history_context}

IMPORTANT ROUTING RULES:
1. If the conversation history shows a document was recently analyzed, follow-up questions about that content should go to "rag"
2. Use "rag" when user asks about specific data, numbers, or content that would come from their documents
3. Use "web_search" ONLY for general knowledge NOT related to user's documents
4. Default to "conversation" for greetings and ambiguous social queries

User Query: {query}

Classify the intent and select the appropriate agent."""


class IntentClassifier:
    """Classifies user intent and routes to appropriate agent."""

    def __init__(self):
        self.llm = get_chat_model(temperature=0.0)
        self.structured_llm = self.llm.with_structured_output(IntentClassification)

    def _format_history_context(self, chat_history: list) -> str:
        """Format chat history to provide context for classification."""
        if not chat_history:
            return "Conversation History: This is the start of the conversation."

        # Check if any previous message involved document analysis
        has_document_context = False
        recent_messages = []

        for msg in chat_history[-4:]:  # Last 4 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")[:150]
            recent_messages.append(f"- {role}: {content}")

            # Check for document-related keywords in assistant responses
            if role == "assistant":
                doc_keywords = ["document", "file", "uploaded", "pdf", "page", "section", "chapter", "table", "figure"]
                if any(kw in content.lower() for kw in doc_keywords):
                    has_document_context = True

        history_text = "\n".join(recent_messages)
        context = f"Conversation History:\n{history_text}"

        if has_document_context:
            context += "\n\nNOTE: The conversation shows previous document analysis. Follow-up questions likely relate to that document."

        return context

    def classify(
        self,
        query: str,
        document_key: Optional[str] = None,
        chat_history: Optional[list] = None
    ) -> Dict:
        """
        Classify the intent of a user query.

        Args:
            query: The user's query
            document_key: If provided, overrides to rag agent
            chat_history: Previous messages for context

        Returns:
            Dict with 'agent' and 'rationale' keys
        """
        # Handle extremely short/empty queries
        if not query or len(query.strip()) <= 2:
            return {
                "agent": "conversation",
                "rationale": "Query too short, routing to conversation for clarification"
            }

        # Override to rag when document_key is provided
        if document_key:
            return {
                "agent": "rag",
                "rationale": f"Document key provided ({document_key}), routing to RAG agent"
            }

        try:
            history_context = self._format_history_context(chat_history or [])
            prompt = CLASSIFICATION_PROMPT.format(query=query, history_context=history_context)
            result = self.structured_llm.invoke(prompt)

            return {
                "agent": result.agent,
                "rationale": result.rationale
            }

        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            # Default to conversation on error
            return {
                "agent": "conversation",
                "rationale": f"Classification error, defaulting to conversation: {str(e)}"
            }


def classify_intent(
    query: str,
    document_key: Optional[str] = None,
    chat_history: Optional[list] = None
) -> Dict:
    """Convenience function for intent classification."""
    classifier = IntentClassifier()
    return classifier.classify(query, document_key, chat_history)
