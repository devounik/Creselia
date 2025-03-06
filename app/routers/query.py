from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.database import NaturalLanguageQuery, SQLQueryResponse
from app.services.query import QueryService
from app.core.database import get_db
from app.services.ai import AIService

router = APIRouter()

@router.post("/query", response_model=SQLQueryResponse)
async def execute_query(
    query: NaturalLanguageQuery,
    db: Session = Depends(get_db)
):
    """
    Convert natural language to SQL and execute the query
    """
    try:
        # Initialize services
        query_service = QueryService(db)
        ai_service = AIService()

        # Get database connection and schema
        connection = await query_service.get_connection(query.connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail="Database connection not found")

        # Convert natural language to SQL using AI
        sql_query = await ai_service.natural_to_sql(
            query.query,
            connection.schema
        )

        # Execute the SQL query and get results
        results = await query_service.execute_query(
            connection,
            sql_query
        )

        return SQLQueryResponse(
            natural_query=query.query,
            sql_query=sql_query,
            results=results,
            execution_time=results.get("execution_time", 0.0),
            status="success",
            error_message=None
        )
    except Exception as e:
        return SQLQueryResponse(
            natural_query=query.query,
            sql_query="",
            results=[],
            execution_time=0.0,
            status="error",
            error_message=str(e)
        )

@router.get("/history/{connection_id}")
async def get_query_history(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """
    Get query history for a specific connection
    """
    query_service = QueryService(db)
    return await query_service.get_query_history(connection_id) 