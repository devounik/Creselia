from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.connection import Connection
from app.services.auth import AuthService
from typing import Optional
import logging
from pydantic import BaseModel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

# Pydantic model for connection creation
class ConnectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get token from cookie
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Get user from token
        auth_service = AuthService(db)
        user = auth_service.get_current_user(token.split(" ")[1])
        
        # Get user's connections
        connections = db.query(Connection).filter(Connection.user_id == user.id).all()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "connections": connections
        })
    except HTTPException:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("access_token")
        return response

@router.post("/api/connections", status_code=status.HTTP_201_CREATED)
async def create_connection(
    connection_data: ConnectionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    # Get user from token
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(token.split(" ")[1])
        
        # Create new connection
        connection = Connection(
            name=connection_data.name,
            description=connection_data.description,
            db_type=connection_data.db_type,
            host=connection_data.host,
            port=connection_data.port,
            database=connection_data.database,
            username=connection_data.username,
            password=connection_data.password,
            user_id=user.id
        )
        
        db.add(connection)
        db.commit()
        db.refresh(connection)
        
        return {"id": connection.id, "name": connection.name}
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/api/connections/{connection_id}")
async def delete_connection(
    connection_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # Get user from token
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(token.split(" ")[1])
        
        # Get connection and verify ownership
        connection = db.query(Connection).filter(
            Connection.id == connection_id,
            Connection.user_id == user.id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        db.delete(connection)
        db.commit()
        
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/api/connections/{connection_id}/test")
async def test_connection(
    connection_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # Get user from token
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(token.split(" ")[1])
        
        connection = db.query(Connection).filter(
            Connection.id == connection_id,
            Connection.user_id == user.id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Test the connection (implement your connection testing logic here)
        # Update last_used timestamp
        connection.last_used = datetime.utcnow()
        connection.is_active = True
        db.commit()
        
        return {"status": "success"}
    except Exception as e:
        connection.is_active = False
        db.commit()
        logger.error(f"Error testing connection: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 