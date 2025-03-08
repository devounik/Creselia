from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth import AuthService

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get the current authenticated user or None"""
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        try:
            auth_service = AuthService(db)
            return auth_service.get_current_user(token.split(" ")[1])
        except Exception:
            pass
    return None

async def require_auth(request: Request, current_user = Depends(get_current_user)):
    """Require authentication for protected routes"""
    if not current_user:
        return RedirectResponse(
            url=f"/unauthorized?next={request.url.path}",
            status_code=303
        )
    return current_user 