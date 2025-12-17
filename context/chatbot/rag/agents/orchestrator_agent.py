import logging
from langchain_community.tools import Tool
from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from settings import settings
from promptlayer import PromptLayer
from extraction.clients.promptlayer_client import PromptLayerClient
from rag.services.conversation_service import ConversationService
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Literal

class AgentRoute(BaseModel):
    """Schema for agent routing decisions."""
    agent: Literal[
        "rag_agent", "web_search_agent", "document_query_agent", 
        "invoice_details_agent", "loan_details_agent", 
        "bank_statement_details_agent", "document_classifier_agent",
        "query_splitter_agent", "greeting_agent"
    ] = Field(description="The agent that should handle this query")
    rationale: str = Field(description="Brief explanation of why this agent was selected")

class OrchestratorAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL_V2)
        self.structured_llm = self.llm.with_structured_output(AgentRoute)
        self.pl_client = PromptLayerClient()
        self.conversation_service = ConversationService()
        
        self.routing_tool_langchain = Tool(
            name="routing_tool",
            func=self.routing_tool,
            description="Tool to decide where to route the user query."
        )   

    def routing_tool(self, query: str, company_id: Optional[str] = None, document_key: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
        """Tool to decide where to route the user query."""
        self.logger.info(f"Tool used: 'routing_tool'")
        
        # Get conversation context if session_id is provided
        conversation_context = ""
        if company_id and session_id:
            conversation_context = self.conversation_service.get_agent_conversation_context(
                session_id=session_id,
                company_id=int(company_id),
                limit=10  # Increase limit to include more conversation history
            )
        
        # Handle extremely short queries directly without calling LLM
        if len(query.strip()) <= 3 or not any(c.isalpha() for c in query):
            return {
                "agent": "greeting_agent", 
                "rationale": "Query is extremely short or unreadable, routing to greeting agent for clarification."
            }
        
        # Prepare input variables for PromptLayer
        input_variables = {
            "query": query,
            "company_id": company_id or 'Not specified',
            "document_key": document_key or 'None',
            "session_id": session_id or 'None',
            "conversation_context": conversation_context or 'No previous conversation'
        }
        
        try:
            # Get the Prompt Template from PromptLayer using the Template ID
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                settings.AGENT_ORCHESTRATOR_PROMPT,
                {
                    "provider": "openai",
                    "input_variables": input_variables,
                    "label": settings.ENV,
                }
            )
            
            messages = prompt_template.get('llm_kwargs', {}).get('messages', [])
            
            if not messages:
                self.logger.warning("No messages found in prompt template, using fallback")
                # Fallback to a simple system message
                messages = [
                    {"role": "system", "content": "You are an AI orchestrator that routes user queries to specialized agents."},
                    {"role": "user", "content": f"Query: {query}\nCompany ID: {company_id or 'Not specified'}\nDocument Key: {document_key or 'None'}\nSession ID: {session_id or 'None'}\nConversation Context: {conversation_context or 'No previous conversation'}"}
                ]
            
            # Get structured output
            routing_decision = self.structured_llm.invoke(messages)
            
            # When document_key is provided, always override to use rag_agent
            if document_key and document_key.lower() != 'none':
                if routing_decision.agent != "rag_agent":
                    routing_decision.agent = "rag_agent"
                    routing_decision.rationale = f"Overridden to rag_agent because document_key is provided: {document_key}"
            
            return {
                "agent": routing_decision.agent,
                "rationale": routing_decision.rationale
            }
            
        except Exception as e:
            self.logger.error(f"Routing tool failed: {str(e)}")
            # Default to greeting agent in case of errors
            return {
                "agent": "greeting_agent",
                "rationale": f"Error in routing, defaulting to greeting agent: {str(e)}"
            }

    def process_query(self, query: str, company_id: str = None, document_key: str = None, session_id: str = None) -> Dict:
        """Main method to process and route the query."""
        # Save the user query to conversation history
        if company_id and session_id:
            self.conversation_service.save_agent_message(
                session_id=session_id,
                company_id=int(company_id),
                content=query,
                role="user",
                document_key=document_key
            )
            
        routing_result = self.routing_tool(query, company_id, document_key, session_id)
        
        return {
            "message": "Query routed successfully",
            "data": {
                "target_agent": routing_result["agent"],
                "query": query,
                "company_id": company_id
            }
        }