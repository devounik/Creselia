from typing import Dict, Any, Optional
import sqlparse
import re
from app.models.connection import Connection
from app.services.database_service import DatabaseService

class ChatService:
    def __init__(self, connection: Connection):
        self.connection = connection
        self.db_service = DatabaseService(connection)
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a chat message and return a response."""
        # Check if it's a schema-related question
        if self._is_schema_query(message):
            return await self._handle_schema_query(message)
        
        # Check if the message is a direct SQL query
        if self._is_sql_query(message):
            return await self._execute_sql_query(message)
        
        # For other natural language queries, provide guidance
        return {
            "message": "I understand you're asking about the database. "
                      "I can help you with:\n"
                      "1. Direct SQL queries\n"
                      "2. Information about tables and columns (try asking 'show tables' or 'describe table_name')\n"
                      "Please rephrase your question or provide a SQL query."
        }
    
    def _is_schema_query(self, message: str) -> bool:
        """Check if the message is asking about database schema."""
        message = message.lower()
        schema_keywords = [
            'show tables', 'list tables', 'what tables', 'tell me about tables',
            'describe table', 'table columns', 'show columns', 'list columns',
            'what columns', 'tell me about columns', 'table structure',
            'database structure', 'schema'
        ]
        return any(keyword in message for keyword in schema_keywords)
    
    async def _handle_schema_query(self, message: str) -> Dict[str, Any]:
        """Handle queries about database schema."""
        message = message.lower()
        try:
            # If asking about tables
            if any(keyword in message for keyword in ['show tables', 'list tables', 'what tables']):
                result = await self.db_service.execute_query("SHOW TABLES")
                return {
                    "message": "Here are the tables in the database:",
                    "results": {
                        "columns": result.columns if result else [],
                        "rows": result.rows if result else []
                    }
                }
            
            # If asking about specific table
            table_match = re.search(r'describe\s+(\w+)', message)
            if table_match:
                table_name = table_match.group(1)
                result = await self.db_service.execute_query(f"DESCRIBE {table_name}")
                return {
                    "message": f"Here's the structure of table '{table_name}':",
                    "results": {
                        "columns": result.columns if result else [],
                        "rows": result.rows if result else []
                    }
                }
            
            # If asking about all columns
            if any(keyword in message for keyword in ['all columns', 'tell me about columns']):
                # Get all tables first
                tables_result = await self.db_service.execute_query("SHOW TABLES")
                all_columns = []
                
                if tables_result and tables_result.rows:
                    for table_row in tables_result.rows:
                        table_name = table_row[0]
                        columns_result = await self.db_service.execute_query(f"SHOW COLUMNS FROM {table_name}")
                        if columns_result and columns_result.rows:
                            for col_row in columns_result.rows:
                                all_columns.append([table_name] + list(col_row))
                
                return {
                    "message": "Here are all columns in the database:",
                    "results": {
                        "columns": ["Table", "Field", "Type", "Null", "Key", "Default", "Extra"],
                        "rows": all_columns
                    }
                }
            
            # Default schema query
            result = await self.db_service.execute_query("SHOW TABLES")
            return {
                "message": "Here are the tables in the database. You can ask me to 'describe' any specific table:",
                "results": {
                    "columns": result.columns if result else [],
                    "rows": result.rows if result else []
                }
            }
            
        except Exception as e:
            return {
                "message": f"Error retrieving schema information: {str(e)}"
            }
    
    def _is_sql_query(self, message: str) -> bool:
        """Check if a message appears to be a SQL query."""
        # Remove comments and whitespace
        cleaned = sqlparse.format(message, strip_comments=True).strip()
        if not cleaned:
            return False
        
        # Check if it starts with common SQL keywords
        sql_starters = (
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
            'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN'
        )
        return cleaned.upper().startswith(sql_starters)
    
    async def _execute_sql_query(self, query: str) -> Dict[str, Any]:
        """Execute a SQL query and return the results."""
        try:
            # Format the query for better readability
            formatted_query = sqlparse.format(
                query,
                reindent=True,
                keyword_case='upper'
            )
            
            # Execute the query
            result = await self.db_service.execute_query(query)
            
            # Prepare the response
            response = {
                "sql": formatted_query,
                "results": {
                    "columns": result.columns if result else [],
                    "rows": result.rows if result else []
                }
            }
            
            # Add a natural language summary
            response["message"] = self._generate_result_summary(result)
            
            return response
            
        except Exception as e:
            return {
                "sql": query,
                "error": str(e)
            }
    
    def _generate_result_summary(self, result: Optional[Any]) -> str:
        """Generate a natural language summary of the query results."""
        if not result or not result.rows:
            return "The query was executed successfully, but returned no results."
        
        row_count = len(result.rows)
        return f"Query executed successfully. Found {row_count} {'row' if row_count == 1 else 'rows'}." 