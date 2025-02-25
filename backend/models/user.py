from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.orm import validates
from utils.database import Base
from utils.logger import logger
from passlib.context import CryptContext
from datetime import datetime
from typing import Dict, Any, Optional
import re

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    """Model representing users of the multi-agent system with authentication credentials."""
    
    __tablename__ = "users"

    # Primary fields
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, doc="Unique identifier for the user")
    username = Column(String, unique=True, index=True, nullable=False, doc="Unique username for the user")
    hashed_password = Column(String, nullable=False, doc="Hashed user password")

    # Metadata fields
    email = Column(String, unique=True, nullable=True, doc="User's email address")
    full_name = Column(String, nullable=True, doc="User's full name")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, doc="Timestamp when the user was created")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, doc="Last update timestamp")
    is_active = Column(Boolean, default=True, nullable=False, doc="Whether the user account is active")
    last_login_at = Column(DateTime, nullable=True, doc="Timestamp of the user's last login")

    # Define composite index for efficient querying
    __table_args__ = (
        Index("ix_users_username_created_at", "username", "created_at"),
    )

    @validates("username")
    def validate_username(self, key: str, value: str) -> str:
        """
        Validate the username field.

        Args:
            key (str): Field name ('username').
            value (str): Value to validate.

        Returns:
            str: Validated username.

        Raises:
            ValueError: If username is invalid.
        """
        if not value or len(value.strip()) == 0:
            logger.error("Username cannot be empty")
            raise ValueError("Username cannot be empty")
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", value):
            logger.error(f"Invalid username format: {value}")
            raise ValueError("Username must be 3-20 alphanumeric characters or underscores")
        if len(value) > 255:
            logger.warning(f"Username truncated from {len(value)} to 255 characters")
            return value[:255]
        return value

    @validates("email")
    def validate_email(self, key: str, value: Optional[str]) -> Optional[str]:
        """
        Validate the email field.

        Args:
            key (str): Field name ('email').
            value (str, optional): Value to validate.

        Returns:
            str: Validated email.

        Raises:
            ValueError: If email is invalid.
        """
        if value is None:
            return None
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", value):
            logger.error(f"Invalid email format: {value}")
            raise ValueError("Invalid email format")
        if len(value) > 255:
            logger.warning(f"Email truncated from {len(value)} to 255 characters")
            return value[:255]
        return value

    def verify_password(self, password: str) -> bool:
        """
        Verify the provided password against the stored hash.

        Args:
            password (str): Plain-text password to verify.

        Returns:
            bool: True if password matches, False otherwise.
        """
        try:
            verified = pwd_context.verify(password, self.hashed_password)
            logger.debug(f"Password verification for {self.username}: {'success' if verified else 'failure'}")
            return verified
        except Exception as e:
            logger.error(f"Password verification failed for {self.username}: {e}")
            return False

    def set_password(self, password: str) -> None:
        """
        Set and hash the user's password.

        Args:
            password (str): Plain-text password to hash.

        Raises:
            ValueError: If password does not meet complexity requirements.
        """
        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[0-9]", password):
            logger.error(f"Password for {self.username} does not meet complexity requirements")
            raise ValueError("Password must be at least 8 characters with an uppercase letter and a number")
        try:
            self.hashed_password = pwd_context.hash(password)
            logger.debug(f"Password set for {self.username}")
        except Exception as e:
            logger.error(f"Failed to hash password for {self.username}: {e}")
            raise ValueError(f"Password hashing failed: {e}")

    def update_last_login(self) -> None:
        """Update the last_login_at field to the current timestamp."""
        self.last_login_at = datetime.utcnow()
        logger.debug(f"Updated last login for {self.username} to {self.last_login_at}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the model instance to a dictionary (excluding sensitive data).

        Returns:
            Dict[str, Any]: Dictionary representation of the instance.
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """
        Create a User instance from a dictionary.

        Args:
            data (Dict[str, Any]): Data dictionary with fields.

        Returns:
            User: New instance of the model.
        """
        try:
            instance = cls(username=data["username"])
            instance.set_password(data["password"])
            instance.email = data.get("email")
            instance.full_name = data.get("full_name")
            instance.is_active = data.get("is_active", True)
            if "created_at" in data:
                instance.created_at = datetime.fromisoformat(data["created_at"])
            if "last_login_at" in data:
                instance.last_login_at = datetime.fromisoformat(data["last_login_at"])
            logger.debug(f"User created from dict: {instance.username}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create User from dict: {e}")
            raise ValueError(f"Invalid data for User: {e}")

if __name__ == "__main__":
    # Test the model
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as OrmSession
    from utils.database import Base

    # Setup test database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    with OrmSession(engine) as session:
        # Test creation
        test_data = {
            "username": "testuser",
            "password": "Test1234",
            "email": "test@example.com",
            "full_name": "Test User"
        }
        user = User.from_dict(test_data)
        session.add(user)
        session.commit()

        # Test retrieval
        retrieved = session.query(User).first()
        print("Retrieved:", retrieved.to_dict())

        # Test password verification
        print("Password Verify:", retrieved.verify_password("Test1234"))

        # Test validation
        try:
            invalid_user = User(username="ab", password="weak")
            session.add(invalid_user)
            session.commit()
        except ValueError as e:
            print(f"Validation Error: {e}")