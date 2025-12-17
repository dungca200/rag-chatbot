import logging
from typing import Dict, Optional, Literal

from pydantic import BaseModel, Field

from core.clients.gemini_client import get_chat_model

logger = logging.getLogger(__name__)


# Agent types for routing
AgentType = Literal["rag", "conversation", "document"]


class IntentClassification(BaseModel):
    """Schema for intent classification output."""
    agent: AgentType = Field(
        description="The agent that should handle this query: 'rag' for knowledge/document questions, 'conversation' for greetings/smalltalk, 'document' for file processing"
    )
    rationale: str = Field(
        description="Brief explanation of why this agent was selected"
    )


CLASSIFICATION_PROMPT = """You are an intent classifier for a RAG chatbot. Analyze the user query and determine which agent should handle it.

Available agents:
- rag: For questions that require searching documents/knowledge base, factual queries, information retrieval
- conversation: For greetings, smalltalk, general chat, help requests, clarifications
- document: For file upload requests, document processing, asking about uploaded files

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
