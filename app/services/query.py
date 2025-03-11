from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from app.models.database import QueryHistory
from typing import Dict, Any, List, Optional
import time
from datetime import datetime
from app.models.connection import Connection
from app.services.database import DatabaseService
import openai
from app.core.config import settings

class QueryService:
    def __init__(self, db: Session):
        self.db = db
        self.database_service = DatabaseService(db)
        openai.api_key = settings.OPENAI_API_KEY

    async def execute_query(
        self,
        connection: Connection,
        sql_query: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query on the connected database"""
        start_time = time.time()
        try:
            # Create connection string
            if connection.db_type == "sqlite":
                conn_str = f"sqlite:///{connection.database}"
            elif connection.db_type == "postgresql":
                conn_str = f"postgresql://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
            else:  # MySQL
                conn_str = f"mysql+mysqlconnector://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"

            # Execute query
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                result = conn.execute(text(sql_query))
                rows = [dict(row) for row in result]

            execution_time = time.time() - start_time

            # Record query history
            await self._record_query_history(
                connection.id,
                sql_query,
                execution_time,
                "success",
                user_id=user_id
            )

            return {
                "rows": rows,
                "execution_time": execution_time,
                "row_count": len(rows)
            }

        except Exception as e:
            execution_time = time.time() - start_time
            # Record failed query
            await self._record_query_history(
                connection.id,
                sql_query,
                execution_time,
                "error",
                str(e),
                user_id=user_id
            )
            raise Exception(f"Query execution failed: {str(e)}")

    async def get_query_history(
        self,
        connection_id: int,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get query history for a connection"""
        # Verify connection ownership
        connection = self.database_service.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        # Get total count
        total_count = self.db.query(QueryHistory).filter(
            QueryHistory.connection_id == connection_id,
            QueryHistory.user_id == user_id
        ).count()

        # Get queries
        queries = self.db.query(QueryHistory).filter(
            QueryHistory.connection_id == connection_id,
            QueryHistory.user_id == user_id
        ).order_by(
            QueryHistory.created_at.desc()
        ).offset(offset).limit(limit).all()

        return {
            "total": total_count,
            "queries": queries,
            "limit": limit,
            "offset": offset
        }

    async def _record_query_history(
        self,
        connection_id: int,
        sql_query: str,
        execution_time: float,
        status: str,
        error_message: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> None:
        """Record a query execution in the history"""
        history = QueryHistory(
            connection_id=connection_id,
            user_id=user_id,
            sql_query=sql_query,
            execution_time=execution_time,
            status=status,
            error_message=error_message,
            created_at=datetime.utcnow()
        )
        self.db.add(history)
        await self.db.commit()

    async def process_natural_language_query(
        self, 
        connection_id: int,
        user_id: int,
        query: str
    ) -> Dict[str, Any]:
        """Process a natural language query and convert it to SQL"""
        try:
            # Get the connection
            connection = self.database_service.get_connection(connection_id, user_id)
            if not connection:
                raise ValueError("Connection not found")

            # Get the database schema
            schema = connection.schema
            if not schema:
                schema = self.database_service.get_schema(connection)
                connection.schema = schema
                self.db.commit()

            # Convert schema to string format for OpenAI
            schema_str = self._format_schema_for_prompt(schema)

            # Create the prompt for OpenAI
            prompt = f"""Given the following database schema:
{schema_str}

Convert this natural language query to SQL:
{query}

Return only the SQL query without any explanation."""

            # Get SQL query from OpenAI
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Convert natural language queries to SQL based on the provided schema."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            sql_query = response.choices[0].message.content.strip()

            # Execute the query
            start_time = datetime.utcnow()
            try:
                results = await self.execute_query(connection, sql_query, user_id=user_id)
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                status = "success"
                error_message = None
            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                status = "error"
                error_message = str(e)
                results = None

            # Store query history
            query_history = QueryHistory(
                connection_id=connection_id,
                user_id=user_id,
                natural_query=query,
                sql_query=sql_query,
                execution_time=execution_time,
                status=status,
                error_message=error_message
            )
            self.db.add(query_history)
            self.db.commit()

            return {
                "natural_query": query,
                "sql_query": sql_query,
                "execution_time": execution_time,
                "status": status,
                "error_message": error_message,
                "results": results["rows"] if results else None,
                "row_count": results["row_count"] if results else 0
            }

        except Exception as e:
            raise Exception(f"Failed to process natural language query: {str(e)}")

    def _format_schema_for_prompt(self, schema: Dict[str, Any]) -> str:
        """Format the schema into a string for the OpenAI prompt"""
        schema_lines = []
        for table_name, table_info in schema.items():
            columns = table_info["columns"]
            column_lines = [
                f"  - {col['name']}: {col['type']}" +
                (f" (Primary Key)" if col.get('primary_key') or col.get('key') == 'PRI' else "") +
                (f" (Nullable)" if col.get('null') == 'YES' or col.get('null') == True else "")
                for col in columns
            ]
            schema_lines.append(f"Table: {table_name}")
            schema_lines.extend(column_lines)
            schema_lines.append("")  # Empty line between tables

        return "\n".join(schema_lines) 