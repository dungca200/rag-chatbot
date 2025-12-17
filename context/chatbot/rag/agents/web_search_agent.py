import logging
from langchain_community.tools import Tool
from typing import List, Dict
from tavily import TavilyClient
from langchain_openai import ChatOpenAI
from settings import settings
import uuid
from datetime import datetime
from rag.agents.rag_agent import GLOBAL_SESSION_STORE
from promptlayer import PromptLayer
from extraction.clients.promptlayer_client import PromptLayerClient
from rag.services.conversation_service import ConversationService

class WebSearchAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL_V2)
        self.pl_client = PromptLayerClient()
        self.conversation_service = ConversationService()
        
        # This will be retrieved from PromptLayer
        self.web_search_tool = Tool(
            name="web_search",
            func=self._web_search,
            description="Tool to perform a web search using Tavily."
        )

    def _web_search(self, query: str, max_results: int = 1) -> List[Dict]:
        """Tool to perform a web search using Tavily."""
        self.logger.info(f"Tool used: 'web_search_tool'")
        self.logger.info(f"Web search: query='{query}', max_results={max_results}")
        try:
            response = self.tavily_client.search(query, max_results=max_results)
            if not response.get("results"):
                return [{"status": "not_found", "message": f"No web results found for '{query}'"}]
            return [{"content": r["content"], "url": r["url"], "title": r["title"]} for r in response["results"]]
        except Exception as e:
            self.logger.error(f"Web search failed: {str(e)}")
            return [{"error": f"Web search failed: {str(e)}"}]

    def _get_session_data(self, session_id: str) -> Dict:
        """Retrieve session data from the session store."""
        return GLOBAL_SESSION_STORE.get(session_id, {})

    def _save_session_data(self, session_id: str, data: Dict):
        """Save session data to the session store."""
        GLOBAL_SESSION_STORE[session_id] = data
        self.logger.info(f"Saved session data for {session_id}")

    def process_query(self, query: str, company_id: str = None, document_key: str = None, session_id: str = None) -> Dict:
        """Process a query, aggregating resources across multi-part queries."""
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
        
        session_data = self._get_session_data(session_id)
        existing_resources = session_data.get("resources", [])
        existing_response = session_data.get("last_response", "")

        results = self._web_search(query)
        context = "\n".join([f"{r['title']}: {r['content']} ({r['url']})" for r in results if "content" in r]) or "No results found."
        
        # Get conversation context if session_id is provided
        conversation_context = ""
        if company_id and session_id:
            conversation_context = self.conversation_service.get_agent_conversation_context(
                session_id=session_id,
                company_id=int(company_id)
            )
        else:
            conversation_context = existing_response or "None"
            
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Input variables for the prompt
        input_variables = {
            "query": query,
            "context": context,
            "current_date": current_date,
            "conversation_context": conversation_context
        }

        # Get the prompt template from PromptLayer using the template ID stored in settings
        pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
        prompt_template = pl.templates.get(
            settings.WEB_SEARCH_AGENT_PROMPT,
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
        prompt = system_message if system_message else f"You are an assistant. Answer this query: {query}"

        messages = [
            {"role": "system", "content": prompt}
        ]
        
        response = self.llm.invoke(
            input=messages,
        ).content

        new_resources = [r["url"] for r in results if "url" in r and r["url"]]
        all_resources = list(set(existing_resources + new_resources))
        combined_response = f"{existing_response}\n\n{response}" if existing_response else response
        self._save_session_data(session_id, {"resources": all_resources, "last_response": combined_response})

        # Save assistant response to conversation history
        if company_id and session_id:
            # Collect sources for inclusion in the conversation history
            sources = [r["url"] for r in results if "url" in r and r["url"]]
            source_info = f" (sources: {', '.join(sources)})" if sources else ""
            
            self.conversation_service.save_agent_message(
                session_id=session_id,
                company_id=int(company_id),
                content=f"{response}{source_info}",
                role="assistant",
                document_key=document_key
            )

        return {
            "message": "Query processed successfully",
            "data": {
                "response": response,
                "company_id": company_id,
                "resources": all_resources,
                "session_id": session_id
            }
        }