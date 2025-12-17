import logging
from langchain_community.tools import Tool
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from settings import settings
import json
import uuid
from rag.agents.rag_agent import GLOBAL_SESSION_STORE
from promptlayer import PromptLayer
from extraction.clients.promptlayer_client import PromptLayerClient
from rag.services.conversation_service import ConversationService

class QuerySplitterAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL_V2)
        self.pl_client = PromptLayerClient()
        self.conversation_service = ConversationService()
        
        self.query_splitter_tool = Tool(
            name="query_splitter",
            func=self._query_splitter,
            description="Tool to split a multi-part query into individual queries."
        )

    def _query_splitter(self, query: str, company_id: Optional[str] = None, session_id: Optional[str] = None) -> List[str]:
        """Tool to split a multi-part query into individual queries."""
        self.logger.info(f"Tool used: 'query_splitter_tool'")
        try:
            # Get conversation context if session_id is provided
            conversation_context = ""
            if company_id and session_id:
                conversation_context = self.conversation_service.get_agent_conversation_context(
                    session_id=session_id,
                    company_id=int(company_id)
                )
            
            # Input variables for the prompt
            input_variables = {
                "query": query,
                "conversation_context": conversation_context or "No previous conversation"
            }

            # Get the prompt template from PromptLayer using the template ID stored in settings
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                settings.QUERY_SPLITTER_AGENT_PROMPT,
                {
                    "provider": "openai",
                    "input_variables": input_variables,
                    "label": settings.ENV,
                }
            )

            # Extract system message from the template
            system_message = None
            for message in prompt_template['llm_kwargs']['messages']:
                if message['role'] == 'system':
                    system_message = message['content']
                    break

            # Use the system message if it exists, otherwise fall back to a default
            prompt = system_message if system_message else f"Split this query into parts: {query}"

            messages = [
                {"role": "system", "content": prompt}
            ]
            
            response = self.llm.invoke(
                input=messages,
                response_format={"type": "json_object"}
            )
            
            split_result = json.loads(response.content)
            return split_result.get("queries", [query])
        except Exception as e:
            self.logger.error(f"Query splitting failed: {str(e)}")
            return [query]

    def _get_session_data(self, session_id: str) -> Dict:
        """Retrieve session data from the session store."""
        return GLOBAL_SESSION_STORE.get(session_id, {})

    def _save_session_data(self, session_id: str, data: Dict):
        """Save session data to the session store."""
        GLOBAL_SESSION_STORE[session_id] = data
        self.logger.info(f"Saved session data for {session_id}")

    def process_query(self, query: str, company_id: str = None, document_key: str = None, session_id: str = None) -> Dict:
        """Main method to process the query and generate a response."""
        try:
            # Use existing session_id or create a new one
            session_id = session_id or str(uuid.uuid4())
            
            # Save user message to conversation history
            if company_id and session_id:
                self.conversation_service.save_agent_message(
                    session_id=session_id,
                    company_id=int(company_id),
                    content=query,
                    role="user",
                    document_key=document_key
                )
            
            split_queries = self._query_splitter(query, company_id, session_id)
            logs = [{"arrangement": i+1, "query": q, "company_id": company_id} for i, q in enumerate(split_queries)]
            
            # Save session data
            self._save_session_data(session_id, {"split_logs": logs})
            
            # Save system message about split queries
            system_message = f"Split the query into {len(split_queries)} parts: " + ", ".join(split_queries)
            if company_id and session_id:
                self.conversation_service.save_agent_message(
                    session_id=session_id,
                    company_id=int(company_id),
                    content=system_message,
                    role="assistant"
                )
            
            return {
                "message": "Query split successfully",
                "data": {
                    "response": f"Split into {len(split_queries)} queries",
                    "company_id": company_id,
                    "resources": [],
                    "session_id": session_id,
                    "logs": logs
                }
            }
        except Exception as e:
            self.logger.error(f"Error processing query: {str(e)}")
            return {
                "message": "Query splitting failed",
                "data": {
                    "response": "Failed to split query",
                    "error": str(e)
                }
            }