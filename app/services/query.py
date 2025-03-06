from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from app.models.database import DatabaseConnection, QueryHistory
from typing import Dict, Any, List, Optional
import time
from datetime import datetime

class QueryService:
    def __init__(self, db: Session):
        self.db = db

    async def execute_query(
        self,
        connection: DatabaseConnection,
        sql_query: str
    ) -> Dict[str, Any]:
        """Execute a SQL query on the connected database"""
        start_time = time.time()
        try:
            # Create connection string
            if connection.engine == "sqlite":
                conn_str = f"sqlite:///{connection.database}"
            elif connection.engine == "postgresql":
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
                "success"
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
                str(e)
            )
            raise Exception(f"Query execution failed: {str(e)}")

    async def get_query_history(
        self,
        connection_id: int,
        limit: int = 100
    ) -> List[QueryHistory]:
        """Get query history for a specific connection"""
        return self.db.query(QueryHistory)\
            .filter(QueryHistory.connection_id == connection_id)\
            .order_by(QueryHistory.created_at.desc())\
            .limit(limit)\
            .all()

    async def _record_query_history(
        self,
        connection_id: int,
        sql_query: str,
        execution_time: float,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Record a query execution in the history"""
        history = QueryHistory(
            connection_id=connection_id,
            sql_query=sql_query,
            execution_time=execution_time,
            status=status,
            error_message=error_message,
            created_at=datetime.utcnow()
        )
        self.db.add(history)
        await self.db.commit()

    async def get_connection(self, connection_id: int) -> Optional[DatabaseConnection]:
        """Get a database connection by ID"""
        return self.db.query(DatabaseConnection)\
            .filter(DatabaseConnection.id == connection_id)\
            .first() 