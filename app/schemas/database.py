from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class DatabaseConnectionBase(BaseModel):
    name: str
    engine: str = Field(..., description="Database engine (postgresql, mysql, sqlite)")
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None

class DatabaseConnectionCreate(DatabaseConnectionBase):
    pass

class DatabaseConnectionResponse(DatabaseConnectionBase):
    id: int
    db_schema: Dict[str, Any] = Field(alias="schema")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class NaturalLanguageQuery(BaseModel):
    connection_id: int
    query: str = Field(..., description="Natural language query to convert to SQL")

class SQLQueryResponse(BaseModel):
    natural_query: str
    sql_query: str
    results: list
    execution_time: float
    status: str
    error_message: Optional[str] = None 