from typing import Dict
from sqlalchemy import create_engine, text
from app.services.nl_to_sql_service import NLToSQLService
from app.services.connection_service import ConnectionService
from app.core.database import get_db
import json
import re
import datetime
import decimal
import time
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db=None):
        self.nl_to_sql = NLToSQLService()
        self.db = db if db is not None else next(get_db())
        self.connection_service = ConnectionService(self.db)

    def _is_schema_question(self, message: str) -> bool:
        """Check if the message is asking about schema/table information"""
        patterns = [
            r"tell me about (?:the )?(?:table )?['`]?(\w+)['`]?",
            r"describe (?:the )?(?:table )?['`]?(\w+)['`]?",
            r"what (?:columns|fields) (?:are )?in (?:the )?(?:table )?['`]?(\w+)['`]?",
            r"show (?:me )?(?:the )?structure of (?:the )?(?:table )?['`]?(\w+)['`]?",
            r"explain (?:the )?(?:table )?['`]?(\w+)['`]?"
        ]
        return any(re.search(pattern, message.lower()) for pattern in patterns)

    def _get_table_name_from_question(self, message: str) -> str:
        """Extract table name from the question"""
        patterns = [
            r"tell me about (?:the )?(?:table )?['`]?(\w+)['`]?",
            r"describe (?:the )?(?:table )?['`]?(\w+)['`]?",
            r"what (?:columns|fields) (?:are )?in (?:the )?(?:table )?['`]?(\w+)['`]?",
            r"show (?:me )?(?:the )?structure of (?:the )?(?:table )?['`]?(\w+)['`]?",
            r"explain (?:the )?(?:table )?['`]?(\w+)['`]?"
        ]
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1)
        return None

    def _describe_table(self, table_name: str, schema: str) -> Dict:
        """Generate a description of a table based on its schema"""
        try:
            if not schema:
                return {
                    "success": False,
                    "error": "No schema information available"
                }
            
            # Find the table section in the schema string
            table_pattern = f"Table: {table_name}\n(.*?)(?=\nTable:|$)"
            table_match = re.search(table_pattern, schema, re.DOTALL)
            
            if not table_match:
                return {
                    "success": False,
                    "error": f"Table '{table_name}' not found in schema"
                }
            
            # Get the table description including columns
            table_desc = table_match.group(1).strip()
            
            # Find any relationships for this table
            relationships = []
            rel_pattern = f"  - {table_name}\\.(.*?) -> (.*?)\\n"
            for rel in re.finditer(rel_pattern, schema):
                relationships.append(f"- {table_name}.{rel.group(1)} references {rel.group(2)}")
            
            # Combine table description with relationships
            description = table_desc
            if relationships:
                description += "\n\nRelationships:\n" + "\n".join(relationships)
            
            return {
                "success": True,
                "message": description
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to describe table: {str(e)}"
            }

    def _format_schema_for_nl_to_sql(self, schema: str) -> str:
        """Format schema information for NLToSQL service"""
        if not schema:
            return ""
        
        # The schema is already formatted for NLToSQL service
        return schema

    def _validate_schema(self, schema: str) -> bool:
        """Validate that the schema string is properly formatted"""
        if not schema:
            return False
        
        # Check for required sections
        if "Database Schema:" not in schema:
            return False
        
        # Check for at least one table definition
        if not re.search(r"Table: \w+\n", schema):
            return False
        
        return True

    def _get_schema(self, connection, url: str) -> Dict:
        """Get schema information, either from cache or fresh"""
        try:
            # Check if we have a valid cached schema
            if connection.schema and self._validate_schema(connection.schema):
                return {
                    "success": True,
                    "schema": connection.schema
                }
            
            # Get fresh schema
            from app.services.schema_service import SchemaService
            schema_service = SchemaService(url, connection.db_type, connection.database)
            schema_info = schema_service.format_schema_for_prompt()
            
            # Validate the fresh schema
            if not self._validate_schema(schema_info):
                return {
                    "success": False,
                    "error": "Generated schema failed validation"
                }
            
            # Store and return the schema
            connection.schema = schema_info
            self.db.commit()
            
            return {
                "success": True,
                "schema": schema_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get schema: {str(e)}"
            }

    def _sanitize_value(self, value) -> str:
        """Sanitize a value to ensure it's JSON serializable"""
        try:
            if value is None:
                return None
            elif isinstance(value, (datetime.date, datetime.datetime)):
                return value.isoformat()
            elif isinstance(value, decimal.Decimal):
                # Preserve decimal precision
                return str(value)
            elif isinstance(value, bytes):
                # Handle binary data safely
                try:
                    return value.decode('utf-8', errors='replace')
                except Exception:
                    return "[binary data]"
            elif isinstance(value, (int, float, bool)):
                # Basic types can be returned as is
                return value
            elif isinstance(value, str):
                # Ensure string is valid UTF-8 and not too long
                if len(value) > 1000000:  # 1MB limit
                    return value[:1000000] + "... [truncated]"
                return value.encode('utf-8', errors='replace').decode('utf-8')
            else:
                # For any other type, convert to string with type info
                return f"{str(value)} ({type(value).__name__})"
        except Exception as e:
            logger.error(f"Error sanitizing value of type {type(value)}: {str(e)}")
            return f"[Error: Could not sanitize value of type {type(value).__name__}]"

    def _create_safe_response(self, success: bool, message: str = "", error: str = "", sql: str = "", results: dict = None) -> Dict:
        """Create a safe response dictionary with basic Python types"""
        try:
            base_response = {
                "success": bool(success),
                "message": self._sanitize_value(message) if message else "",
                "sql": self._sanitize_value(sql) if sql else ""
            }
            
            if error:
                # Sanitize error message to avoid exposing internal details
                error_msg = self._sanitize_value(error)
                if "mysql" in error_msg.lower() or "sql" in error_msg.lower():
                    error_msg = "Database error occurred. Please try again."
                base_response["error"] = error_msg
            
            if results:
                # Format results as HTML table
                table_html = "<div class='result-table-wrapper'><table class='result-table'>"
                
                # Add headers
                if results.get("columns"):
                    table_html += "<thead><tr>"
                    for col in results["columns"]:
                        table_html += f"<th>{self._sanitize_value(col)}</th>"
                    table_html += "</tr></thead>"
                
                # Add rows
                if results.get("rows"):
                    table_html += "<tbody>"
                    for row in results["rows"]:
                        table_html += "<tr>"
                        for cell in row:
                            table_html += f"<td>{self._sanitize_value(cell)}</td>"
                        table_html += "</tr>"
                    table_html += "</tbody>"
                
                table_html += "</table></div>"
                
                # Add summary text
                total_rows = len(results.get("rows", []))
                if total_rows > 0:
                    summary = f"Found {total_rows} result{'s' if total_rows != 1 else ''}:"
                    base_response["content"] = f"{summary}<br>{table_html}"
                else:
                    base_response["content"] = "No matching records found."
            
            # Verify the response is JSON serializable
            json.dumps(base_response)
            return base_response
            
        except Exception as e:
            logger.error(f"Error creating safe response: {str(e)}")
            return {
                "success": False,
                "error": "An internal error occurred while processing the response",
                "message": "",
                "sql": ""
            }

    async def process_message(self, message: str, connection_id: int = None, user_id: int = None, connection = None) -> Dict:
        """Process a chat message and return the response"""
        engine = None
        start_time = time.time()
        
        try:
            # Get connection details if not provided
            if connection is None and connection_id is not None and user_id is not None:
                connection = self.connection_service.get_connection(connection_id, user_id)
            
            if not connection:
                return self._create_safe_response(
                    success=False,
                    error="Connection not found"
                )

            logger.info(f"Processing message for connection: {connection.id}")
            
            # Create database URL with connection timeout
            if connection.db_type.lower() == "mysql":
                decrypted_password = connection.password
                if not decrypted_password:
                    return self._create_safe_response(
                        success=False,
                        error="Failed to decrypt database password"
                    )
                
                # Configure MySQL connection with proper parameters
                url = (
                    f"mysql+mysqlconnector://{connection.username}:{decrypted_password}"
                    f"@{connection.host}:{connection.port}/{connection.database}"
                    "?charset=utf8mb4"
                    "&collation=utf8mb4_unicode_ci"
                    "&connection_timeout=30"
                    "&pool_size=5"
                )
            else:
                return self._create_safe_response(
                    success=False,
                    error=f"Database type {connection.db_type} not supported"
                )

            # Get schema information with timeout
            logger.info("Getting schema information...")
            schema_result = self._get_schema(connection, url)
            if not schema_result["success"]:
                return self._create_safe_response(
                    success=False,
                    error=schema_result["error"]
                )

            # Check execution time
            if time.time() - start_time > 30:  # 30 seconds timeout
                return self._create_safe_response(
                    success=False,
                    error="Query timed out"
                )

            # Create database engine with basic configuration
            try:
                logger.info("Creating database engine...")
                engine = create_engine(
                    url,
                    pool_pre_ping=True  # Keep this as it's supported
                )
                
                with engine.connect() as conn:
                    # Set session timeout
                    conn.execute(text("SET SESSION wait_timeout=30"))
                    
                    # Format schema for NLToSQL service
                    logger.info("Formatting schema for NLToSQL service...")
                    formatted_schema = self._format_schema_for_nl_to_sql(schema_result["schema"])

                    # Generate SQL from natural language
                    logger.info("Generating SQL from natural language...")
                    result = await self.nl_to_sql.generate_sql(message, formatted_schema)
                    if not result["success"]:
                        return self._create_safe_response(
                            success=False,
                            error=result["error"]
                        )
                    
                    # Execute query with timeout monitoring
                    logger.info("Executing query...")
                    try:
                        result_set = conn.execute(text(result["sql"]))
                        
                        # Process results with size limits
                        try:
                            columns = [str(col) for col in result_set.keys()]
                            rows = []
                            row_count = 0
                            max_rows = 1000
                            
                            for row in result_set.fetchall():
                                if row_count >= max_rows:
                                    break
                                processed_row = [self._sanitize_value(value) for value in row]
                                rows.append(processed_row)
                                row_count += 1
                            
                            logger.info(f"Query executed successfully. Found {row_count} rows.")
                            
                            return self._create_safe_response(
                                success=True,
                                message=result.get("explanation", "Query executed successfully"),
                                sql=result.get("sql", ""),
                                results={
                                    "columns": columns,
                                    "rows": rows,
                                    "total_rows": row_count,
                                    "truncated": row_count >= max_rows
                                }
                            )
                            
                        except Exception as e:
                            logger.error(f"Error processing query results: {str(e)}")
                            return self._create_safe_response(
                                success=False,
                                error="Error processing query results",
                                sql=result.get("sql", "")
                            )
                            
                    except Exception as e:
                        logger.error(f"Error executing query: {str(e)}")
                        return self._create_safe_response(
                            success=False,
                            error="Error executing query",
                            sql=result.get("sql", "")
                        )

            except Exception as e:
                logger.error(f"Database connection error: {str(e)}")
                return self._create_safe_response(
                    success=False,
                    error="Failed to connect to database"
                )

        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            return self._create_safe_response(
                success=False,
                error="An unexpected error occurred"
            )
        finally:
            if engine:
                engine.dispose() 