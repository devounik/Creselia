from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.schema import SchemaService
from app.core.database import get_db
from typing import Dict, Any

router = APIRouter()

@router.get("/schema/{connection_id}")
async def get_schema(
    connection_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the schema for a specific database connection
    """
    try:
        schema_service = SchemaService(db)
        schema = await schema_service.get_schema(connection_id)
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")
        return schema
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/schema/{connection_id}/refresh")
async def refresh_schema(
    connection_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Refresh the schema for a specific database connection
    """
    try:
        schema_service = SchemaService(db)
        schema = await schema_service.refresh_schema(connection_id)
        return schema
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 