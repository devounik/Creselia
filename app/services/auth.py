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
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            logger.debug(f"Found user with ID {user_id}: {user is not None}")
            return user
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            logger.debug(f"Found user with email {email}: {user is not None}")
            return user
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_current_user(self, token: str) -> User:
        """Get the current user from a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                logger.warning("Token payload missing 'sub' claim")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user = self.db.query(User).filter(User.id == user_id).first()
            if user is None:
                logger.warning(f"No user found for ID {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return user
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Unexpected error in get_current_user: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication error",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def authenticate_user(self, email: str, password: str) -> Optional[Token]:
        """Authenticate a user and return a JWT token"""
        try:
            user = self.get_user_by_email(email)
            if not user:
                logger.warning(f"Authentication failed: User not found for email {email}")
                return None
            
            if not verify_password(password, user.hashed_password):
                logger.warning(f"Authentication failed: Invalid password for email {email}")
                return None

            # Create access token
            access_token = create_access_token(
                data={"sub": str(user.id)},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            logger.info(f"Successfully authenticated user: {email}")
            return Token(access_token=access_token, token_type="bearer")
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    def create_user(self, user_data: Dict) -> User:
        """Create a new user"""
        try:
            # Check if user already exists
            if self.get_user_by_email(user_data["email"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create new user
            hashed_password = get_password_hash(user_data["password"])
            user = User(
                email=user_data["email"],
                hashed_password=hashed_password,
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", "")
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Created new user: {user.email}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user"
            )

    def update_password(self, user_id: int, new_password: str) -> bool:
        """Update a user's password"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"Password update failed: User not found with ID {user_id}")
                return False
            
            hashed_password = get_password_hash(new_password)
            user.hashed_password = hashed_password
            self.db.commit()
            
            logger.info(f"Successfully updated password for user ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            self.db.rollback()
            return False 