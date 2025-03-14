from fastapi import APIRouter, Request, Response, HTTPException, Depends, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth import AuthService
from app.services.email_service import ResetCodeService
from app.schemas.auth import UserCreate, Token, UserResponse
from app.core.config import settings
import secrets

# Create two routers: one for web routes and one for API routes
web_router = APIRouter(tags=["web"])
api_router = APIRouter(prefix="/api/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")
reset_code_service = ResetCodeService()

# Web routes
@web_router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@web_router.get("/unauthorized", response_class=HTMLResponse)
async def unauthorized_page(request: Request, next: str = "/dashboard"):
    return templates.TemplateResponse("unauthorized.html", {"request": request, "next": next})

@web_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/dashboard"):
    return templates.TemplateResponse("login.html", {"request": request, "next": next})

@web_router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, next: str = "/dashboard"):
    return templates.TemplateResponse("signup.html", {"request": request, "next": next})

@web_router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

@web_router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Display forgot password form"""
    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request}
    )

@web_router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle forgot password form submission"""
    try:
        # Find user by email
        auth_service = AuthService(db)
        user = auth_service.get_user_by_email(email)
        if not user:
            return templates.TemplateResponse(
                "forgot_password.html",
                {
                    "request": request,
                    "messages": [{"text": "If this email exists, you will receive a reset code.", "tags": "info"}]
                }
            )

        # Generate reset code
        reset_code = reset_code_service.generate_reset_code(email)

        return templates.TemplateResponse(
            "forgot_password.html",
            {
                "request": request,
                "reset_code": reset_code,
                "messages": [{"text": "Use this code to reset your password.", "tags": "success"}]
            }
        )

    except Exception as e:
        return templates.TemplateResponse(
            "forgot_password.html",
            {
                "request": request,
                "messages": [{"text": "An error occurred. Please try again.", "tags": "danger"}]
            }
        )

@web_router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Display reset password form"""
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request}
    )

@web_router.post("/reset-password", response_class=HTMLResponse)
async def reset_password(
    request: Request,
    email: str = Form(...),
    reset_code: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle password reset"""
    try:
        if password != confirm_password:
            return templates.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "messages": [{"text": "Passwords do not match.", "tags": "danger"}]
                }
            )

        # Verify the reset code
        if not reset_code_service.verify_reset_code(email, reset_code):
            return templates.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "messages": [{"text": "Invalid or expired reset code.", "tags": "danger"}]
                }
            )

        # Find user and update password
        auth_service = AuthService(db)
        user = auth_service.get_user_by_email(email)
        if not user:
            return templates.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "messages": [{"text": "User not found.", "tags": "danger"}]
                }
            )

        if not auth_service.update_password(user.id, password):
            return templates.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "messages": [{"text": "Failed to update password. Please try again.", "tags": "danger"}]
                }
            )

        return RedirectResponse(
            url="/login",
            status_code=303,
            headers={"X-Message": "Password has been reset successfully. Please login."}
        )

    except Exception as e:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "messages": [{"text": "An error occurred. Please try again.", "tags": "danger"}]
            }
        )

# API routes
@api_router.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    next: str = Form("/dashboard"),
    db: Session = Depends(get_db)
):
    try:
        user_data = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name
        }
        
        auth_service = AuthService(db)
        user = auth_service.create_user(user_data)
        token = await auth_service.authenticate_user(email, password)
        
        if not token:
            return templates.TemplateResponse(
                "signup.html",
                {"request": request, "error": "Failed to authenticate after signup"},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        response = RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token.access_token}",
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return response
        
    except HTTPException as e:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": e.detail},
            status_code=e.status_code
        )
    except Exception as e:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/dashboard"),
    db: Session = Depends(get_db)
):
    try:
        auth_service = AuthService(db)
        token = await auth_service.authenticate_user(email, password)
        if not token:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Incorrect email or password"},
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        response = RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token.access_token}",
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return response
        
    except Exception as e:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_router.get("/chat", response_class=HTMLResponse)
async def chat_page(
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
        
        # Get connection ID from query params
        connection_id = request.query_params.get("connection")
        if not connection_id:
            return RedirectResponse(url="/dashboard", status_code=303)
            
        return templates.TemplateResponse("chat.html", {
            "request": request,
            "user": user
        })
    except HTTPException:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("access_token")
        return response 