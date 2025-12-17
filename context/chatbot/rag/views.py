import logging
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import MultiPartParser, FormParser
from rag.serializers import ChatbotRequestSerializer, SuccessResponseSerializer, ErrorResponseSerializer
from rag.services.conversation_service import ConversationService
from rag.utils.utils import parse_request_body
from rag.agents.orchestrator_agent import OrchestratorAgent
from rag.agents.rag_agent import RagAgent
from rag.agents.web_search_agent import WebSearchAgent
from rag.agents.document_query_agent import DocumentQueryAgent
from rag.agents.invoice_details_agent import InvoiceDetailsAgent
from rag.agents.loan_details_agent import LoanDetailsAgent
from rag.agents.bank_statement_details_agent import BankStatementDetailsAgent
from rag.agents.query_splitter_agent import QuerySplitterAgent
from rag.agents.response_agent import ResponseAgent
from rag.agents.document_classifier_agent import DocumentClassifierAgent
from rag.agents.greeting_agent import GreetingAgent
from rag.graph.workflow import WorkflowManager
class ChatbotView(APIView):
    authentication_classes = []
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize individual agents for specific use cases like document classification
        self.orchestrator_agent = OrchestratorAgent()
        self.rag_agent = RagAgent()
        self.web_search_agent = WebSearchAgent()
        self.document_query_agent = DocumentQueryAgent()
        self.invoice_details_agent = InvoiceDetailsAgent()
        self.loan_details_agent = LoanDetailsAgent()
        self.bank_statement_details_agent = BankStatementDetailsAgent()
        self.query_splitter_agent = QuerySplitterAgent()
        self.response_agent = ResponseAgent()
        self.document_classifier_agent = DocumentClassifierAgent()
        self.greeting_agent = GreetingAgent()
        self.logger = logging.getLogger(__name__)
        
        # Initialize workflow manager with the same agents
        self.workflow_manager = WorkflowManager(
            orchestrator_agent=self.orchestrator_agent,
            rag_agent=self.rag_agent,
            web_search_agent=self.web_search_agent,
            document_query_agent=self.document_query_agent,
            invoice_details_agent=self.invoice_details_agent,
            query_splitter_agent=self.query_splitter_agent,
            response_agent=self.response_agent,
            document_classifier_agent=self.document_classifier_agent,
            greeting_agent=self.greeting_agent,
            bank_statement_details_agent=self.bank_statement_details_agent,
            loan_details_agent=self.loan_details_agent
        )
        
        self.logger.info("ChatbotView initialized with all agents and workflow manager")

    @swagger_auto_schema(
        request_body=ChatbotRequestSerializer,
        responses={
            '200': SuccessResponseSerializer,
            '400': ErrorResponseSerializer,
            '500': ErrorResponseSerializer
        }
    )
    def post(self, request):
        correlation_id = str(uuid.uuid4())

        try:
            req = parse_request_body(request)
            if isinstance(req, Response):
                self.logger.info(f"parse_request_body returned Response: {req.data}")
                return req

            validation = ChatbotRequestSerializer(data=req)
            if not validation.is_valid():
                error_data = {"message": "Invalid request body", "errors": validation.errors}
                self.logger.warning(f"Validation error - correlation_id: {correlation_id}, errors: {validation.errors}")
                return Response(ErrorResponseSerializer(error_data).data, status=status.HTTP_400_BAD_REQUEST)

            company_id = validation.validated_data.get('company_id')
            query = validation.validated_data['query']
            document_key = validation.validated_data.get('document_key')
            session_id = validation.validated_data.get('session_id')
            thread_id = validation.validated_data.get('thread_id')
            
            # Use thread_id if provided, otherwise use session_id
            # This will use the session_id=thread_id mapping done in the serializer's validate method
            conversation_id = thread_id or session_id

            # First check if this is a document classification confirmation
            if conversation_id:
                # Try to get session data from document classifier's session store
                doc_session_data = self.document_classifier_agent._get_session_data(conversation_id)
                if doc_session_data and doc_session_data.get("awaiting_confirmation", False):
                    self.logger.info(f"Found document classification session: {conversation_id}")
                    # Process as document classification confirmation
                    result = self.document_classifier_agent.process_query(
                        query=query,
                        company_id=str(company_id) if company_id else None,
                        session_id=conversation_id
                    )
                    
                    if "data" not in result or not result["data"]:
                        error_data = {"message": result.get("message", "Failed to process document confirmation")}
                        self.logger.error(f"Document confirmation failed - correlation_id: {correlation_id}, error: {error_data}")
                        return Response(ErrorResponseSerializer(error_data).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
                    # Use the result directly from document classifier agent
                    success_data = {"message": "Query processed successfully", "data": result["data"]}
                    
                    # Check if we need to transform the response format
                    if "resources" in result["data"] and "rag_resources" not in result["data"]:
                        # Transform response to match ChatbotResponseSerializer format
                        transformed_data = {
                            "response": result["data"]["response"],
                            "company_id": result["data"]["company_id"],
                            "rag_resources": result["data"]["resources"],
                            "document_table_resources": [],
                            "invoice_details_resources": [],
                            "loan_details_resources": [],
                            "bank_statement_details_resources": [],
                            "web_search_resources": [],
                            "thread_id": result["data"].get("thread_id") or result["data"].get("session_id"),
                            "session_id": result["data"].get("session_id"),
                            "summary": [result["data"].get("classification_result", {}).get("summary", "")] if "classification_result" in result["data"] else []
                        }
                        success_data = {"message": "Query processed successfully", "data": transformed_data}
                    
                    return Response(SuccessResponseSerializer(success_data).data, status=status.HTTP_200_OK)

            # Continue with regular conversation handling if not a document confirmation
            conversation, resolved_session_id, created = ConversationService.get_or_create_conversation(
                company_id=company_id,
                session_id=conversation_id
            )
            if conversation_id and conversation_id != resolved_session_id:
                self.logger.warning(f"Provided conversation_id {conversation_id} not found. Created new session {resolved_session_id}")
            conversation_id = resolved_session_id

            context = ConversationService.get_conversation_context(conversation)
            formatted_context = ConversationService.format_context_for_rag(context)

            response_data = self.process_query_with_agents(
                query=query,
                company_id=str(company_id) if company_id else None,
                document_key=document_key,
                session_id=conversation_id,  # For backward compatibility
                conversation_context=formatted_context
            )

            if "data" not in response_data or not response_data["data"]:
                error_data = {"message": response_data.get("message", "Failed to process query")}
                self.logger.error(f"Response data invalid - correlation_id: {correlation_id}, error: {error_data}")
                return Response(ErrorResponseSerializer(error_data).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            ConversationService.add_message(conversation=conversation, role='user', content=query, document_key=document_key)
            ConversationService.add_message(conversation=conversation, role='assistant', content=response_data["data"]["response"], document_key=document_key)

            # Ensure both thread_id and session_id are in the response for backward compatibility
            if "thread_id" in response_data["data"] and "session_id" not in response_data["data"]:
                response_data["data"]["session_id"] = response_data["data"]["thread_id"]
            elif "session_id" in response_data["data"] and "thread_id" not in response_data["data"]:
                response_data["data"]["thread_id"] = response_data["data"]["session_id"]

            success_data = {"message": "Query processed successfully", "data": response_data["data"]}
            return Response(SuccessResponseSerializer(success_data).data, status=status.HTTP_200_OK)

        except Exception as e:
            self.logger.error(f"Error processing chatbot query: {str(e)} - correlation_id: {correlation_id}")
            error_data = {"message": f"Failed to process query: {str(e)}"}
            return Response(ErrorResponseSerializer(error_data).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def process_query_with_agents(self, query: str, company_id: str = None, document_key: str = None,
                                  session_id: str = None, conversation_context: str = None) -> dict:
        try:
            self.logger.info(f"Processing query using workflow: {query}")
            # Use the workflow manager to process the query
            response = self.workflow_manager.process_user_query(
                query=query,
                company_id=company_id,
                document_key=document_key,
                thread_id=session_id
            )
            
            self.logger.info(f"Workflow returned response with agent_type: {response.get('agent_type', 'unknown')}")
            
            # Add conversation context if provided
            if conversation_context:
                response["data"]["response"] = (
                    f"{response['data']['response']}"
                )
                
            return response
            
        except Exception as e:
            self.logger.error(f"Error in agentic workflow: {str(e)}")
            return {"message": f"Failed to process query: {str(e)}", "data": None}

class DocumentClassifierView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = (MultiPartParser, FormParser)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.document_classifier_agent = DocumentClassifierAgent()
        self.logger = logging.getLogger(__name__)

    @swagger_auto_schema(
        responses={
            '200': SuccessResponseSerializer,
            '400': ErrorResponseSerializer,
            '500': ErrorResponseSerializer
        }
    )
    def post(self, request):
        correlation_id = str(uuid.uuid4())
        self.logger.info(f"Processing document classification - correlation_id: {correlation_id}")
        
        try:
            # Extract form data
            company_id = request.data.get('company_id')
            session_id = request.data.get('session_id')
            document_key = request.data.get('document_key')
            auth_token = request.data.get('auth_token', None)

            if auth_token is None:
                error_data = {"message": "Auth token is required"}
                return Response(ErrorResponseSerializer(error_data).data, status=status.HTTP_401_UNAUTHORIZED)
            
            # Generate session_id if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                self.logger.info(f"Generated new session_id: {session_id}")
            
            # Get file from request
            if 'file' not in request.FILES:
                error_data = {"message": "No file provided"}
                return Response(ErrorResponseSerializer(error_data).data, status=status.HTTP_400_BAD_REQUEST)
            
            file = request.FILES['file']
            file_content = file.read()  # Read the content as bytes
            filename = file.name
            
            # If document_key is not provided, use filename as document_key
            if not document_key:
                document_key = filename
            
            # Process the document using the appropriate method
            try:
                # Use the renamed internal method directly
                classification_result = self.document_classifier_agent.process_uploaded_document(
                    file_content,
                    filename,
                    self.document_classifier_agent.document_types
                )
                
                # Store session data for possible follow-up interaction
                self.document_classifier_agent._save_session_data(session_id, {
                    "resources": [document_key] if document_key else [],
                    "classification_result": classification_result,
                    "awaiting_confirmation": True,
                    "company_id": company_id,
                    "document_key": document_key,
                    "file": file_content,
                    "filename": filename,
                    "auth_token": auth_token
                })                
                
                # Construct a response similar to what process_query would return
                result = {
                    "message": "Document classified successfully",
                    "data": {
                        "response": f"Document classified as: **{classification_result.get('document_type', 'Unknown')}.**\n {classification_result.get('summary', '')} \nPlease confirm if the document type and details are correct. If not, kindly specify the correct document type (Purchase Bills, Expense Claims, Sales Invoices, Statements, Others, Loans, Finance Lease, Loans Payable, Rental (ROU) Lease).",
                        "company_id": company_id,
                        "resources": [document_key] if document_key else [],
                        "session_id": session_id,
                        "classification_result": classification_result
                    }
                }
                
            except Exception as classification_error:
                self.logger.error(f"Classification failed: {str(classification_error)}")
                # Fall back to a simple response if all else fails
                session_id = session_id or str(uuid.uuid4())
                classification_result = {
                    "document_type": "Unknown",
                    "metadata": {},
                    "summary": f"Classification failed: {str(classification_error)}"
                }
                
                # Store session data for error case
                self.document_classifier_agent._save_session_data(session_id, {
                    "resources": [document_key] if document_key else [],
                    "classification_result": classification_result,
                    "awaiting_confirmation": True,
                    "company_id": company_id,
                    "document_key": document_key,
                    "file": file_content,
                    "filename": filename,
                    "error": str(classification_error)
                })
                
                result = {
                    "message": "Classification processed with warnings",
                    "data": {
                        "response": f"Warning: Document classification had issues. Please verify results.",
                        "company_id": company_id,
                        "resources": [document_key] if document_key else [],
                        "session_id": session_id,
                        "summary": [classification_result.get('summary', '')]
                    }
                }
            
            if "data" not in result or not result["data"]:
                error_data = {"message": result.get("message", "Failed to classify document")}
                self.logger.error(f"Classification failed - correlation_id: {correlation_id}, error: {error_data}")
                return Response(ErrorResponseSerializer(error_data).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            success_data = {"message": "Document classified successfully", "data": result["data"]}
            self.logger.info(f"Document classification completed - correlation_id: {correlation_id}, session_id: {session_id}")
            return Response(SuccessResponseSerializer(success_data).data, status=status.HTTP_200_OK)
            
        except Exception as e:
            self.logger.error(f"Error classifying document: {str(e)} - correlation_id: {correlation_id}")
            error_data = {"message": f"Failed to classify document: {str(e)}"}
            return Response(ErrorResponseSerializer(error_data).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)