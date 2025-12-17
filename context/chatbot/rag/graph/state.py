from typing import TypedDict, List, Dict, Optional

class AgentState(TypedDict):
    query: str
    company_id: Optional[str]
    document_key: Optional[str]
    thread_id: str
    responses: List[Dict]
    resources: List[str]
    target_agent: Optional[str]
    logs: List[Dict]