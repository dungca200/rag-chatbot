import logging
import uuid
from typing import Dict, Optional

from langgraph.graph import StateGraph, END

from apps.chatbot.graph.state import AgentState
from apps.chatbot.agents import (
    orchestrator_node,
    route_to_agent,
    rag_agent_node,
    conversation_agent_node,
    document_agent_node
)

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages the LangGraph workflow for the RAG chatbot."""

    def __init__(self):
        self.app = self._build_workflow_graph()
        logger.info("WorkflowManager initialized")

    def _build_workflow_graph(self):
        """Build and compile the LangGraph workflow."""

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("orchestrator", orchestrator_node)
        workflow.add_node("rag_agent", rag_agent_node)
        workflow.add_node("conversation_agent", conversation_agent_node)
        workflow.add_node("document_agent", document_agent_node)

        # Set entry point
        workflow.set_entry_point("orchestrator")

        # Conditional edges from orchestrator
        workflow.add_conditional_edges(
            "orchestrator",
            route_to_agent,
            {
                "rag_agent": "rag_agent",
                "conversation_agent": "conversation_agent",
                "document_agent": "document_agent"
            }
        )

        # All agents go to END
        workflow.add_edge("rag_agent", END)
        workflow.add_edge("conversation_agent", END)
        workflow.add_edge("document_agent", END)

        # Compile
        return workflow.compile()

    def process_query(
        self,
        query: str,
        user_id: str,
        thread_id: Optional[str] = None,
        document_key: Optional[str] = None,
        persist_embeddings: bool = False
    ) -> Dict:
        """
        Process a user query through the workflow.

        Args:
            query: The user's query
            user_id: User identifier
            thread_id: Conversation thread ID (generated if not provided)
            document_key: Optional specific document to query
            persist_embeddings: Whether to persist embeddings (store mode)

        Returns:
            Dict with response, sources, and thread_id
        """
        # Generate thread_id if not provided
        thread_id = thread_id or str(uuid.uuid4())

        # Initialize state
        initial_state: AgentState = {
            "query": query,
            "user_id": user_id,
            "thread_id": thread_id,
            "document_key": document_key,
            "persist_embeddings": persist_embeddings,
            "target_agent": None,
            "retrieved_context": [],
            "responses": [],
            "sources": [],
            "logs": []
        }

        logger.info(f"Processing query for user {user_id}, thread {thread_id}")

        # Run workflow
        result = self.app.invoke(initial_state)

        # Extract response
        responses = result.get("responses", [])
        if responses:
            last_response = responses[-1]
            return {
                "success": True,
                "thread_id": thread_id,
                "response": last_response.get("content", ""),
                "agent": last_response.get("agent", "unknown"),
                "sources": result.get("sources", [])
            }

        return {
            "success": False,
            "thread_id": thread_id,
            "response": "I apologize, but I couldn't process your request. Please try again.",
            "agent": "error",
            "sources": []
        }


# Default instance
workflow_manager = WorkflowManager()


def process_user_query(
    query: str,
    user_id: str,
    thread_id: Optional[str] = None,
    document_key: Optional[str] = None,
    persist_embeddings: bool = False
) -> Dict:
    """Convenience function to process queries."""
    return workflow_manager.process_query(
        query=query,
        user_id=user_id,
        thread_id=thread_id,
        document_key=document_key,
        persist_embeddings=persist_embeddings
    )
