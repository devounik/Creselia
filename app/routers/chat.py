from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.core.auth import require_auth
from app.core.database import get_db
from app.services.connection_service import ConnectionService
from app.services.chat_service import ChatService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    connection: Optional[int] = None,
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection ID is required"
        )
    
    conn_service = ConnectionService(db)
    db_connection = conn_service.get_connection(connection, current_user.id)
    
    if not db_connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    if db_connection.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this connection"
        )
    
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "user": current_user,
            "connection": db_connection
        }
    )

@router.post("/api/chat")
async def chat_message(
    request: Dict[str, Any],
    current_user = Depends(require_auth),
    db: Session = Depends(get_db)
):
    if "connection_id" not in request or "message" not in request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection ID and message are required"
        )
    
    conn_service = ConnectionService(db)
    db_connection = conn_service.get_connection(request["connection_id"], current_user.id)
    
    if not db_connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    if db_connection.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this connection"
        )
    
    chat_service = ChatService(db)
    try:
        result = await chat_service.process_message(
            message=request["message"],
            connection=db_connection
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 