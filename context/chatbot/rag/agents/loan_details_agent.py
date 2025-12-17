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
from rag.schemas.database_schema import LOAN_DB_TABLE_SCHEMA
from promptlayer import PromptLayer
from extraction.clients.promptlayer_client import PromptLayerClient
from rag.utils.response_templates import FALLBACK_TEMPLATES

class LoanDetailsAgent:
    """Agent for querying and processing loan details from the database."""
    def __init__(self):
        self.DB_SCHEMA = LOAN_DB_TABLE_SCHEMA
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL_V2)
        self.pl_client = PromptLayerClient()
        
        self.LOAN_QUERY_PROMPT_ID = settings.LOAN_QUERY_PROMPT
        self.SQL_LOAN_GENERATION_PROMPT_ID = settings.SQL_LOAN_GENERATION_PROMPT
        self.SQL_CHECK_PROMPT_ID = settings.SQL_CHECK_PROMPT
        
        self.loan_query_tool = Tool(
            name="loan_query_tool",
            func=self._loan_query_tool,
            description="Queries the 'loan_details' table based on the provided query and optional company_id."
        )

    def _format_schema_for_prompt(self) -> str:
        schema_text = []
        for table_name, table_info in self.DB_SCHEMA.items():
            schema_text.append(f"- Table: {table_info['table']}")
            schema_text.append(f"  Fields: {', '.join(table_info['fields'])}")
            if 'relationships' in table_info and table_info['relationships']:
                for rel in table_info['relationships']:
                    schema_text.append(f"  Relationship: {table_info['table']}.{rel['from']} references {rel['to']}")
        return "\n".join(schema_text)

    def _get_db_schema(self) -> str:
        schema = LOAN_DB_TABLE_SCHEMA
        return schema
        
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
        
    def _check_sql_query(self, query: str) -> Dict:
        schema_text = self._get_db_schema()
        
        input_variables = {
            "schema": schema_text,
            "query": query
        }

        try:
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                self.SQL_CHECK_PROMPT_ID,
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
            return {"success": False, "error": str(e), "query": query}
            
    def _generate_sql_query(self, query: str, account_numbers: List[str] = None, currency: str = None, limit: int = 100, company_id: str = None) -> str:
        if account_numbers and any(term in query.lower() for term in ['show', 'get', 'find', 'details', 'check']):
            where_clauses = []
            if len(account_numbers) == 1:
                where_clauses.append(f"(loan_details.account_number = '{account_numbers[0]}' OR loan_details.account_number LIKE '%{account_numbers[0]}%')")
            else:
                placeholders = ", ".join([f"'{num}'" for num in account_numbers])
                where_clauses.append(f"loan_details.account_number IN ({placeholders})")
            if currency:
                where_clauses.append(f"loan_details.currency = '{currency}'")
            where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            base_query = "SELECT loan_details.* FROM loan_details"
            if company_id:
                base_query = """
                SELECT loan_details.* 
                FROM loan_details 
                JOIN documents ON loan_details.document_id = documents.id
                """
                where_clause += f" AND documents.company_id = '{company_id}'" if where_clause else f" WHERE documents.company_id = '{company_id}'"
            sql_query = f"{base_query}{where_clause} LIMIT {limit}"
            return sql_query
        
        schema_info = self._get_db_schema()
        
        input_variables = {
            "schema": schema_info,
            "query": query,
            "limit": limit,
            "company_id": company_id or "Not specified"
        }
        
        if account_numbers:
            input_variables["account_numbers"] = account_numbers
        if currency:
            input_variables["currency"] = currency
            
        try:
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                self.SQL_LOAN_GENERATION_PROMPT_ID,
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

            prompt = system_message if system_message else f"Generate SQL for this query: {query}"
            
            messages = [
                {"role": "system", "content": prompt}
            ]
            
            response = self.llm.invoke(
                input=messages
            )
            
            sql_query = self._clean_sql_query(response.content.strip())
            check_result = self._check_sql_query(sql_query)
            if check_result["success"]:
                sql_query = check_result["query"]
            
            if sql_query.endswith(';'):
                sql_query = sql_query[:-1]
            
            if "LIMIT" not in sql_query.upper():
                sql_query += f" LIMIT {limit}"
                
            return sql_query
            
        except Exception as e:
            self.logger.error(f"Error generating SQL query: {str(e)}")
            return f"SELECT * FROM loan_details LIMIT {limit}"

    def _validate_sql_query(self, sql_query: str) -> bool:
        """
        Validate the SQL query for safety.
        
        Args:
            sql_query (str): SQL query to validate
            
        Returns:
            bool: True if the query is safe, False otherwise
        """
        normalized_query = " " + " ".join(sql_query.lower().strip().split()) + " "
                
        if not re.search(r'^\s*select\s+', normalized_query.lower().strip()):
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
            self.logger.error("SQL validation failed: Query must contain FROM clause")
            return False
        
        allowed_tables = [table_info["table"].lower() for table_info in self.DB_SCHEMA.values()]
        allowed_tables.append("documents")
        
        allowed_table_patterns = []
        for table in allowed_tables:
            allowed_table_patterns.extend([table, f'"{table}"', f"'{table}'"])
        
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
                    extracted_tables.append(f'"{groups[1]}"' if groups[1] else f'"{groups[0]}"')
                elif unquoted_match:
                    groups = unquoted_match.groups()
                    extracted_tables.append(groups[1] if groups[1] else groups[0])
                else:
                    extracted_tables.append(table_name)
                        
            valid_tables = False
            for table in extracted_tables:
                clean_table = table.replace('"', '').replace("'", "").lower()
                
                if clean_table in allowed_tables:
                    valid_tables = True
                    break
                
                if table.lower() in [p.lower() for p in allowed_table_patterns]:
                    valid_tables = True
                    break
            
            if not valid_tables:
                table_list = ", ".join(extracted_tables)
                self.logger.error(f"SQL validation failed: Query contains unauthorized tables: {table_list}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"SQL validation error: {str(e)}")
            self.logger.error(traceback.format_exc())
            return True

    def _execute_sql_query(self, sql_query: str, params: tuple = None) -> List[Dict]:
        try:
            if not self._validate_sql_query(sql_query):
                return [{"error": "Invalid SQL query: security validation failed"}]
            with connection.cursor() as cursor:
                cursor.execute(sql_query, params) if params else cursor.execute(sql_query)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"SQL query execution failed: {str(e)}")
            return [{"error": f"Query failed: {str(e)}"}]

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
            self.SQL_LOAN_GENERATION_PROMPT_ID,
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
            sql_query = sql_query.replace("SELECT id", "SELECT loan_details.id")
        
        if sql_query.endswith(';'):
            sql_query = sql_query[:-1]
        
        if "LIMIT" not in sql_query.upper():
            sql_query += f" LIMIT {limit}"
        
        return sql_query

    def _loan_query_tool(self, query: str, company_id: str = None) -> str:
        """
        Tool for looking up loan details based on query parameters.
        
        Args:
            query (str): The user's query
            company_id (str): Optional company ID to filter results
            
        Returns:
            str: Response with loan details
        """
        sql_query = self._generate_query_from_schema(query, company_id)
        
        results = self._execute_sql_query(sql_query)
        
        if len(results) == 1 and "error" in results[0]:
            error_message = results[0]["error"]
            self.logger.error(f"Error executing SQL query: {error_message}")
            return f"Error retrieving loan details: {error_message}"
        
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
        
        if not formatted_results:
            return FALLBACK_TEMPLATES["LOAN_NOT_FOUND"]
        
        input_variables = {
            "query": query,
            "company_id": company_id or "Not specified",
            "context": json.dumps(formatted_results, indent=2),
            "sql_query": sql_query
        }
        
        try:
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                self.LOAN_QUERY_PROMPT_ID,
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
                loan = formatted_results[0]
                acc_num = loan.get('account_number', 'Unknown')
                currency = loan.get('currency', '')
                principal = loan.get('principal_amount', 'Not available')
                date = loan.get('start_date', 'Not available')
                return f"Found loan {acc_num} from {date} with principal amount {principal} {currency}."
            else:
                # Multiple loan summary
                count = len(formatted_results)
                return f"Found {count} loans matching your query. The loan numbers are: {', '.join([r.get('account_number', 'Unknown') for r in formatted_results if 'account_number' in r])}."

    def process_query(self, query: str, company_id: str = None, document_key: str = None, session_id: str = None) -> Dict:
        """
        Process a user query by generating SQL from the schema and executing it
        
        Args:
            query (str): The user's query about loan details
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
                        "response": f"Error retrieving loan details: {error_message}",
                        "company_id": company_id,
                        "resources": [],
                        "session_id": session_id
                    }
                }
            
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
            
            if not formatted_results:
                return {
                    "message": "No results found",
                    "data": {
                        "response": FALLBACK_TEMPLATES["LOAN_NOT_FOUND"],
                        "company_id": company_id,
                        "resources": [],
                        "session_id": session_id,
                        "sql_query": sql_query
                    }
                }
            
            # Step 6: Generate a human-readable response using PromptLayer
            input_variables = {
                "query": query,
                "company_id": company_id or "Not specified",
                "context": json.dumps(formatted_results, indent=2),
                "sql_query": sql_query
            }
            
            # Get the prompt template from PromptLayer
            pl = PromptLayer(api_key=settings.PROMPTLAYER_API_KEY)
            prompt_template = pl.templates.get(
                self.LOAN_QUERY_PROMPT_ID,
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
                if "account_number" in result:
                    resources.append(result["account_number"])
            
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
        return GLOBAL_SESSION_STORE.get(session_id, {})

    def _save_session_data(self, session_id: str, data: Dict):
        GLOBAL_SESSION_STORE[session_id] = data
        self.logger.info(f"Saved session data for {session_id}")