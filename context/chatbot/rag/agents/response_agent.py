import logging
from langchain_community.tools import Tool
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from settings import settings
import json
from promptlayer import PromptLayer
from extraction.clients.promptlayer_client import PromptLayerClient

class ResponseAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL_V2)
        self.pl_client = PromptLayerClient()
        
        self.compile_multiple_query_tool = Tool(
            name="compile_multiple_query_tool",
            func=self._compile_multiple_query_tool,
            description="Tool to compile responses from multiple queries."
        )

    def _compile_multiple_query_tool(self, query: str, responses: List[Dict], logs: Optional[List[Dict]] = None) -> Dict:
        """Tool to compile responses from multiple queries."""
        self.logger.info(f"Tool used: 'compile_query_tool'")
        try:
            # Safely extract response texts with better error handling
            response_texts = []
            for i, r in enumerate(responses):
                try:
                    if not r or not isinstance(r, dict):
                        self.logger.warning(f"Response at index {i} is not a dictionary: {r}")
                        continue
                        
                    if "data" not in r:
                        self.logger.warning(f"Response at index {i} does not have a 'data' key: {r}")
                        continue
                        
                    data = r["data"]
                    if not isinstance(data, dict):
                        self.logger.warning(f"Data at index {i} is not a dictionary: {data}")
                        continue
                        
                    if "response" not in data:
                        self.logger.warning(f"Data at index {i} does not have a 'response' key: {data}")
                        continue
                        
                    response_text = data["response"]
                    if response_text:
                        response_texts.append(str(response_text))
                except Exception as e:
                    self.logger.error(f"Error extracting response at index {i}: {str(e)}")
                    continue
            
            # If no valid responses were found, return a helpful message
            if not response_texts:
                self.logger.warning("No valid responses found to compile")
                return {
                    "response": f"I'm sorry, but I couldn't find any valid responses for your query: '{query}'",
                    "summary": ["No valid responses found"],
                    "rag_resources": [],
                    "document_table_resources": [],
                    "invoice_details_resources": [],
                    "loan_details_resources": [],
                    "bank_statement_details_resources": [],
                    "web_search_resources": []
                }
            
            responses_str = "\n\n".join(response_texts)
            logs_str = json.dumps(logs) if logs is not None else "None"
            
            # Input variables for the prompt
            input_variables = {
                "query": query,
                "responses": responses_str,
                "logs": logs_str
            }

            # Get the prompt template from PromptLayer using the template ID stored in settings
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                settings.RESPONSE_AGENT_PROMPT,
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
            prompt = system_message if system_message else f"Compile these responses for query: {query}"
            
            messages = [
                {"role": "system", "content": prompt}
            ]
            
            response = self.llm.invoke(
                input=messages,
            ).content
            
            if "[SUMMARY]" in response:
                response_parts = response.split("[SUMMARY]")
                compiled_response = response_parts[0].strip()
                summary = response_parts[1].strip()
            else:
                compiled_response = response.strip()
                summary = f"Processed {len(responses)} response(s) for '{query}'" if len(responses) > 1 else responses_str.strip()

            rag_resources = []
            document_table_resources = []
            invoice_details_resources = []
            loan_details_resources = []
            bank_statement_details_resources = []
            web_search_resources = []

            for resp in responses:
                try:
                    agent_type = resp.get("agent_type", "unknown")
                    self.logger.info(f"Processing response from agent type: {agent_type}")
                    
                    if "data" in resp and isinstance(resp["data"], dict):
                        # Check for specific resources based on agent type
                        if agent_type == "invoice_details_agent" and "invoice_details_resources" in resp["data"]:
                            invoice_resources = resp["data"]["invoice_details_resources"]
                            self.logger.info(f"Found {len(invoice_resources)} invoice_details_resources")
                            if invoice_resources:
                                invoice_details_resources.extend(invoice_resources)
                        elif agent_type == "loan_details_agent" and "loan_details_resources" in resp["data"]:
                            loan_resources = resp["data"]["loan_details_resources"]
                            self.logger.info(f"Found {len(loan_resources)} loan_details_resources")
                            if loan_resources:
                                loan_details_resources.extend(loan_resources)
                        elif agent_type == "bank_statement_details_agent" and "bank_statement_details_resources" in resp["data"]:
                            bank_statement_resources = resp["data"]["bank_statement_details_resources"]
                            self.logger.info(f"Found {len(bank_statement_resources)} bank_statement_details_resources")
                            if bank_statement_resources:
                                bank_statement_details_resources.extend(bank_statement_resources)
                        # Fall back to generic resources for other agents
                        elif "resources" in resp["data"]:
                            resources = resp["data"]["resources"]
                            self.logger.info(f"Found {len(resources)} resources")
                            if resources:
                                if agent_type == "rag_agent":
                                    # For rag_agent, collect resources with similarity information if available
                                    if "similarity_info" in resp["data"]:
                                        similarity_info = resp["data"]["similarity_info"]
                                        for resource in resources:
                                            resource_key = resource
                                            if isinstance(resource, dict):
                                                resource_key = resource.get("key", "")
                                            
                                            if resource_key in similarity_info:
                                                rag_resources.append({"key": resource_key, "similarity": similarity_info[resource_key]})
                                            else:
                                                rag_resources.append({"key": resource_key, "similarity": 0.0})
                                    else:
                                        # If no similarity info available, just add the resources
                                        rag_resources.extend(resources)
                                elif agent_type == "document_query_agent":
                                    document_table_resources.extend(resources)
                                elif agent_type == "invoice_details_agent":
                                    invoice_details_resources.extend(resources)
                                elif agent_type == "loan_details_agent":
                                    loan_details_resources.extend(resources)
                                elif agent_type == "bank_statement_details_agent":
                                    bank_statement_details_resources.extend(resources)
                                elif agent_type == "web_search_agent":
                                    web_search_resources.extend(resources)
                except Exception as e:
                    self.logger.error(f"Error extracting resources from response: {str(e)}")
                    self.logger.error(f"Response data: {resp}")
                    continue

            # For rag_resources, filter to keep only the most relevant resource
            if len(rag_resources) > 1:
                self.logger.info(f"Filtering {len(rag_resources)} rag_resources to keep only the most relevant one")
                
                # First, try to find resources with similarity information
                resources_with_similarity = [r for r in rag_resources if isinstance(r, dict) and "similarity" in r]
                
                if resources_with_similarity:
                    # Sort by similarity (highest first)
                    most_relevant_resource = sorted(resources_with_similarity, key=lambda x: x.get("similarity", 0.0), reverse=True)[0]
                    rag_resources = [most_relevant_resource["key"] if isinstance(most_relevant_resource, dict) else most_relevant_resource]
                else:
                    # If no similarity info available, just take the first one
                    rag_resources = [rag_resources[0]]
                
                self.logger.info(f"Reduced to single most relevant resource: {rag_resources}")

            # Deduplicate resources safely (for non-rag resources)
            def deduplicate_resources(resources_list):
                unique_resources = []
                resource_ids = set()
                for resource in resources_list:
                    if isinstance(resource, str):
                        if resource not in resource_ids:
                            resource_ids.add(resource)
                            unique_resources.append(resource)
                    else:
                        resource_id = str(resource.get('id', '')) or str(resource.get('title', '')) or str(resource.get('key', ''))
                        if resource_id and resource_id not in resource_ids:
                            resource_ids.add(resource_id)
                            unique_resources.append(resource)
                return unique_resources

            document_table_resources = deduplicate_resources(document_table_resources)
            invoice_details_resources = deduplicate_resources(invoice_details_resources)
            loan_details_resources = deduplicate_resources(loan_details_resources)
            bank_statement_details_resources = deduplicate_resources(bank_statement_details_resources)
            web_search_resources = deduplicate_resources(web_search_resources)

            # Log final resource counts
            self.logger.info(f"Final resource counts - rag: {len(rag_resources)}, document: {len(document_table_resources)}, invoice: {len(invoice_details_resources)}, loan: {len(loan_details_resources)}, bank_statement: {len(bank_statement_details_resources)}, web: {len(web_search_resources)}")

            # Check if the compiled response is a fallback message
            fallback_phrases = [
                "I appreciate your question. While I don't have the complete information at the moment, I'd be happy to help if you could provide more specific details about what you're looking for in the document.",
                "Thank you for your inquiry. I need a bit more context to give you an accurate answer. Could you please clarify which specific aspect of the document you're interested in?",
                "I'd like to help you with that. To provide the most relevant information, could you narrow down your question or specify which section of the document you're referring to?",
                "While I don't have all the details for a complete answer right now, I'd be glad to assist if you could provide additional context or ask a more specific question about the document.",
                "Based on the available information, I can't give you a comprehensive answer yet. Would you like to explore a particular aspect of the document in more detail?",
                "To better assist you, I may need more specific information. Could you please elaborate on your question or indicate which part of the document you're most interested in?"
            ]
            is_fallback_response = any(phrase in compiled_response for phrase in fallback_phrases)
            
            # Clear all resources if it's a fallback response
            if is_fallback_response:
                self.logger.info("Fallback response detected. Clearing all resources.")
                rag_resources = []
                document_table_resources = []
                invoice_details_resources = []
                loan_details_resources = []
                bank_statement_details_resources = []
                web_search_resources = []

            return {
                "response": compiled_response,
                "summary": [summary],
                "rag_resources": rag_resources,
                "document_table_resources": document_table_resources,
                "invoice_details_resources": invoice_details_resources,
                "loan_details_resources": loan_details_resources,
                "bank_statement_details_resources": bank_statement_details_resources,
                "web_search_resources": web_search_resources
            }
        except Exception as e:
            self.logger.error(f"Response compilation failed: {str(e)}")
            return {
                "response": f"I encountered an error while processing your query. Please try again or rephrase your question. Error: {str(e)}",
                "summary": [],
                "rag_resources": [],
                "document_table_resources": [],
                "invoice_details_resources": [],
                "loan_details_resources": [],
                "bank_statement_details_resources": [],
                "web_search_resources": []
            }

    def process_query(self, query: str, responses: List[Dict], company_id: str = None, session_id: str = None) -> Dict:
        all_logs = []
        
        # Treat session_id as thread_id for compatibility
        thread_id = session_id
        
        for resp in responses:
            if "logs" in resp["data"] and resp["data"]["logs"]:
                all_logs.extend(resp["data"]["logs"])
        
        if len(responses) > 1 and not all_logs:
            import re
            sub_queries = [q.strip() for q in re.split(r'[.!?]+', query) if q.strip()]
            if len(sub_queries) >= len(responses):
                all_logs = [{"arrangement": i+1, "query": sub_query, "company_id": company_id} for i, sub_query in enumerate(sub_queries[:len(responses)])]
            else:
                all_logs = [{"arrangement": i+1, "query": query, "company_id": company_id} for i in range(len(responses))]

        compiled = self._compile_multiple_query_tool(query, responses, all_logs)
        
        return {
            "message": "Query processed successfully",
            "data": {
                "response": compiled["response"],
                "company_id": company_id,
                "rag_resources": compiled["rag_resources"],
                "document_table_resources": compiled["document_table_resources"],
                "invoice_details_resources": compiled["invoice_details_resources"],
                "loan_details_resources": compiled["loan_details_resources"],
                "bank_statement_details_resources": compiled["bank_statement_details_resources"],
                "web_search_resources": compiled["web_search_resources"],
                "thread_id": thread_id,  # Return thread_id instead of session_id 
                "summary": compiled["summary"],
                "logs": all_logs
            }
        }