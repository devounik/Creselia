from fastapi import Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth import AuthService
from app.core.config import settings
from datetime import datetime
import jwt
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Rate limiting
from collections import defaultdict
from datetime import datetime, timedelta

# Store login attempts: {ip: [(timestamp, success), ...]}
login_attempts = defaultdict(list)
MAX_ATTEMPTS = 5  # Maximum failed attempts
ATTEMPT_WINDOW = 300  # 5 minutes window for attempts
LOCKOUT_DURATION = 900  # 15 minutes lockout

def is_rate_limited(ip: str) -> bool:
    """Check if an IP is rate limited"""
    now = datetime.now()
    # Clean up old attempts
    login_attempts[ip] = [
        attempt for attempt in login_attempts[ip]
        if now - attempt[0] < timedelta(seconds=ATTEMPT_WINDOW)
    ]
    
    # Count failed attempts in window
    failed_attempts = sum(
        1 for attempt in login_attempts[ip]
        if not attempt[1]  # not success
    )
    
    return failed_attempts >= MAX_ATTEMPTS

def record_login_attempt(ip: str, success: bool):
    """Record a login attempt"""
    login_attempts[ip].append((datetime.now(), success))

async def validate_token(token: str) -> Optional[dict]:
    """Validate JWT token and return payload if valid"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token expiration
        exp = payload.get('exp')
        if not exp or datetime.fromtimestamp(exp) < datetime.utcnow():
            return None
            
        return payload
    except jwt.InvalidTokenError:
        return None

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get the current authenticated user or None"""
    try:
        token = request.cookies.get("access_token")
        if not token or not token.startswith("Bearer "):
            return None
            
        token_str = token.split(" ")[1]
        payload = await validate_token(token_str)
        if not payload:
            return None
            
        auth_service = AuthService(db)
        user = auth_service.get_user_by_id(payload.get('sub'))
        if not user:
            return None
            
        # Update last activity
        user.last_active = datetime.utcnow()
        db.commit()
        
        return user
        
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        return None

async def require_auth(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Require authentication for protected routes"""
    if not current_user:
        # Don't redirect login/auth related paths
        path = request.url.path
        if path.startswith("/login") or path.startswith("/api/auth"):
            return None
            
        # Check rate limiting for protected routes
        client_ip = request.client.host
        if is_rate_limited(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Please try again later."
            )
            
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Authentication required",
            headers={"Location": f"/unauthorized?next={request.url.path}"}
        )
        
    return current_user

# Cleanup task for rate limiting data
def cleanup_rate_limiting():
    """Clean up old rate limiting data"""
    now = datetime.now()
    for ip in list(login_attempts.keys()):
        login_attempts[ip] = [
            attempt for attempt in login_attempts[ip]
            if now - attempt[0] < timedelta(seconds=LOCKOUT_DURATION)
        ]
        if not login_attempts[ip]:
            del login_attempts[ip]

# Run cleanup periodically
import threading
def cleanup_thread():
    while True:
        time.sleep(300)  # Run every 5 minutes
        cleanup_rate_limiting()

threading.Thread(target=cleanup_thread, daemon=True).start() 