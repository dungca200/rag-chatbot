import logging
from langchain_community.tools import Tool
from typing import List, Dict
from langchain_openai import ChatOpenAI
from settings import settings
import json
import uuid
import traceback
from rag.agents.rag_agent import GLOBAL_SESSION_STORE
from django.db import connection
import re
import datetime
import decimal
from rag.schemas.database_schema import INVOICE_DB_TABLE_SCHEMA
from promptlayer import PromptLayer
from extraction.clients.promptlayer_client import PromptLayerClient
from rag.utils.response_templates import FALLBACK_TEMPLATES
import re


class InvoiceDetailsAgent:
    """Agent for querying and processing invoice details from the database."""    
    def __init__(self):
        self.DB_SCHEMA = INVOICE_DB_TABLE_SCHEMA
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL_V2)
        self.pl_client = PromptLayerClient()
        
        # Define prompt template IDs - these should be created in PromptLayer and set in settings
        self.INVOICE_QUERY_PROMPT_ID = settings.INVOICE_QUERY_PROMPT
        self.SQL_INVOICE_GENERATION_PROMPT_ID = settings.SQL_INVOICE_GENERATION_PROMPT
        self.SQL_INVOICE_CHECK_PROMPT_ID = settings.SQL_CHECK_PROMPT
        
        self.invoice_query_tool = Tool(
            name="invoice_query_tool",
            func=self._invoice_query_tool,
            description="Queries the 'invoice_details' table based on the provided query and optional company_id."
        )

    def _format_schema_for_prompt(self) -> str:
        """Format the database schema in a way that is easy for the LLM to understand"""
        schema_text = []
        
        for table_name, table_info in self.DB_SCHEMA.items():
            fields_str = []
            for field_name, field_info in table_info["fields"].items():
                field_type = field_info.get("type", "")
                field_desc = field_info.get("description", "")
                fields_str.append(f"  - {field_name}: {field_type} - {field_desc}")
            
            schema_text.append(f"Table: {table_name}")
            schema_text.append("Fields:")
            schema_text.extend(fields_str)
            
            if 'relationships' in table_info:
                schema_text.append("Relationships:")
                for rel in table_info['relationships']:
                    schema_text.append(f"  - {table_name}.{rel['from']} references {rel['to']}")
            
            schema_text.append("")  # Add blank line between tables
        
        return "\n".join(schema_text)

    def _clean_sql_query(self, sql_query: str) -> str:
        """
        Clean the SQL query by removing any markdown code block markers or other non-SQL content.
        
        Args:
            sql_query (str): The raw SQL query possibly containing markdown
            
        Returns:
            str: Cleaned SQL query
        """
        sql_query = sql_query.replace("```sql", "").replace("```", "")
        sql_query = sql_query.strip()
        
        # Remove semicolons at the end of the query
        if sql_query.endswith(';'):
            sql_query = sql_query[:-1]
        
        lines = sql_query.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith('--') or line.strip().startswith('#'):
                continue
            if '--' in line:
                line = line.split('--')[0]
            if '#' in line:
                line = line.split('#')[0]
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
        
    def _validate_sql_query(self, sql_query: str) -> bool:
        """
        Validate the SQL query for safety.
        
        Args:
            sql_query (str): SQL query to validate
            
        Returns:
            bool: True if the query is safe, False otherwise
        """
        raw_query = sql_query.lower().strip()
        normalized_query = " " + " ".join(raw_query.split()) + " "
                
        if not normalized_query.strip().startswith("select "):
            self.logger.error("SQL validation failed: Query must be a SELECT statement")
            return False
        
        dangerous_keywords = [
            " insert ", " update ", " delete ", " drop ", " alter ", " truncate ",
            " create ", " grant ", " revoke ", " union ", "--", "/*", "*/", "xp_",
            " exec ", " execute ", " sp_", " information_schema", " pg_"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in normalized_query:
                self.logger.error(f"SQL validation failed: Query contains dangerous keyword: {keyword}")
                return False
        
        if " from " not in normalized_query:
            self.logger.error(f"SQL validation failed: Query must contain FROM clause")
            return False
            
        allowed_tables = [table_name.lower() for table_name in self.DB_SCHEMA.keys()]
        
        allowed_table_patterns = []
        for table in allowed_tables:
            allowed_table_patterns.append(table)
            allowed_table_patterns.append(f'"{table}"')
            allowed_table_patterns.append(f"'{table}'")
        
        try:
            parts = normalized_query.split(" from ")
            if len(parts) < 2:
                self.logger.error("SQL validation failed: Could not parse FROM clause")
                return False
                
            from_clause = parts[1]
            
            end_clauses = [" where ", " group by ", " having ", " order by ", " limit ", ";"]
            end_positions = []
            
            for clause in end_clauses:
                pos = from_clause.find(clause)
                if pos >= 0:
                    end_positions.append(pos)
            
            if end_positions:
                table_part = from_clause[:min(end_positions)]
            else:
                table_part = from_clause
                
            table_expressions = []
            
            if " join " in table_part:
                join_parts = table_part.split(" join ")
                for part in join_parts:
                    if " on " in part:
                        table_expressions.append(part.split(" on ")[0].strip())
                    else:
                        table_expressions.append(part.strip())
            else:
                table_expressions = [t.strip() for t in table_part.split(",")]
            
            extracted_tables = []
            
            
            double_quoted_pattern = re.compile(r'"([^"]+)"(?:\."([^"]+)")?')
            unquoted_pattern = re.compile(r'([a-z0-9_]+)(?:\.([a-z0-9_]+))?')
            
            for expr in table_expressions:
                table_name = expr.strip()
                
                if " as " in table_name:
                    table_name = table_name.split(" as ")[0].strip()
                elif " " in table_name:
                    table_name = table_name.split()[0].strip()
                
                double_quoted_match = double_quoted_pattern.search(table_name)
                unquoted_match = unquoted_pattern.search(table_name)
                
                if double_quoted_match:
                    groups = double_quoted_match.groups()
                    if groups[1]: 
                        extracted_tables.append(f'"{groups[1]}"')
                    else: 
                        extracted_tables.append(f'"{groups[0]}"')
                elif unquoted_match:
                    groups = unquoted_match.groups()
                    if groups[1]:
                        extracted_tables.append(groups[1])
                    else:  
                        extracted_tables.append(groups[0])
                else:
                    extracted_tables.append(table_name)
                        
            valid_tables = False
            for table in extracted_tables:
                clean_table = table.replace('"', '').replace("'", "")
                
                if clean_table in allowed_tables:
                    valid_tables = True
                    break
                
                if table in allowed_table_patterns:
                    valid_tables = True
                    break
            
            if not valid_tables:
                table_list = ", ".join(extracted_tables)
                self.logger.error(f"SQL validation failed: Query contains unauthorized tables: {table_list}")
                return False
            
            return True
                
        except Exception as e:
            self.logger.error(f"SQL validation error: {str(e)}")
            return True

    def _execute_sql_query(self, sql_query: str, params: tuple = None) -> List[Dict]:
        """
        Execute a raw SQL query and return results as a list of dictionaries.
        
        Args:
            sql_query (str): SQL query to execute
            params (tuple): Parameters for the query
            
        Returns:
            List[Dict]: Query results as a list of dictionaries
        """
        try:
            # Validate the SQL query before execution
            if not self._validate_sql_query(sql_query):
                return [{"error": "Invalid SQL query: security validation failed"}]
                
            with connection.cursor() as cursor:
                if params:
                    cursor.execute(sql_query, params)
                else:
                    cursor.execute(sql_query)
                
                columns = [col[0] for col in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except Exception as e:
            self.logger.error(f"SQL query execution failed: {str(e)}")
            return [{"error": f"Query failed: {str(e)}"}]

    def _get_db_schema(self) -> str:
        """Get the database schema for SQL validation and generation"""
        schema = ""
        for table_name, table_info in self.DB_SCHEMA.items():
            schema += f"Table: {table_name}\n"
            fields = []
            for field_name, field_info in table_info["fields"].items():
                field_type = field_info.get("type", "")
                fields.append(f"{field_name} {field_type}")
            schema += f"Fields: {', '.join(fields)}\n"
            
            if 'relationships' in table_info:
                for rel in table_info['relationships']:
                    schema += f"Relationship: {table_name}.{rel['from']} references {rel['to']}\n"
            schema += "\n"
        return schema

    def _check_sql_query(self, query: str) -> Dict:
        """
        Check and correct an SQL query for syntax and logic errors.
        
        Args:
            query (str): The SQL query to check
            
        Returns:
            Dict: Result with corrected query and success status
        """
        schema_text = self._get_db_schema()
        
        input_variables = {
            "schema": schema_text,
            "query": query
        }

        try:
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                self.SQL_INVOICE_CHECK_PROMPT_ID,
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

            prompt = system_message if system_message else f"Check this SQL query: {query}"
            
            messages = [
                {"role": "system", "content": prompt}
            ]
            
            response = self.llm.invoke(
                input=messages
            )
            
            corrected_query = self._clean_sql_query(response.content.strip())
            if corrected_query != query:
                if "documents.id = " in corrected_query:
                    corrected_query = corrected_query.replace(
                        "documents.id = ", 
                        "documents.company_id = "
                    )
            return {"success": True, "query": corrected_query}
        except Exception as e:
            self.logger.error(f"Error checking SQL query: {str(e)}")
            return {"success": False, "error": str(e), "query": query}

    def _generate_query_from_schema(self, user_query: str, company_id: str = None, limit: int = 100) -> str:
        """
        Generate an SQL query based on the user's natural language query and the DB schema.
        
        Args:
            user_query (str): The user's natural language query
            company_id (str): Optional company ID to filter by
            limit (int): Maximum number of results to return
            
        Returns:
            str: Generated SQL query
        """
        schema_text = self._format_schema_for_prompt()
        
        input_variables = {
            "schema": schema_text,
            "query": user_query,
            "limit": limit,
            "company_id": company_id or "Not specified"
        }

        pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
        prompt_template = pl.templates.get(
            self.SQL_INVOICE_GENERATION_PROMPT_ID,
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

        prompt = system_message if system_message else f"Generate SQL for this query: {user_query}"

        messages = [
            {"role": "system", "content": prompt}
        ]
        
        response = self.llm.invoke(
            input=messages
        )
        
        sql_query = response.content.strip()
        sql_query = self._clean_sql_query(sql_query)
        
        check_result = self._check_sql_query(sql_query)
        if check_result["success"]:
            sql_query = check_result["query"]
        
        if company_id:
            if "documents.id = '{}'".format(company_id) in sql_query:
                sql_query = sql_query.replace(
                    "documents.id = '{}'".format(company_id),
                    "documents.company_id = '{}'".format(company_id)
                )
            elif "documents.id = {}".format(company_id) in sql_query:
                sql_query = sql_query.replace(
                    "documents.id = {}".format(company_id),
                    "documents.company_id = '{}'".format(company_id)
                )
            elif "WHERE d.id = " in sql_query:
                sql_query = sql_query.replace(
                    "WHERE d.id = {}".format(company_id),
                    "WHERE d.company_id = '{}'".format(company_id)
                )
                sql_query = sql_query.replace(
                    "WHERE d.id = '{}'".format(company_id),
                    "WHERE d.company_id = '{}'".format(company_id)
                )
        
        if "SELECT id" in sql_query:
            sql_query = sql_query.replace("SELECT id", "SELECT invoice_details.id")
        
        if sql_query.endswith(';'):
            sql_query = sql_query[:-1]
        
        if "LIMIT" not in sql_query.upper():
            sql_query += f" LIMIT {limit}"
                
        return sql_query

    def _format_query_results(self, results: List[Dict]) -> List[Dict]:
        """
        Format query results for better presentation, handling date and decimal values.
        
        Args:
            results (List[Dict]): Raw query results
            
        Returns:
            List[Dict]: Formatted results
        """
        formatted_results = []
        for row in results:
            formatted_row = {}
            for key, value in row.items():
                if isinstance(value, (datetime.date, datetime.datetime)):
                    formatted_row[key] = value.strftime('%Y-%m-%d')
                elif isinstance(value, decimal.Decimal):
                    formatted_row[key] = float(value)
                else:
                    formatted_row[key] = value
            formatted_results.append(formatted_row)
        
        return formatted_results

    def _invoice_query_tool(self, query: str, company_id: str = None) -> str:
        """
        Tool for looking up invoice details based on query parameters.
        
        Args:
            query (str): The user's query
            company_id (str): Optional company ID to filter results
            
        Returns:
            str: Response with invoice details
        """
        sql_query = self._generate_query_from_schema(query, company_id)
        results = self._execute_sql_query(sql_query)
        
        if len(results) == 1 and "error" in results[0]:
            error_message = results[0]["error"]
            self.logger.error(f"Error executing SQL query: {error_message}")
            return f"Error retrieving invoice details: {error_message}"
        
        formatted_results = self._format_query_results(results)
        
        if not formatted_results:
            return FALLBACK_TEMPLATES["INVOICE_NOT_FOUND"]
        
        input_variables = {
            "query": query,
            "company_id": company_id or "Not specified",
            "sql_query": sql_query,
            "results": json.dumps(formatted_results, indent=2)
        }
        
        try:
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                self.INVOICE_QUERY_PROMPT_ID,
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

            prompt = system_message if system_message else f"Format these results: {json.dumps(formatted_results)}"
            
            messages = [
                {"role": "system", "content": prompt}
            ]
            
            response = self.llm.invoke(
                input=messages
            )
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error generating response from query results: {str(e)}")
            
            if len(formatted_results) == 1:
                invoice = formatted_results[0]
                inv_num = invoice.get('invoice_number', 'Unknown')
                currency = invoice.get('currency', '')
                total = invoice.get('grand_total', 'Not available')
                date = invoice.get('invoice_date', 'Not available')
                return f"Found invoice {inv_num} from {date} with total amount {total} {currency}."
            else:
                count = len(formatted_results)
                return f"Found {count} invoices matching your query. The invoice numbers are: {', '.join([r.get('invoice_number', 'Unknown') for r in formatted_results if 'invoice_number' in r])}."

    def process_query(self, query: str, company_id: str = None, document_key: str = None, session_id: str = None) -> Dict:
        """
        Process a user query by generating SQL from the schema and executing it
        
        Args:
            query (str): The user's query about invoice details
            company_id (str, optional): Company ID to filter results
            document_key (str, optional): Document key for context
            session_id (str, optional): Session ID for storing state
            
        Returns:
            Dict: Response containing the answer and related metadata
        """
        session_id = session_id or str(uuid.uuid4())
        
        try:
            sql_query = self._generate_query_from_schema(query, company_id)
            results = self._execute_sql_query(sql_query)
            
            if len(results) == 1 and "error" in results[0]:
                error_message = results[0]["error"]
                self.logger.error(f"Error executing SQL query: {error_message}")
                return {
                    "message": "Query failed",
                    "data": {
                        "response": f"Error retrieving invoice details: {error_message}",
                        "company_id": company_id,
                        "resources": [],
                        "session_id": session_id
                    }
                }
            
            formatted_results = self._format_query_results(results)
            
            if not formatted_results:
                return {
                    "message": "No results found",
                    "data": {
                        "response": FALLBACK_TEMPLATES["INVOICE_NOT_FOUND"],
                        "company_id": company_id,
                        "resources": [],
                        "session_id": session_id,
                        "sql_query": sql_query
                    }
                }
            
            input_variables = {
                "query": query,
                "company_id": company_id or "Not specified",
                "sql_query": sql_query,
                "results": json.dumps(formatted_results, indent=2)
            }
            
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                self.INVOICE_QUERY_PROMPT_ID,
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

            prompt = system_message if system_message else f"Format these results: {json.dumps(formatted_results)}"
            
            messages = [
                {"role": "system", "content": prompt}
            ]
            
            response = self.llm.invoke(
                input=messages
            )
            
            answer = response.content
            
            resources = []
            for result in formatted_results:
                if "invoice_number" in result:
                    resources.append(result["invoice_number"])
            
            self._save_session_data(session_id, {
                "resources": resources,
                "last_response": answer,
                "sql_query": sql_query,
                "results": formatted_results
            })
            
            return {
                "message": "Query processed successfully",
                "data": {
                    "response": answer,
                    "company_id": company_id,
                    "resources": resources,
                    "session_id": session_id,
                    "sql_query": sql_query
                }
            }
                
        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(traceback.format_exc())
            return {
                "message": "Query failed",
                "data": {
                    "response": error_message,
                    "company_id": company_id,
                    "resources": [],
                    "session_id": session_id
                }
            }
    
    def _get_session_data(self, session_id: str) -> Dict:
        """Retrieve session data from the session store."""
        return GLOBAL_SESSION_STORE.get(session_id, {})

    def _save_session_data(self, session_id: str, data: Dict):
        """Save session data to the session store."""
        GLOBAL_SESSION_STORE[session_id] = data
        self.logger.info(f"Saved session data for {session_id}")
