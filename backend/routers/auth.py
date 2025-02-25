from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from utils.database import get_db
from utils.security import create_access_token, create_refresh_token, decode_token, get_current_user
from utils.logger import logger
from models.user import User
from pydantic import BaseModel, validator
from typing import Dict, Optional
import re

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic models for request/response validation
class UserCreate(BaseModel):
    username: str
    password: str

    @validator("username")
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", v):
            raise ValueError("Username must be 3-20 alphanumeric characters or underscores")
        return v

    @validator("password")
    def password_complexity(cls, v):
        if len(v) < 8 or not re.search(r"[A-Z]", v) or not re.search(r"[0-9]", v):
            raise ValueError("Password must be at least 8 characters with an uppercase letter and a number")
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Signup endpoint
@router.post("/signup", response_model=TokenResponse)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user and return access and refresh tokens.

    Args:
        user (UserCreate): User data (username, password).
        db (Session): Database session.

    Returns:
        TokenResponse: Access and refresh tokens.

    Raises:
        HTTPException: If username exists or token creation fails.
    """
    try:
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            logger.warning(f"Signup attempt with existing username: {user.username}")
            raise HTTPException(status_code=400, detail="Username already exists")

        new_user = User(username=user.username)
        new_user.set_password(user.password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"User created: {user.username}")

        access_token = create_access_token({"sub": user.username})
        refresh_token = create_refresh_token({"sub": user.username})

        if not access_token or not refresh_token:
            logger.error("Token creation failed during signup")
            raise HTTPException(status_code=500, detail="Token creation failed")

        return {"access_token": access_token, "refresh_token": refresh_token}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Signup failed for {user.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signup")

# Login endpoint (token generation)
@router.post("/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate a user and return access and refresh tokens.

    Args:
        form_data (OAuth2PasswordRequestForm): Username and password form data.
        db (Session): Database session.

    Returns:
        TokenResponse: Access and refresh tokens.

    Raises:
        HTTPException: If credentials are invalid or token creation fails.
    """
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not user.verify_password(form_data.password):
            logger.warning(f"Login attempt failed for {form_data.username}: invalid credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        access_token = create_access_token({"sub": form_data.username})
        refresh_token = create_refresh_token({"sub": form_data.username})

        if not access_token or not refresh_token:
            logger.error(f"Token creation failed for {form_data.username}")
            raise HTTPException(status_code=500, detail="Token creation failed")

        logger.info(f"User logged in: {form_data.username}")
        return {"access_token": access_token, "refresh_token": refresh_token}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Login failed for {form_data.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during login")

# Refresh token endpoint
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh an access token using a refresh token.

    Args:
        request (RefreshTokenRequest): Refresh token data.
        db (Session): Database session.

    Returns:
        TokenResponse: New access token.

    Raises:
        HTTPException: If refresh token is invalid or user not found.
    """
    try:
        payload = decode_token(request.refresh_token, scope="refresh")
        if not payload or "sub" not in payload:
            logger.warning("Invalid refresh token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        username = payload["sub"]
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.warning(f"User not found for refresh token: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )

        new_access_token = create_access_token({"sub": username})
        if not new_access_token:
            logger.error(f"Access token creation failed during refresh for {username}")
            raise HTTPException(status_code=500, detail="Token creation failed")

        logger.info(f"Access token refreshed for {username}")
        return {"access_token": new_access_token}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Refresh token failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during token refresh")

# Get current user info (example utility endpoint)
@router.get("/me")
async def get_me(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieve information about the current authenticated user.

    Args:
        current_user (str): User identifier from token.
        db (Session): Database session.

    Returns:
        dict: User information.

    Raises:
        HTTPException: If user not found.
    """
    try:
        user = db.query(User).filter(User.username == current_user).first()
        if not user:
            logger.warning(f"Authenticated user not found: {current_user}")
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.debug(f"User info retrieved: {current_user}")
        return {"username": user.username}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to retrieve user info for {current_user}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    # Test the endpoints (requires a running FastAPI app)
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test signup
    signup_response = client.post("/auth/signup", json={"username": "testuser", "password": "Test1234"})
    print("Signup Response:", signup_response.json())
    
    # Test login
    login_response = client.post("/auth/token", data={"username": "testuser", "password": "Test1234"})
    print("Login Response:", login_response.json())