from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from config.settings import settings
from utils.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta})
    try:
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        return None

def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except JWTError as e:
        logger.error(f"Token decoding failed: {e}")
        return None
