from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.auth import AuthService
from app.core.database import get_db

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.scope["user"] = None
        
        # Get token from cookie
        token = request.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            try:
                # Get database session
                db = next(get_db())
                
                # Get user from token
                auth_service = AuthService(db)
                user = auth_service.get_current_user(token.split(" ")[1])
                
                # Set user in request scope
                request.scope["user"] = user
            except Exception:
                pass
        
        response = await call_next(request)
        return response 