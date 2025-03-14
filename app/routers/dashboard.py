from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_auth
from app.services.database import DatabaseService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(require_auth)
):
    """Render the dashboard page"""
    try:
        # Get user's database connections
        db_service = DatabaseService(db)
        connections = db_service.get_connections(current_user.id)
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "connections": connections
        })
    except HTTPException as e:
        if e.status_code in (status.HTTP_307_TEMPORARY_REDIRECT, status.HTTP_401_UNAUTHORIZED):
            return RedirectResponse(
                url=e.headers.get("Location", "/unauthorized"),
                status_code=status.HTTP_303_SEE_OTHER
            )
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))