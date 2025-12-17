import logging
from langchain_community.tools import tool, Tool
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from settings import settings
import json
import uuid
import requests
from rag.agents.rag_agent import GLOBAL_SESSION_STORE
from ai.utils import PDFToImageConverter
import io
from rag.agents.rag_agent import RagAgent
from openai import OpenAI
from rag.utils.response_templates import DOCUMENT_CLASSIFIER_TEMPLATES

class DocumentClassifierAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL_V2)
        self.pdf_converter = PDFToImageConverter()
        self.document_types = [
            'Purchase Bills',
            'Expense Claims',
            'Sales Invoices',
            'Statements',
            'Others',
            'Loans',
            'Finance Lease',
            'Loans Payable',
            'Rental (ROU) Lease'
        ]
        
        # Document type mapping for direct keyword matching
        self.direct_mapping = {
            "bill": "Purchase Bills",
            "purchase": "Purchase Bills",
            "invoice": "Sales Invoices", 
            "sales": "Sales Invoices",
            "expense": "Expense Claims",
            "claim": "Expense Claims",
            "statement": "Statements",
            "loan": "Loans",
            "rental": "Rental (ROU) Lease",
            "lease": "Finance Lease"
        }
        
        self.classify_document_content_tool = Tool(
            name="classify_document_content_tool",
            func=self._classify_document_content,
            description="Analyzes document content to classify its type from a predefined list."
        )
        
        self.process_uploaded_document_tool = Tool(
            name="process_uploaded_document_tool",
            func=self.process_uploaded_document,
            description="Processes an uploaded document file and classifies it."
        )
        
        self.submit_document_to_api_tool = Tool(
            name="submit_document_to_api_tool",
            func=self._submit_document_to_api,
            description="Submits the document to the external staging API for processing using form-data."
        )

    # Classification Prompt
    CLASSIFICATION_PROMPT = """
    You are a Document Classification Agent for Documa8e.
    Your role is to analyze document content and determine its type from the following options:

    <document_types>{document_types}</document_types>
    <document_content> {content} </document_content>
    <company_id> {company_id} </company_id>

    Instructions:
    - Analyze the document content carefully to identify its type.
    - Choose ONLY from the provided document types list.
    - For each document, extract key metadata appropriate to its type:
      - For Sales Invoices/Purchase Bills: invoice number, date, due date, total amount, supplier, customer
      - For Expense Claims: claim number, date, total amount, claimant
      - For Loans/Finance Lease/Loans Payable/Rental (ROU) Lease: parties involved, effective date, expiration date, key terms, amount
      - For Statements: account number, period, opening balance, closing balance
      - For Others: document title, date, key details (if any)
    
    - Return your analysis as a structured response with:
      1. Document type (must be one from the provided list)
      2. Document attributes (metadata fields appropriate to the document type)
      3. Brief summary of the document content (1-2 sentences)
    """

    def _match_document_type(self, input_type: str) -> str:
        """
        Uses LLM to match user input document type to the closest valid document type.
        Returns the matched document type or None if no good match is found.
        """
        if not input_type:
            return None
            
        if input_type in self.document_types:
            return input_type
            
        prompt = f"""
        I need to match the user's document type input to the closest valid document type.
        
        User input: "{input_type}"
        
        Valid document types:
        {json.dumps(self.document_types, indent=2)}
        
        Here are some examples of common variations:
        - "Invoice", "Bill", "Receipt" → "Purchase Bills" (for vendor/supplier bills)
        - "Sales", "Customer Invoice" → "Sales Invoices"
        - "Expense", "Claim", "Reimbursement" → "Expense Claims"
        - "Bank Statement", "Account Statement" → "Statements"
        - "Loan", "Loan Agreement", "Credit" → "Loans"
        - "Lease", "Rental Agreement" → "Rental (ROU) Lease"
        
        Find the best matching document type from the valid list. Consider:
        1. Common terminology in accounting/finance
        2. Semantic meaning and purpose of the document
        3. Industry-standard terminology
        4. Singular/plural forms, abbreviations, and common variations
        
        If there's a good match, return the exact valid document type string. 
        If there is no reasonable match, return null.
        
        Return your answer as a JSON object with a single key "matched_type" whose value is 
        either the matched document type string or null.
        """
        
        try:
            messages = [
                {"role": "system", "content": "You are a document classification assistant specializing in financial and business documents."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm.invoke(
                input=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.content)
            return result.get("matched_type")
            
        except Exception as e:
            self.logger.error(f"Error matching document type: {str(e)}")
            closest_match = min(self.document_types, 
                               key=lambda x: abs(len(x) - len(input_type)))
            return closest_match if len(input_type) > 3 else None

    def _classify_document_content(self, first_image: bytes, document_types: List[str]) -> Dict:
        """
        Analyzes document content to classify its type from a predefined list.
        """
        self.logger.info(f"Tool used: 'classify_document_content_tool'")
        document_types_str = "\n".join([f"- {doc_type}" for doc_type in document_types])
        try:
            base64_image = self.pdf_converter.encode_image(first_image)
            image_url = f"data:image/jpeg;base64,{base64_image}"

            system_prompt = """
            You are a document classification expert. Analyze the document content and classify it into one of the provided document types.
            Your response will be parsed as JSON, so maintain this exact format:
            {
                "document_type": "<exact match from provided types>",
                "metadata": {
                    <relevant fields based on document type>
                },
                "summary": "<brief description>"
            }
            """

            user_prompt = f"""
            Classify the financial document into one of the following types:
            <document_types>
            {document_types_str}
            </document_types>
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ]

            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL_V1,
                messages=messages,
                temperature=settings.EXTRACTION_DEFAULT_TEMPERATURE,
                response_format={ "type": "json_object" }  
            )
            try:
                raw_analysis = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                raw_analysis = {
                    "document_type": "Unknown",
                    "metadata": {},
                    "summary": "Failed to parse classification response"
                }
            classification_result = {
                "document_type": raw_analysis.get("document_type", "Unknown"),
                "metadata": raw_analysis.get("metadata", {}),
                "summary": raw_analysis.get("summary", "No summary available")
            }
            if classification_result["document_type"] not in document_types:
                matched_type = self._match_document_type(classification_result["document_type"])
                if matched_type:
                    classification_result["document_type"] = matched_type
                else:
                    closest_match = min(document_types, key=lambda x: abs(len(x) - len(classification_result["document_type"])))
                    classification_result["document_type"] = closest_match
            return classification_result
            
        except Exception as e:
            self.logger.error(f"Document classification failed: {str(e)}")
            return {
                "document_type": "Unknown",
                "metadata": {},
                "summary": f"Classification failed: {str(e)}"
            }

    def process_uploaded_document(self, file: bytes, filename: str, document_types: List[str]) -> Dict:
        """
        Processes an uploaded document file and classifies it.
        """
        self.logger.info(f"Tool used: 'process_uploaded_document_tool' for file: {filename}")
        first_image = None
        try:
            if filename.lower().endswith('.pdf'):
                first_image = self.pdf_converter.pdf_to_first_image(file)
            
            elif filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image = io.BytesIO(file)
                if first_image is None:
                    first_image = image
            else:
                return {
                    "document_type": "Unknown",
                    "metadata": {},
                    "summary": f"Unsupported file type: {filename}. Please upload a PDF or text file."
                }
            
            return self._classify_document_content(first_image, document_types)
            
        except Exception as e:
            self.logger.error(f"Document processing failed: {str(e)}")
            return {
                "document_type": "Unknown",
                "metadata": {},
                "summary": f"Processing failed: {str(e)}"
            }

    def _submit_document_to_api(self, document_key: str, document_type: str, company_id: str, auth_token: str, file: bytes = None, filename: str = None) -> Dict:
        """
        Submits the document to the external staging API for processing using form-data.
        The file and filename are provided by the frontend via the attach button.
        """
        self.logger.info(f"Tool used: 'submit_document_to_api_tool' for document: {document_key}")

        try:
            api_url = settings.DOCUMA8E_URI + "/api/upload_document"

            if not auth_token:
                self.logger.error("Bearer token not found in environment variables (BEARER_AUTH).")
                return {
                    "success": False,
                    "message": "Bearer token not found. Please set BEARER_AUTH in your environment variables."
                }

            # Strip any whitespace, including newlines, from the auth token
            auth_token = auth_token.strip() if auth_token else ""
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "multipart/form-data",
            }

            if not file or not filename:
                self.logger.error("File content or filename not provided for upload.")
                return {
                    "success": False,
                    "message": "File content or filename not provided. Please ensure a file is attached."
                }

            # Enhanced document type matching
            if document_type not in self.document_types:
                # Try direct keyword matching first
                doc_type_lower = document_type.lower()
                matched = False
                
                for key, value in self.direct_mapping.items():
                    if key in doc_type_lower:
                        document_type = value
                        matched = True
                        break
                        
                # If direct matching fails, use the LLM matcher
                if not matched:
                    matched_type = self._match_document_type(document_type)
                    if matched_type:
                        document_type = matched_type
                    else:
                        # Last resort fallback
                        document_type = "Purchase Bills" if "purchase" in document_type.lower() or "bill" in document_type.lower() else "Others"
                
                self.logger.info(f"Adjusted document_type to: {document_type}")

            form_data = {
                "company_id": int(company_id),
                "document_type": document_type,
                "use_automa8e_company_id": 1,
            }
            self.logger.info(f"Form data: {form_data}")

            files = [
                ("files[]", (filename, file, "application/pdf"))
            ]
            
            # Remove Content-Type header to let requests set it correctly with boundary
            headers.pop("Content-Type", None)
            
            response = requests.post(
                api_url,
                headers=headers,
                data=form_data,
                files=files,
            )

            self.logger.info(f"Raw response status: {response.status_code}")

            if response.status_code == 200:
                try:
                    response_json = response.json()
                    # Extract the actual document key from the API response if available
                    api_document_key = None
                    if response_json and isinstance(response_json, dict):
                        # Extract document key from response - adjust this path based on actual API response structure
                        if 'data' in response_json and 'document_key' in response_json['data']:
                            api_document_key = response_json['data']['document_key']
                        elif 'document_key' in response_json:
                            api_document_key = response_json['document_key']
                    
                    return {
                        "success": True,
                        "message": "Document successfully submitted to API",
                        "response": response_json,
                        "document_key": api_document_key
                    }
                except ValueError:
                    return {
                        "success": False,
                        "message": "Failed to parse API response as JSON",
                        "error_detail": response.text[:200]
                    }
            else:
                content_type = response.headers.get("Content-Type", "")
                self.logger.info(f"Response Content-Type: {content_type}")

                try:
                    error_response = response.json()
                    error_message = error_response.get("message", "Unknown error occurred.")
                    error_data = error_response.get("data", "")
                except ValueError:
                    error_message = "Failed to parse API response (possibly compressed or corrupted)."
                    error_data = response.text[:100]

                error_detail = (
                    f"Status Code: {response.status_code}\n"
                    f"Response: {response.text[:100]}\n"
                    f"Response Headers: {dict(response.headers)}\n"
                    f"Request URL: {api_url}\n"
                    f"Request Headers: {dict(response.request.headers)}\n"
                    f"Form Data: {form_data}"
                )
                self.logger.error(f"API request failed:\n{error_detail}")

                if "user is not registered in this company" in error_message.lower():
                    return {
                        "success": False,
                        "message": f"Failed to submit document: The user is not registered with company ID {company_id}. Please verify the company ID or user permissions.",
                        "error_detail": error_detail
                    }

                if response.status_code == 404:
                    return {
                        "success": False,
                        "message": f"API endpoint not found (404). Please verify the endpoint URL: {api_url} and ensure the server is operational.",
                        "error_detail": error_detail
                    }

                return {
                    "success": False,
                    "message": f"API request failed with status {response.status_code}: {error_message} {error_data}",
                    "error_detail": error_detail
                }

        except Exception as e:
            self.logger.error(f"API submission failed: {str(e)}")
            return {
                "success": False,
                "message": f"API submission failed: {str(e)}"
            }
    
    def _get_session_data(self, session_id: str) -> Dict:
        """Retrieve session data from the global store."""
        return GLOBAL_SESSION_STORE.get(session_id, {})

    def _save_session_data(self, session_id: str, data: Dict):
        """Save session data to the global store."""
        GLOBAL_SESSION_STORE[session_id] = data
        self.logger.info(f"Saved session data for {session_id}")

    # New method to handle follow-up questions after document upload
    def _handle_document_follow_up(self, query: str, session_id: str, company_id: str):
        """
        Handles follow-up questions about a document after it has been uploaded and classified.
        This method creates a handoff to the RAG agent to answer questions about the document.
        """
        session_data = self._get_session_data(session_id)
        
        # Check if we have a valid document key from the API response
        document_key = session_data.get("document_key")
        
        # Fall back to original document key if API didn't return one
        if not document_key:
            document_key = session_data.get("resources", [None])[0]
        
        if not document_key:
            return {
                "message": "No document available",
                "data": {
                    "response": "I can't answer questions about this document because no document key was found. Please try uploading the document again.",
                    "company_id": company_id,
                    "resources": [],
                    "session_id": session_id
                }
            }
        
        # Initialize RagAgent and process the follow-up query
        rag_agent = RagAgent()
        result = rag_agent.process_query(
            query=query,
            company_id=company_id,
            document_key=document_key,
            session_id=session_id
        )
        
        # Update session data with the latest response
        session_data["last_response"] = result.get("data", {}).get("response", "")
        session_data["last_query"] = query
        self._save_session_data(session_id, session_data)
        
        return result

    def process_query(self, query: str, company_id: str = None, document_key: str = None, session_id: str = None, file: bytes = None, filename: str = None) -> Dict:
        """Main method to process the query and generate a classification response."""
        session_id = session_id or str(uuid.uuid4())
        
        session_data = self._get_session_data(session_id)
        
        # Check if we have a document uploaded and this is a follow-up question (not awaiting confirmation)
        if (not session_data.get("awaiting_confirmation", False) and 
            session_data.get("document_uploaded", False) and 
            not file):  # No new file means it's likely a follow-up question
            
            # Handle follow-up question using the RAG agent
            return self._handle_document_follow_up(query, session_id, company_id)
        
        is_confirmation = session_data.get("awaiting_confirmation", False) and query.lower().strip()

        if is_confirmation:
            confirmation_prompt = f"""
            User was asked: "Is this the correct document type and details?"
            Previous classification: {json.dumps(session_data.get('classification_result', {}))}
            User's response: "{query}"
            
            Analyze the user's response carefully to determine:
            1. If they confirmed the classification as correct (said yes, confirmed, etc.)
            2. If they suggested a different document type (e.g., "no, it's a Purchase Bill")
            3. If they mentioned a document category that needs to be mapped to an official type
            
            Valid document types are: {", ".join(self.document_types)}
            
            Consider that users may use shorthand or variations:
            - "Bills", "Bill", "Purchase" likely map to "Purchase Bills"
            - "Invoice", "Sales", "Customer Invoice" likely map to "Sales Invoices"
            - "Expense", "Claim" likely map to "Expense Claims"
            - etc.
            
            Return a JSON object with:
            - "confirmed": true/false (true only if they clearly confirmed)
            - "selected_type": null if confirmed=true, otherwise the new document type they suggested or implied
            """
            
            messages = [
                {"role": "system", "content": "You are an AI that interprets user responses about document classification with expertise in financial documents."},
                {"role": "user", "content": confirmation_prompt}
            ]
            
            response = self.llm.invoke(
                input=messages,
                temperature=0.3,
                response_format={ "type": "json_object" }  
            )
            
            try:
                confirmation_result = json.loads(response.content)
            except:
                confirmation_result = {"confirmed": False, "selected_type": None}

            classification_result = session_data.get("classification_result", {})
            doc_type = classification_result.get("document_type", "Unknown")
            document_key = session_data.get("document_key") or document_key
            file = session_data.get("file")
            filename = session_data.get("filename")
            auth_token = session_data.get("auth_token")
            # company_id = session_data.get("company_id") 
            
            if not document_key:
                response_text = DOCUMENT_CLASSIFIER_TEMPLATES["NO_DOCUMENT_KEY"].format(session_id=session_id)
                session_data["awaiting_confirmation"] = True
            elif confirmation_result["confirmed"]:
                api_result = self._submit_document_to_api(document_key, doc_type, company_id, auth_token, file, filename)
                
                if api_result.get("success"):
                    # Store the API-returned document key in session_data if available
                    api_document_key = api_result.get("document_key")
                    if api_document_key:
                        session_data["document_key"] = api_document_key
                        # Update resources with the correct document key for RAG queries
                        session_data["resources"] = [api_document_key]
                    
                    # Set a flag to indicate that RAG queries can now be processed for this document
                    session_data["document_uploaded"] = True
                    response_text = DOCUMENT_CLASSIFIER_TEMPLATES["CLASSIFICATION_CONFIRMED_SUCCESS_WITH_PROMPT"].format(doc_type=doc_type)
                else:
                    response_text = DOCUMENT_CLASSIFIER_TEMPLATES["CLASSIFICATION_CONFIRMED_FAILURE"].format(
                        doc_type=doc_type,
                        error_message=api_result.get('message'),
                        session_id=session_id
                    )
                session_data["awaiting_confirmation"] = False
            elif confirmation_result["selected_type"]:
                user_selected_type = confirmation_result["selected_type"]
                # Use LLM to match the user's input to a valid document type
                matched_type = self._match_document_type(user_selected_type)
                
                if matched_type:
                    doc_type = matched_type
                    api_result = self._submit_document_to_api(document_key, doc_type, company_id, auth_token, file, filename)
                    if api_result.get("success"):
                        # Store the API-returned document key in session_data if available
                        api_document_key = api_result.get("document_key")
                        if api_document_key:
                            session_data["document_key"] = api_document_key
                            # Update resources with the correct document key for RAG queries
                            session_data["resources"] = [api_document_key]
                        
                        # Set a flag to indicate that RAG queries can now be processed for this document
                        session_data["document_uploaded"] = True
                        response_text = DOCUMENT_CLASSIFIER_TEMPLATES["CLASSIFICATION_UPDATED_SUCCESS_WITH_PROMPT"].format(doc_type=doc_type)
                    else:
                        response_text = DOCUMENT_CLASSIFIER_TEMPLATES["CLASSIFICATION_UPDATED_FAILURE"].format(
                            doc_type=doc_type,
                            error_message=api_result.get('message'),
                            session_id=session_id
                        )
                    session_data["awaiting_confirmation"] = False
                else:
                    # Try to determine what they meant - make a better guess
                    user_input_lower = user_selected_type.lower()
                    
                    # Check direct mappings
                    for key, value in self.direct_mapping.items():
                        if key in user_input_lower:
                            doc_type = value
                            api_result = self._submit_document_to_api(document_key, doc_type, company_id, auth_token, file, filename)
                            if api_result.get("success"):
                                # Store the API-returned document key in session_data if available
                                api_document_key = api_result.get("document_key")
                                if api_document_key:
                                    session_data["document_key"] = api_document_key
                                    # Update resources with the correct document key for RAG queries
                                    session_data["resources"] = [api_document_key]
                                
                                # Set a flag to indicate that RAG queries can now be processed for this document
                                session_data["document_uploaded"] = True
                                response_text = DOCUMENT_CLASSIFIER_TEMPLATES["CLASSIFICATION_UPDATED_SUCCESS_WITH_PROMPT"].format(doc_type=doc_type)
                            else:
                                response_text = DOCUMENT_CLASSIFIER_TEMPLATES["CLASSIFICATION_UPDATED_FAILURE"].format(
                                    doc_type=doc_type,
                                    error_message=api_result.get('message'),
                                    session_id=session_id
                                )
                            session_data["awaiting_confirmation"] = False
                            break
                    else:  # No match found in the direct mapping
                        response_text = DOCUMENT_CLASSIFIER_TEMPLATES["INVALID_DOCUMENT_TYPE"].format(
                            doc_type=user_selected_type,
                            document_types=', '.join(self.document_types),
                            session_id=session_id
                        )
                        session_data["awaiting_confirmation"] = True
            else:
                response_text = DOCUMENT_CLASSIFIER_TEMPLATES["CLASSIFICATION_NOT_CONFIRMED"].format(
                    document_types=', '.join(self.document_types),
                    session_id=session_id
                )
                session_data["awaiting_confirmation"] = True
                
            self._save_session_data(session_id, session_data)
            
            return {
                "message": "Confirmation processed",
                "data": {
                    "response": response_text,
                    "company_id": company_id,
                    "resources": [document_key] if document_key else [],
                    "session_id": session_id,
                    "classification_result": classification_result
                }
            }

        classification_result = None
        if file and filename:
            classification_result = self.process_uploaded_document(file, filename, self.document_types)
            if classification_result.get("document_type") != "Unknown":
                document_key = filename
        elif document_key:
            rag_agent = RagAgent()
            docs = rag_agent.get_document_by_key_tool.invoke({"document_key": document_key})
            if docs and "error" not in docs[0] and "status" not in docs[0]:
                content = "\n\n".join([doc.get("content", "") for doc in docs])
                classification_result = self._classify_document_content(content, self.document_types)
            else:
                classification_result = {
                    "document_type": "Unknown",
                    "metadata": {},
                    "summary": f"Document not found: {document_key}"
                }
        else:
            classification_result = {
                "document_type": "Unknown",
                "metadata": {},
                "summary": "No document provided for classification."
            }

        doc_type = classification_result.get("document_type", "Unknown")
        
        response_text = DOCUMENT_CLASSIFIER_TEMPLATES["CLASSIFICATION_RESULTS"].format(
            doc_type=doc_type,
            session_id=session_id,
            document_types=', '.join(self.document_types)
        )

        resources = [document_key] if document_key else []
        session_data = {
            "resources": resources,
            "last_response": response_text,
            "classification_result": classification_result,
            "awaiting_confirmation": True,
            "company_id": company_id,
            "document_key": document_key,
            "file": file,
            "filename": filename
        }
        self._save_session_data(session_id, session_data)

        return {
            "message": "Classification processed successfully",
            "data": {
                "response": response_text,
                "company_id": company_id,
                "resources": resources,
                "session_id": session_id,
                "classification_result": classification_result
            }
        }