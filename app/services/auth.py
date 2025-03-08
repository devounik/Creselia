from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.models.user import User
from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.auth import Token
import logging

logger = logging.getLogger(__name__)

# JWT configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> User:
        """Get a user by email"""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            logger.debug(f"Found user with email {email}: {user is not None}")
            return user
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def create_user(self, user_data: dict) -> User:
        """Create a new user"""
        try:
            # Check if user already exists
            if self.get_user_by_email(user_data["email"]):
                logger.warning(f"User with email {user_data['email']} already exists")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Hash password and create user
            hashed_password = get_password_hash(user_data["password"])
            user = User(
                email=user_data["email"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                hashed_password=hashed_password
            )
            
            logger.info(f"Creating new user with email: {user_data['email']}")
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Successfully created user with ID: {user.id}")
            return user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            )

    async def authenticate_user(self, email: str, password: str) -> Token:
        """Authenticate a user and return access token"""
        try:
            user = self.get_user_by_email(email)
            if not user:
                logger.warning(f"Authentication failed: User not found for email {email}")
                return None
            
            if not verify_password(password, user.hashed_password):
                logger.warning(f"Authentication failed: Invalid password for email {email}")
                return None
            
            access_token = create_access_token(data={"sub": str(user.id)})
            logger.info(f"Successfully authenticated user: {email}")
            return Token(access_token=access_token, token_type="bearer")
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return None

    def get_current_user(self, token: str) -> User:
        """Get current user from token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: int = payload.get("sub")
            if user_id is None:
                logger.warning("Token payload does not contain user ID")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user = self.db.query(User).filter(User.id == user_id).first()
            if user is None:
                logger.warning(f"User not found for ID from token: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.debug(f"Successfully retrieved current user: {user.email}")
            return user
        except JWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) 