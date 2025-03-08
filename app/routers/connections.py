from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.connection import Connection
from app.services.auth import AuthService
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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

@router.post("/connections/create")
async def create_connection(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get user from token
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return RedirectResponse(url="/login", status_code=303)

    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(token.split(" ")[1])
        
        # Get form data
        form_data = await request.form()
        
        # Create new connection
        connection = Connection(
            name=form_data.get("name"),
            description=form_data.get("description"),
            db_type=form_data.get("db_type"),
            host=form_data.get("host"),
            port=int(form_data.get("port")) if form_data.get("port") else None,
            database=form_data.get("database"),
            username=form_data.get("username"),
            password=form_data.get("password"),
            user_id=user.id
        )
        
        db.add(connection)
        db.commit()
        db.refresh(connection)
        
        return RedirectResponse(url="/dashboard", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "connections": db.query(Connection).filter(Connection.user_id == user.id).all(),
                "error": str(e)
            }
        )

@router.get("/connections/{connection_id}/test")
async def test_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    try:
        # Test the connection (implement your connection testing logic here)
        # Update last_used timestamp
        connection.last_used = datetime.utcnow()
        connection.is_active = True
        db.commit()
        return {"status": "success"}
    except Exception as e:
        connection.is_active = False
        db.commit()
        raise HTTPException(status_code=500, detail=str(e)) 