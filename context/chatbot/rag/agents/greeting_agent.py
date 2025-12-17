import logging
from typing import Dict, Optional
from langchain_community.tools import Tool
from langchain_openai import ChatOpenAI
from settings import settings
from promptlayer import PromptLayer
from extraction.clients.promptlayer_client import PromptLayerClient
from datetime import datetime
from rag.services.conversation_service import ConversationService
from rag.utils.response_templates import FALLBACK_TEMPLATES

class GreetingAgent:
    """Agent for handling greetings and simple conversational queries."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL_V2)
        self.pl_client = PromptLayerClient()
        self.conversation_service = ConversationService()
        
        self.fallback_response = FALLBACK_TEMPLATES["SENSITIVE_QUERY"]
        
        self.sensitive_topics = [
            "prompt", "system message", "instructions", "how do you work", 
            "your code", "your programming", "your implementation", 
            "token", "api key", "password", "credentials"
        ]
        
        self.greeting_tool_langchain = Tool(
            name="greeting_tool",
            func=self.greeting_tool,
            description="Tool to handle greetings and conversational queries."
        )
    
    def _is_sensitive_query(self, query: str) -> bool:
        """Check if the query contains sensitive topics."""
        query = query.lower()
        is_sensitive = any(topic in query for topic in self.sensitive_topics)
        if is_sensitive:
            self.logger.warning(f"Sensitive query detected")
        return is_sensitive
    
    def greeting_tool(self, query: str, company_id: Optional[str] = None, document_key: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
        """Tool to handle greetings and conversational queries."""
        self.logger.info(f"Tool used: 'greeting_tool'")
        
        if self._is_sensitive_query(query):
            self.logger.info("Returning fallback response for sensitive query")
            return {"response": self.fallback_response}
        
        conversation_context = ""
        if company_id and session_id:
            conversation_context = self.conversation_service.get_agent_conversation_context(
                session_id=session_id,
                company_id=int(company_id),
                limit=10
            )
        
        input_variables = {
            "query": query,
            "company_id": company_id or "Not specified",
            "document_key": document_key or "None",
            "session_id": session_id or "None",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "conversation_context": conversation_context or "No previous conversation"
        }
        
        try:
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template_id = settings.GREETING_AGENT_PROMPT
            
            prompt_template = pl.templates.get(
                prompt_template_id,
                {
                    "provider": "openai",
                    "input_variables": input_variables,
                    "label": settings.ENV,
                }
            )
            
            messages = prompt_template.get('llm_kwargs', {}).get('messages', [])
            
            if not messages:
                self.logger.warning("No messages found in prompt template, using fallback")
                messages = [
                    {"role": "system", "content": "You are Aira, Documa8e's AI assistant."},
                    {"role": "user", "content": query}
                ]
            
            response = self.llm.invoke(
                input=messages,
                model=settings.OPENAI_MODEL_V2,
            )
            
            return {"response": response.content}
            
        except Exception as e:
            self.logger.error(f"Greeting tool failed: {str(e)}")
            greeting = "Hello! I'm Aira, Documa8e's AI assistant. How can I help you today?"
            return {"response": greeting}
    
    def process_query(self, query: str, company_id: str = None, document_key: str = None, session_id: str = None) -> Dict:
        """Process a greeting query and return a response."""
        
        # Save user message to conversation history
        if company_id and session_id:
            self.conversation_service.save_agent_message(
                session_id=session_id,
                company_id=int(company_id),
                content=query,
                role="user",
                document_key=document_key
            )
        
        greeting_result = self.greeting_tool(query, company_id, document_key, session_id)
        
        # Save assistant response to conversation history
        if company_id and session_id:
            self.conversation_service.save_agent_message(
                session_id=session_id,
                company_id=int(company_id),
                content=greeting_result["response"],
                role="assistant",
                document_key=document_key
            )
        
        return {
            "message": "Greeting processed successfully",
            "data": {
                "response": greeting_result["response"],
                "company_id": company_id,
                "resources": [],
                "session_id": session_id
            }
        }
