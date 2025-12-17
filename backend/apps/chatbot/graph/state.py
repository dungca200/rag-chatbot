from typing import TypedDict, List, Dict, Optional, Literal


class AgentState(TypedDict):
    """State schema for LangGraph workflow."""

    # Input
    query: str
    user_id: str
    thread_id: str
    document_key: Optional[str]
    persist_embeddings: bool  # Toggle: True=store mode, False=session mode

    # Routing
    target_agent: Optional[Literal["rag", "conversation", "document"]]

    # RAG context
    retrieved_context: List[Dict]

    # Output
    responses: List[Dict]
    sources: List[str]

    # Logging
    logs: List[Dict]
