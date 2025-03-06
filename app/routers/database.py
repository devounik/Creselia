from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.schemas.database import (
    DatabaseConnectionCreate,
    DatabaseConnectionResponse
)
from app.services.database import DatabaseService
from app.core.database import get_db

router = APIRouter()

@router.post("/connect", response_model=DatabaseConnectionResponse)
async def connect_database(
    connection: DatabaseConnectionCreate,
    db: Session = Depends(get_db)
):
    """
    Connect to a database and store the connection details
    """
    try:
        db_service = DatabaseService(db)
        return await db_service.create_connection(connection)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/connections", response_model=List[DatabaseConnectionResponse])
async def get_connections(db: Session = Depends(get_db)):
    """
    Get all stored database connections
    """
    db_service = DatabaseService(db)
    return await db_service.get_connections()

@router.get("/connections/{connection_id}", response_model=DatabaseConnectionResponse)
async def get_connection(connection_id: int, db: Session = Depends(get_db)):
    """
    Get a specific database connection
    """
    db_service = DatabaseService(db)
    connection = await db_service.get_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection

@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: int, db: Session = Depends(get_db)):
    """
    Delete a database connection
    """
    db_service = DatabaseService(db)
    success = await db_service.delete_connection(connection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"message": "Connection deleted successfully"} 