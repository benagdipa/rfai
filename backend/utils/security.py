from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from config.settings import settings
from utils.logger import logger
from typing import Dict, Any, Optional, Union
from fastapi import HTTPException, status
from pydantic import BaseModel

# OAuth2 scheme for token retrieval
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Pydantic model for token payload (optional, for structure validation)
class TokenPayload(BaseModel):
    sub: str  # Subject (e.g., username or user ID)
    exp: Optional[int] = None  # Expiration timestamp
    iat: Optional[int] = None  # Issued-at timestamp
    scope: Optional[str] = None  # Token scope

# Helper function to validate settings
def _validate_settings() -> None:
    """Ensure required security settings are present."""
    required = ["SECRET_KEY", "ALGORITHM"]
    missing = [key for key in required if not hasattr(settings, key) or not getattr(settings, key)]
    if missing:
        logger.error(f"Missing required security settings: {missing}")
        raise ValueError(f"Missing security settings: {missing}")

# Create access token
def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    scope: str = "access"
) -> str:
    """
    Create a JWT access token with the provided data.

    Args:
        data (dict): Payload data (e.g., {"sub": "username"}).
        expires_delta (timedelta, optional): Token expiration duration. Default: 24 hours.
        scope (str): Token scope (e.g., "access", "refresh"). Default: "access".

    Returns:
        str: Encoded JWT token.

    Raises:
        HTTPException: If token creation fails.
    """
    _validate_settings()
    expires_delta = expires_delta or timedelta(hours=24)
    
    to_encode = data.copy()
    to_encode.update({
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),  # Issued-at time
        "scope": scope
    })
    
    try:
        token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.debug(f"Access token created for subject: {data.get('sub', 'unknown')}")
        return token
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create access token")

# Create refresh token
def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token with the provided data.

    Args:
        data (dict): Payload data (e.g., {"sub": "username"}).
        expires_delta (timedelta, optional): Token expiration duration. Default: 7 days.

    Returns:
        str: Encoded JWT refresh token.

    Raises:
        HTTPException: If token creation fails.
    """
    expires_delta = expires_delta or timedelta(days=7)
    return create_access_token(data, expires_delta, scope="refresh")

# Decode and validate token
def decode_token(token: str, scope: str = "access") -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token (str): JWT token to decode.
        scope (str): Expected token scope (e.g., "access", "refresh"). Default: "access".

    Returns:
        dict: Decoded payload if valid, None otherwise.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    _validate_settings()
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_scope = payload.get("scope", "access")
        
        if token_scope != scope:
            logger.warning(f"Invalid token scope: expected {scope}, got {token_scope}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid token scope: {token_scope}"
            )
        
        if "sub" not in payload:
            logger.warning("Token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject"
            )
        
        logger.debug(f"Token decoded successfully for subject: {payload['sub']}")
        return payload
    
    except jwt.ExpiredSignatureError:
        logger.warning(f"Token expired: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Token decoding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token decoding error"
        )

# Get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependency to extract the current user from an access token.

    Args:
        token (str): JWT token from OAuth2 scheme.

    Returns:
        str: User identifier (subject) from the token.

    Raises:
        HTTPException: If token is invalid or user cannot be extracted.
    """
    payload = decode_token(token, scope="access")
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return payload["sub"]

if __name__ == "__main__":
    # Test the security functions
    test_data = {"sub": "test_user"}
    
    # Create tokens
    access_token = create_access_token(test_data)
    refresh_token = create_refresh_token(test_data)
    print(f"Access Token: {access_token}")
    print(f"Refresh Token: {refresh_token}")
    
    # Decode tokens
    try:
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token, scope="refresh")
        print(f"Access Payload: {access_payload}")
        print(f"Refresh Payload: {refresh_payload}")
    except HTTPException as e:
        print(f"Decode Error: {e.detail}")