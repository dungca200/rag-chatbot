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
- rag: ONLY for questions about user's UPLOADED documents (e.g., "What does my PDF say about X?", "Summarize my uploaded file", "Find in my document")
- web_search: For general knowledge questions, facts, current events, definitions, explanations (e.g., "What is the powerhouse of a cell?", "Who is the president?", "How does X work?")
- conversation: For greetings, smalltalk, personal chat, help requests, questions about the bot itself (e.g., "Hello", "How are you?", "What can you do?")
- document: For file upload/processing requests (e.g., "Upload a file", "Process this document")

IMPORTANT:
- Use "rag" ONLY when the user explicitly refers to their uploaded documents
- Use "web_search" for any factual/knowledge question that doesn't mention uploaded documents
- Default to "conversation" for ambiguous social queries

User Query: {query}

Classify the intent and select the appropriate agent."""


class IntentClassifier:
    """Classifies user intent and routes to appropriate agent."""

    def __init__(self):
        self.llm = get_chat_model(temperature=0.0)
        self.structured_llm = self.llm.with_structured_output(IntentClassification)

    def classify(
        self,
        query: str,
        document_key: Optional[str] = None
    ) -> Dict:
        """
        Classify the intent of a user query.

        Args:
            query: The user's query
            document_key: If provided, overrides to rag agent

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
            prompt = CLASSIFICATION_PROMPT.format(query=query)
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
    document_key: Optional[str] = None
) -> Dict:
    """Convenience function for intent classification."""
    classifier = IntentClassifier()
    return classifier.classify(query, document_key)
