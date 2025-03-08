from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class QueryRequest(BaseModel):
    """Schema for natural language query request"""
    query: str

class QueryHistory(BaseModel):
    """Schema for query history"""
    id: int
    connection_id: int
    natural_query: str
    sql_query: str
    execution_time: float
    status: str
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class QueryResponse(BaseModel):
    """Schema for query response"""
    natural_query: str
    sql_query: str
    execution_time: float
    status: str
    error_message: Optional[str]
    results: Optional[List[Dict[str, Any]]]
    row_count: int

class QueryHistoryResponse(BaseModel):
    """Schema for paginated query history response"""
    total: int
    queries: List[QueryHistory]
    limit: int
    offset: int 