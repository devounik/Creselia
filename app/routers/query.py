from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.query import QueryService
from app.models.connection import Connection
from app.models.database import QueryHistory
from app.schemas.query import QueryRequest, QueryResponse, QueryHistoryResponse
from typing import List
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/query", tags=["query"])

@router.post("/{connection_id}", response_model=QueryResponse)
async def execute_query(
    connection_id: int,
    query_request: QueryRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Execute a natural language query on a database connection"""
    try:
        query_service = QueryService(db)
        result = await query_service.process_natural_language_query(
            connection_id=connection_id,
            user_id=current_user.id,
            query=query_request.query
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{connection_id}/history", response_model=QueryHistoryResponse)
async def get_query_history(
    connection_id: int,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get query history for a database connection"""
    try:
        query_service = QueryService(db)
        return query_service.get_query_history(
            connection_id=connection_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 