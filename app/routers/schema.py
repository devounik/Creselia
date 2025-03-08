from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.schema import SchemaService
from app.core.auth import get_current_user
from typing import Dict, Any, List

router = APIRouter(prefix="/api/schema", tags=["schema"])

@router.get("/{connection_id}")
async def get_schema(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get the database schema for a connection"""
    try:
        schema_service = SchemaService(db)
        return schema_service.get_schema(connection_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{connection_id}/tables")
async def get_tables(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[str]:
    """Get list of tables in the database"""
    try:
        schema_service = SchemaService(db)
        return schema_service.get_tables(connection_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{connection_id}/tables/{table_name}")
async def get_table_columns(
    connection_id: int,
    table_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get column information for a specific table"""
    try:
        schema_service = SchemaService(db)
        return schema_service.get_table_columns(connection_id, table_name, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{connection_id}/refresh")
async def refresh_schema(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Force refresh the schema for a database connection"""
    try:
        schema_service = SchemaService(db)
        return schema_service.refresh_schema(connection_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 