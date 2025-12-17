from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from rag.agents.orchestrator_agent import OrchestratorAgent
from rag.agents.rag_agent import RagAgent
from rag.agents.web_search_agent import WebSearchAgent
from rag.agents.document_query_agent import DocumentQueryAgent
from rag.agents.invoice_details_agent import InvoiceDetailsAgent
from rag.agents.query_splitter_agent import QuerySplitterAgent
from rag.agents.response_agent import ResponseAgent
from rag.agents.document_classifier_agent import DocumentClassifierAgent
from rag.agents.greeting_agent import GreetingAgent
from rag.agents.bank_statement_details_agent import BankStatementDetailsAgent
from rag.agents.loan_details_agent import LoanDetailsAgent
from rag.graph.state import AgentState
from typing import Dict, List, Optional, Any
import uuid
import logging
from rag.services.conversation_service import ConversationService
from rag.utils.db_connection import get_connection_pool
from settings import settings

class WorkflowManager:
    def __init__(
        self,
        orchestrator_agent: Optional[OrchestratorAgent] = None,
        rag_agent: Optional[RagAgent] = None,
        web_search_agent: Optional[WebSearchAgent] = None,
        document_query_agent: Optional[DocumentQueryAgent] = None,
        invoice_details_agent: Optional[InvoiceDetailsAgent] = None,
        query_splitter_agent: Optional[QuerySplitterAgent] = None,
        response_agent: Optional[ResponseAgent] = None,
        document_classifier_agent: Optional[DocumentClassifierAgent] = None,
        greeting_agent: Optional[GreetingAgent] = None,
        bank_statement_details_agent: Optional[BankStatementDetailsAgent] = None,
        loan_details_agent: Optional[LoanDetailsAgent] = None
    ):
        # Initialize agents
        self.orchestrator = orchestrator_agent or OrchestratorAgent()
        self.rag_agent = rag_agent or RagAgent()
        self.web_search_agent = web_search_agent or WebSearchAgent()
        self.document_query_agent = document_query_agent or DocumentQueryAgent()
        self.invoice_details_agent = invoice_details_agent or InvoiceDetailsAgent()
        self.query_splitter_agent = query_splitter_agent or QuerySplitterAgent()
        self.response_agent = response_agent or ResponseAgent()
        self.document_classifier_agent = document_classifier_agent or DocumentClassifierAgent()
        self.greeting_agent = greeting_agent or GreetingAgent()
        self.bank_statement_details_agent = bank_statement_details_agent or BankStatementDetailsAgent()
        self.loan_details_agent = loan_details_agent or LoanDetailsAgent()
          # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Only initialize DB pool & PostgresSaver when checkpointing is enabled
        if settings.ENABLE_LANGGRAPH_CHECKPOINT:
            try:
                self.connection_pool = get_connection_pool()
                self.postgres_saver = PostgresSaver(self.connection_pool)
                self.postgres_saver.table_name = "langgraph_checkpoints"
                self.postgres_saver.setup()
                self.logger.info("LangGraph checkpointing enabled - successfully initialized database connection using global pool")
            except Exception as e:
                self.logger.error(f"Failed to initialize LangGraph saver: {str(e)}")
                raise e
        else:
            self.connection_pool = None
            self.postgres_saver = None
            self.logger.info("LangGraph checkpointing DISABLED - no database connection for checkpoints")
        
        self.app = self._build_workflow_graph()
        self.conversation_service = ConversationService()

    def orchestrator_node(self, state: AgentState) -> AgentState:
        result = self.orchestrator.process_query(
            query=state["query"],
            company_id=state["company_id"],
            document_key=state["document_key"],
            session_id=state.get("thread_id", None) 
        )
        state["target_agent"] = result["data"]["target_agent"]
        return state

    def rag_node(self, state: AgentState) -> AgentState:
        result = self.rag_agent.process_query(
            query=state["query"],
            company_id=state["company_id"],
            document_key=state["document_key"],
            session_id=state.get("thread_id", None)
        )
        # Add agent_type to the response
        result["agent_type"] = "rag_agent"
        state["responses"].append(result)
        state["resources"].extend(result["data"]["resources"])
        return state

    def web_search_node(self, state: AgentState) -> AgentState:
        result = self.web_search_agent.process_query(
            query=state["query"],
            company_id=state["company_id"],
            session_id=state.get("thread_id", None)
        )
        # Add agent_type to the response
        result["agent_type"] = "web_search_agent"
        state["responses"].append(result)
        state["resources"].extend(result["data"]["resources"])
        return state

    def document_query_node(self, state: AgentState) -> AgentState:
        result = self.document_query_agent.process_query(
            query=state["query"],
            company_id=state["company_id"],
            session_id=state.get("thread_id", None)
        )
        # Add agent_type to the response
        result["agent_type"] = "document_query_agent"
        state["responses"].append(result)
        state["resources"].extend(result["data"]["resources"])
        return state

    def invoice_details_node(self, state: AgentState) -> AgentState:
        result = self.invoice_details_agent.process_query(
            query=state["query"],
            company_id=state["company_id"],
            session_id=state.get("thread_id", None)
        )
        # Add agent_type to the response
        result["agent_type"] = "invoice_details_agent"
        state["responses"].append(result)
        state["resources"].extend(result["data"]["resources"])
        return state

    def query_splitter_node(self, state: AgentState) -> AgentState:
        result = self.query_splitter_agent.process_query(
            query=state["query"],
            company_id=state["company_id"]
        )
        result["agent_type"] = "query_splitter_agent"
        state["logs"] = result["data"]["logs"]
        state["responses"] = []
        return state

    def bank_statement_details_node(self, state: AgentState) -> AgentState:
        result = self.bank_statement_details_agent.process_query(
            query=state["query"],
            company_id=state["company_id"],
            session_id=state.get("thread_id", None)
        )
        
        result["agent_type"] = "bank_statement_details_agent"
        state["responses"].append(result)
        state["resources"].extend(result["data"]["resources"])
        return state

    def loan_details_node(self, state: AgentState) -> AgentState:
        result = self.loan_details_agent.process_query(
            query=state["query"],
            company_id=state["company_id"],
            session_id=state.get("thread_id", None)  
        )
        
        result["agent_type"] = "loan_details_agent"
        state["responses"].append(result)
        state["resources"].extend(result["data"]["resources"])
        return state

    def process_sub_queries(self, state: AgentState) -> AgentState:
        for log in state["logs"]:
            sub_query = log["query"]
            sub_state = {
                "query": sub_query,
                "company_id": state["company_id"],
                "document_key": state["document_key"],
                "thread_id": state.get("thread_id"),
                "responses": [],
                "resources": state["resources"],
                "target_agent": None,
                "logs": []
            }
            
            sub_state = self.orchestrator_node(sub_state)
            target_agent = sub_state["target_agent"]
            agent_nodes = {
                "rag_agent": self.rag_node,
                "web_search_agent": self.web_search_node,
                "document_query_agent": self.document_query_node,
                "invoice_details_agent": self.invoice_details_node,
                "bank_statement_details_agent": self.bank_statement_details_node,
                "loan_details_agent": self.loan_details_node,
                "document_classifier_agent": self.document_classifier_node,
                "greeting_agent": self.greeting_node
            }
            if target_agent in agent_nodes:
                sub_state = agent_nodes[target_agent](sub_state)
            state["responses"].extend(sub_state["responses"])
            state["resources"].extend(sub_state["resources"])
        return state

    def response_node(self, state: AgentState) -> AgentState:
        result = self.response_agent.process_query(
            query=state["query"],
            responses=state["responses"],
            company_id=state["company_id"],
            session_id=state.get("thread_id", None)
        )
        if not "agent_type" in result:
            result["agent_type"] = "response_agent"
        state["responses"] = [result]
        state["resources"] = list(set(state["resources"]))
        return state

    def document_classifier_node(self, state: AgentState) -> AgentState:
        result = self.document_classifier_agent.process_query(
            query=state["query"],
            company_id=state["company_id"],
            document_key=state["document_key"],
            session_id=state.get("thread_id", None) 
        )
        
        result["agent_type"] = "document_classifier_agent"
        state["responses"].append(result)
        state["resources"].extend(result["data"]["resources"])
        return state

    def greeting_node(self, state: AgentState) -> AgentState:
        result = self.greeting_agent.process_query(
            query=state["query"],
            company_id=state["company_id"],
            document_key=state["document_key"],
            session_id=state.get("thread_id", None) 
        )
        result["agent_type"] = "greeting_agent"
        state["responses"].append(result)
        state["resources"] = []
        return state

    def _route_from_orchestrator(self, state: AgentState) -> str:
        return state["target_agent"]

    def _build_workflow_graph(self) -> Any:

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("orchestrator", self.orchestrator_node)
        workflow.add_node("rag_agent", self.rag_node)
        workflow.add_node("web_search_agent", self.web_search_node)
        workflow.add_node("document_query_agent", self.document_query_node)
        workflow.add_node("invoice_details_agent", self.invoice_details_node)
        workflow.add_node("query_splitter_agent", self.query_splitter_node)
        workflow.add_node("process_sub_queries", self.process_sub_queries)
        workflow.add_node("response_agent", self.response_node)
        workflow.add_node("document_classifier_agent", self.document_classifier_node)
        workflow.add_node("greeting_agent", self.greeting_node)
        workflow.add_node("bank_statement_details_agent", self.bank_statement_details_node)
        workflow.add_node("loan_details_agent", self.loan_details_node)

        # Set entry point
        workflow.set_entry_point("orchestrator")

        # Conditional edges from orchestrator
        workflow.add_conditional_edges(
            "orchestrator",
            self._route_from_orchestrator,
            {
                "rag_agent": "rag_agent",
                "web_search_agent": "web_search_agent",
                "document_query_agent": "document_query_agent",
                "invoice_details_agent": "invoice_details_agent",
                "document_classifier_agent": "document_classifier_agent",
                "query_splitter_agent": "query_splitter_agent",
                "greeting_agent": "greeting_agent",
                "bank_statement_details_agent": "bank_statement_details_agent",
                "loan_details_agent": "loan_details_agent",
            }
        )

        # Edges for single-agent paths to response
        for agent in ["rag_agent", "web_search_agent", "document_query_agent", "invoice_details_agent", 
                     "document_classifier_agent", "greeting_agent", "bank_statement_details_agent", "loan_details_agent"]:
            workflow.add_edge(agent, "response_agent")

        # Edges for multi-part query path
        workflow.add_edge("query_splitter_agent", "process_sub_queries")
        workflow.add_edge("process_sub_queries", "response_agent")        # Set finish point
        workflow.add_edge("response_agent", END)

        # Compile the graph with or without persistence
        if self.postgres_saver:
            return workflow.compile(checkpointer=self.postgres_saver)
        else:
            return workflow.compile()

    def process_user_query(self, query: str, company_id: Optional[str] = None, document_key: Optional[str] = None, thread_id: Optional[str] = None) -> Dict:
        # Generate thread_id if not provided
        thread_id = thread_id or str(uuid.uuid4())
        
        # Save the user query to conversation history BEFORE processing
        if company_id and thread_id:
            try:
                # Get or create the conversation
                conversation, _, _ = self.conversation_service.get_or_create_conversation(
                    company_id=int(company_id),
                    session_id=thread_id
                )
                
                # Save the user message first
                self.conversation_service.add_message(
                    conversation=conversation,
                    role='user',
                    content=query,
                    document_key=document_key
                )
            except Exception as e:
                self.logger.error(f"Error saving user message to conversation: {str(e)}")
          # Check if we have an existing thread and checkpointing is enabled
        initial_state = {
            "query": query,
            "company_id": company_id,
            "document_key": document_key,
            "thread_id": thread_id,
            "responses": [],
            "resources": [],
            "target_agent": None,
            "logs": []
        }
        
        if self.postgres_saver:
            try:
                # If thread exists, load checkpoint
                config_dict = self.postgres_saver.get_checkpoint(thread_id)
                app = self.app.with_config(config_dict)
                result = app.invoke(initial_state)
            except:
                # New thread, initialize state with persistence
                result = self.app.invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
        else:
            # No persistence - just run the workflow without checkpointing
            result = self.app.invoke(initial_state)
        
        # Save the assistant's response AFTER processing
        if company_id and thread_id and "responses" in result and result["responses"]:
            try:
                conversation, _, _ = self.conversation_service.get_or_create_conversation(
                    company_id=int(company_id),
                    session_id=thread_id
                )
                
                # Get the response content from the result
                response_content = result["responses"][0].get("data", {}).get("response", "")
                if response_content:
                    self.conversation_service.add_message(
                        conversation=conversation,
                        role='assistant',
                        content=response_content,
                        document_key=document_key
                    )
            except Exception as e:
                self.logger.error(f"Error saving assistant message to conversation: {str(e)}")        # Return final response
        return {"thread_id": thread_id, **result["responses"][0]}
    
    def setup_langgraph_checkpoint_table(self) -> bool:
        """Setup the PostgreSQL table required for LangGraph checkpoints."""
        if not self.postgres_saver:
            self.logger.warning("LangGraph checkpointing is disabled - cannot setup checkpoint table")
            return False
            
        try:
            self.logger.info("Setting up LangGraph checkpoint table")
            self.postgres_saver.setup()
            self.logger.info("Successfully set up LangGraph checkpoint table")
            return True
        except Exception as e:
            self.logger.error(f"Error setting up LangGraph checkpoint table: {str(e)}")
            return False
      
    def migrate_conversations(self) -> bool:
        """Migrate existing conversations from the Django database to LangGraph's checkpoint format."""
        if not self.postgres_saver:
            self.logger.warning("LangGraph checkpointing is disabled - cannot migrate conversations")
            return False
            
        try:
            self.logger.info("Starting migration of conversations to LangGraph")
            
            # First make sure the checkpoint table exists
            self.setup_langgraph_checkpoint_table()
            
            # Using the conversation service to migrate data
            self.conversation_service.migrate_conversations_to_langgraph(
                connection_pool=self.connection_pool,
                table_name="langgraph_checkpoints"
            )
            
            self.logger.info("Migration of conversations completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during conversation migration: {str(e)}")
            return False

default_workflow_manager = WorkflowManager()
process_user_query = default_workflow_manager.process_user_query