from typing import TypedDict, List, Dict, Optional, Literal


class ChatMessage(TypedDict):
    """A single chat message."""
    role: Literal["user", "assistant"]
    content: str


class AgentState(TypedDict):
    """State schema for LangGraph workflow."""

    # Input
    query: str
    user_id: str
    thread_id: str
    document_key: Optional[str]
    persist_embeddings: bool  # Toggle: True=store mode, False=session mode
    chat_history: List[ChatMessage]  # Previous messages in conversation

    # Routing
    target_agent: Optional[Literal["rag", "conversation", "document", "web_search"]]

    # RAG context
    retrieved_context: List[Dict]

    # Output
    responses: List[Dict]
    sources: List[str]

    # Logging
    logs: List[Dict]
