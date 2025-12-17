import logging
from langchain_community.tools import Tool
from typing import List, Dict, Optional
from supabase import create_client, Client
from langchain_openai import ChatOpenAI
from settings import settings
import uuid
import tiktoken
from datetime import datetime
from rag.utils.text_processing import TextProcessor
from promptlayer import PromptLayer
from extraction.clients.promptlayer_client import PromptLayerClient
from rag.services.conversation_service import ConversationService

GLOBAL_SESSION_STORE = {}

class RagAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.llm = ChatOpenAI(model=settings.OPENAI_MODEL_V2, api_key=settings.OPENAI_API_KEY)
        self.text_processor = TextProcessor()
        self.company_id = None
        self.tokenizer = tiktoken.encoding_for_model(settings.OPENAI_MODEL_V2)
        self.max_tokens = settings.RAG_MAX_TOKENS
        self.pl_client = PromptLayerClient()
        self.conversation_service = ConversationService()
        
        self.semantic_search_tool = Tool(
            name="semantic_search",
            func=self._semantic_search,
            description="Tool to perform semantic search over documents in Supabase."
        )
        
        self.get_document_by_key_tool = Tool(
            name="get_document_by_key",
            func=self._get_document_by_key,
            description="Tool to retrieve a specific document by its key."
        )

    def set_company_id(self, company_id: str):
        """Set the company ID for this agent."""
        self.company_id = str(company_id)

    def _semantic_search(self, query: str, company_id: Optional[str] = None, top_k: int = 1, document_key: Optional[str] = None) -> List[Dict]:
        """Tool to perform semantic search over documents in Supabase."""
        self.logger.info(f"Tool used: 'semantic_search_tool'")
        self.logger.info(f"Semantic search: query='{query}', company_id={company_id}, top_k={top_k}")
        try:
            query_embedding = self.text_processor.get_embedding(query)
            company_id = company_id or self.company_id
            result = self.supabase.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "search_company_id": company_id,
                    "search_key": document_key,
                    "match_threshold": 0.15,
                    "match_count": top_k
                }
            ).execute()
            if not result.data:
                # Fixed the 'No documents found for '{query}'
                return [{"status": "not_found", "message": "I'm sorry, I don't have enough information to provide an answer to your question based on the current document. If you'd like, you can provide additional details or clarify your query."}]
            return [{"key": doc["key"], "content": doc["content"], "similarity": doc["similarity"]} for doc in result.data]
        except Exception as e:
            self.logger.error(f"Semantic search failed: {str(e)}")
            return [{"error": f"Semantic search failed: {str(e)}"}]

    def _get_document_by_key(self, document_key: str) -> List[Dict]:
        """Tool to retrieve a specific document by its key."""
        self.logger.info(f"Tool used: 'get_document_by_key_tool'")
        try:
            parent_key = document_key.split("_chunk_")[0]
            result = self.supabase.rpc("get_document_by_parent_key", {"search_parent_key": parent_key}).execute()
            if result.data:
                return [{"key": doc["key"], "content": doc["content"], "similarity": 1.0} for doc in result.data]
            # Fixed the 'No documents found for '{query}'
            return [{"status": "not_found", "message": "I'm sorry, I don't have enough information to provide an answer to your question based on the current document. If you'd like, you can provide additional details or clarify your query."}]
        except Exception as e:
            self.logger.error(f"Get document by key failed: {str(e)}")
            return [{"error": f"Document retrieval failed: {str(e)}"}]

    def _get_session_data(self, thread_id: str) -> Dict:
        """Retrieve session data from the session store."""
        return GLOBAL_SESSION_STORE.get(thread_id, {})

    def _save_session_data(self, thread_id: str, data: Dict):
        """Save session data to the session store."""
        GLOBAL_SESSION_STORE[thread_id] = data
        self.logger.info(f"Saved session data for {thread_id}")

    def _get_conversation_context(self, thread_id: str, company_id: int) -> str:
        """Get conversation context from database using ConversationService."""
        try:
            if not thread_id or not company_id:
                return ""
                
            # Get more context (10 messages instead of default 5) to provide better history for referential analysis
            return self.conversation_service.get_agent_conversation_context(
                session_id=thread_id, 
                company_id=company_id,
                limit=10  # Increased from default 5
            )
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {str(e)}")
            return ""

    def _save_conversation_message(self, thread_id: str, company_id: int, content: str, role: str, document_key: Optional[str] = None):
        """Save a message to the conversation history."""
        try:
            if not thread_id or not company_id:
                return
                
            self.conversation_service.save_agent_message(
                session_id=thread_id,
                company_id=int(company_id), 
                content=content,
                role=role,
                document_key=document_key
            )

        except Exception as e:
            self.logger.error(f"Error saving conversation message: {str(e)}")

    def _retrieve_documents(self, query: str, document_key: str = None, thread_id: str = None) -> List[Dict]:
        """
        Retrieve relevant documents for a query using document key, conversation context, or semantic search.

        Args:
            query (str): User's query.
            document_key (str, optional): Specific document key to fetch.
            thread_id (str, optional): Session or conversation identifier.

        Returns:
            List[Dict]: List of document dicts or empty if none found.
        """
        try:
            # 1. If document_key is provided, use it
            if document_key:
                self.logger.info(f"Fetching document by key: {document_key}")
                docs = self._get_document_by_key(document_key)
                if docs and "error" not in docs[0]:
                    return docs

            # 2. Get conversation context
            conversation_context = ""
            if thread_id and self.company_id:
                conversation_context = self._get_conversation_context(thread_id, int(self.company_id))

            # 3. If session resources exist, check referential query
            if thread_id and thread_id in GLOBAL_SESSION_STORE:
                session_resources = GLOBAL_SESSION_STORE[thread_id].get('resources', [])
                if session_resources:
                    is_referential = self._is_referential_query(query, conversation_context)
                    self.logger.info(f"Referential query check result: {is_referential} for query: '{query}'")
                    
                    if is_referential:
                        self.logger.info(f"Referential query detected, using last session resource: {session_resources[-1]}")
                        docs = self._get_document_by_key(session_resources[-1])
                        if docs and "error" not in docs[0]:
                            return docs

            # 4. Otherwise, always run a new semantic search
            self.logger.info("New query detected, running semantic search.")
            docs = self._semantic_search(query, self.company_id, 1)
            if docs and "error" not in docs[0]:
                return docs

            return []
        except Exception as e:
            self.logger.error(f"Error in document retrieval: {str(e)}")
            return []

    def _prepare_context(self, docs: List[Dict]) -> str:
        """Prepare context string from retrieved documents."""
        if not docs:
            return "No relevant documents found."
        contexts = []
        total_tokens = 0
        for doc in docs:
            if "error" in doc:
                continue
            chunk = f"From document {doc.get('key', 'Unknown')}:\n{doc.get('content', 'No content available')}"
            chunk_tokens = len(self.tokenizer.encode(chunk))
            if total_tokens + chunk_tokens > self.max_tokens // 2:
                break
            contexts.append(chunk)
            total_tokens += chunk_tokens
        return "\n\n".join(contexts)

    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens)

    def _generate_answer(self, context: str, prompt: str) -> str:
        """Generate an answer using OpenAI based on prompt and context."""
        try:
            prompt_tokens = len(self.tokenizer.encode(prompt))
            context_tokens = len(self.tokenizer.encode(context))
            total_tokens = prompt_tokens + context_tokens + 100

            if total_tokens > self.max_tokens:
                excess_tokens = total_tokens - self.max_tokens
                context_max_tokens = max(0, len(self.tokenizer.encode(context)) - excess_tokens)
                context = self._truncate_text(context, context_max_tokens)

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Context: {context}\nPlease provide an answer based on the prompt and context."}
            ]
            
            response = self.llm.invoke(input=messages)
            return response.content
        except Exception as e:
            self.logger.error(f"Error in generating answer: {str(e)}")
            raise

    def _is_referential_query(self, query: str, conversation_context: str) -> bool:
        """
        Use the LLM to determine if the query refers to the previous document or a new one.
        Returns True if it refers to the previous document, False if it's a new search.
        """
        check_prompt = (
            """
            You are an assistant tasked with analyzing whether a user's query refers to a previously discussed document or requests a new document search.
            
            For this task, you will use a reasoning process:
            1. Analyze what document was last discussed in the conversation context
            2. Identify any explicit references in the new query (phrases like "same document", "this invoice", "it")
            3. Check if the query asks for specific details that would be found in the previously discussed document
            4. Determine if the query mentions a new/different document name or entity
            5. Make your decision based on this analysis
            
            Let's break down your thought process step by step:
            
            Conversation Context:
            {conversation_context}
            
            Query:
            {query}
            
            Thought: First, I'll identify what document was last discussed in the conversation.
            [Analyze the conversation context and identify the last document discussed]
            
            Thought: Now, I'll check if the query contains explicit references to the previous document.
            [Look for phrases like "same document", "this invoice", "it", etc.]
            
            Thought: I'll check if the query asks for specific information likely found in the previous document.
            [Consider if the query asks about dates, amounts, people, or other details contained in a document]
            
            Thought: I'll check if the query mentions a new or different document name or entity.
            [Look for names of different documents, companies, or explicit requests for new searches]
            
            Thought: Based on my analysis, I'll make my decision.
            [Synthesize the above reasoning]
            
            Decision: [ONLY write 'previous' or 'new' here with no other text]
            """
        )
        
        try:
            response = self.llm.invoke(input=[{"role": "user", "content": check_prompt.format(conversation_context=conversation_context, query=query)}])
            answer = response.content.strip().lower()
            
            # Log the full reasoning process for debugging
            self.logger.info(f"Referential query analysis:\n{answer}")
            
            # Extract the decision from the response
            if "decision: previous" in answer:
                self.logger.info("Query determined to reference the previous document")
                return True
            elif "decision: new" in answer:
                self.logger.info("Query determined to request a new document")
                return False
            else:
                # Fallback to simple keyword matching if the structured decision isn't found
                self.logger.warning(f"Structured decision not found in response, falling back to keyword matching")
                result = "previous" in answer and not "new" in answer
                self.logger.info(f"Fallback decision: {'previous' if result else 'new'}")
                return result
        except Exception as e:
            self.logger.error(f"Error in referential query analysis: {str(e)}")
            # Default to treating it as a new query in case of errors
            return False
    
    def process_query(self, query: str, company_id: str = None, document_key: str = None, session_id: str = None) -> Dict:
        """Main method to process the query and generate a response."""
        if company_id:
            self.set_company_id(company_id)
        
        # Use session_id as thread_id if provided, otherwise generate a new one
        thread_id = session_id or str(uuid.uuid4())
        
        conversation_context = ""
        if company_id and thread_id:
            self._save_conversation_message(
                thread_id=thread_id,
                company_id=int(company_id),
                content=query,
                role="user",
                document_key=document_key
            )
            
            conversation_context = self._get_conversation_context(
                thread_id=thread_id,
                company_id=int(company_id)
            )
        else:
            prior_query = self._get_session_data(thread_id).get('last_query', 'None') if thread_id else 'None'
            conversation_context = f"Prior query: {prior_query}"
        
        if not conversation_context:
            conversation_context = "None"
        
        docs = self._retrieve_documents(query, document_key, thread_id)
        context = self._prepare_context(docs)
            
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Input variables for PromptLayer Prompt
        input_variables = {
            "query": query,
            "company_id": self.company_id or "Not specified",
            "document_key": document_key or "None",
            "session_id": thread_id,
            "context": context,
            "current_date": current_date,
            "conversation_context": conversation_context
        }

        # Get the Prompt Template from PromptLayer using the Template ID stored in settings.py
        pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
        prompt_template = pl.templates.get(
            settings.RAG_AGENT_PROMPT,
            {
                "provider": "openai",
                "input_variables": input_variables,
                "label": settings.ENV,
            }
        )

        system_message = None
        for message in prompt_template['llm_kwargs']['messages']:
            if message['role'] == 'system':
                system_message = message['content']
                break

        prompt = system_message if system_message else f"You are an assistant. Answer this query about documents: {query}"
        
        response = self._generate_answer(context, prompt)
        resources = [doc.get("key") for doc in docs if "key" in doc]
        
        if company_id and thread_id:
            response_doc_key = document_key
            if not response_doc_key and resources:
                response_doc_key = resources[0]
                
            self._save_conversation_message(
                thread_id=thread_id,
                company_id=int(company_id),
                content=response,
                role="assistant",
                document_key=response_doc_key
            )
        
        if thread_id:
            self._save_session_data(thread_id, {
                "resources": resources,
                "last_response": response,
                "last_query": query
            })
        
        return {
            "message": "Query processed successfully",
            "data": {
                "response": response,
                "company_id": self.company_id,
                "resources": resources,
                "thread_id": thread_id  # Return thread_id instead of session_id
            }
        }