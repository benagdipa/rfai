from sqlalchemy import Column, Integer, JSON, String, DateTime, Index, ForeignKey
from sqlalchemy.orm import validates
from utils.database import Base
from utils.logger import logger
from datetime import datetime
from typing import Dict, Any, Optional
import json

class DynamicData(Base):
    """Model representing dynamic data collected and processed by the multi-agent system."""
    
    __tablename__ = "dynamic_data"

    # Primary fields
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, doc="Unique identifier for the record")
    timestamp = Column(DateTime, index=True, nullable=False, doc="Timestamp of data collection or processing")
    identifier = Column(String, index=True, nullable=False, doc="Unique identifier for the data source or context")
    data = Column(JSON, nullable=False, doc="Dynamic JSON data payload")

    # Metadata fields
    agent_id = Column(String, nullable=True, doc="ID of the agent that created or last modified this record")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, doc="Record creation timestamp")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, doc="Last update timestamp")

    # Define composite index for efficient querying
    __table_args__ = (
        Index("ix_dynamic_data_identifier_timestamp_agent", "identifier", "timestamp", "agent_id"),
    )

    @validates("data")
    def validate_data(self, key: str, value: Any) -> Dict[str, Any]:
        """
        Validate and normalize the JSON data field.

        Args:
            key (str): Field name ('data').
            value (Any): Value to validate.

        Returns:
            Dict[str, Any]: Validated JSON data.

        Raises:
            ValueError: If data is not JSON-serializable.
        """
        try:
            if isinstance(value, (dict, list)):
                return value
            elif isinstance(value, str):
                return json.loads(value)
            else:
                raise ValueError("Data must be a dict, list, or JSON string")
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"Invalid JSON data for {self.identifier}: {e}")
            raise ValueError(f"Invalid JSON data: {e}")

    @validates("identifier")
    def validate_identifier(self, key: str, value: str) -> str:
        """
        Validate the identifier field.

        Args:
            key (str): Field name ('identifier').
            value (str): Value to validate.

        Returns:
            str: Validated identifier.

        Raises:
            ValueError: If identifier is empty or too long.
        """
        if not value or len(value.strip()) == 0:
            logger.error("Identifier cannot be empty")
            raise ValueError("Identifier cannot be empty")
        if len(value) > 255:
            logger.warning(f"Identifier truncated from {len(value)} to 255 characters")
            return value[:255]
        return value

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the model instance to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the instance.
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "identifier": self.identifier,
            "data": self.data,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], agent_id: Optional[str] = None) -> "DynamicData":
        """
        Create a DynamicData instance from a dictionary.

        Args:
            data (Dict[str, Any]): Data dictionary with fields.
            agent_id (str, optional): ID of the agent creating the instance.

        Returns:
            DynamicData: New instance of the model.
        """
        try:
            instance = cls(
                timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
                identifier=data["identifier"],
                data=data["data"],
                agent_id=agent_id or data.get("agent_id")
            )
            return instance
        except Exception as e:
            logger.error(f"Failed to create DynamicData from dict: {e}")
            raise ValueError(f"Invalid data for DynamicData: {e}")

if __name__ == "__main__":
    # Test the model
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as OrmSession
    from utils.database import Base, get_db

    # Setup test database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    with OrmSession(engine) as session:
        # Test creation
        test_data = {
            "timestamp": "2023-01-01T12:00:00",
            "identifier": "test_data",
            "data": {"value": 10, "load": 5},
            "agent_id": "test_agent_1"
        }
        record = DynamicData.from_dict(test_data)
        session.add(record)
        session.commit()

        # Test retrieval
        retrieved = session.query(DynamicData).first()
        print("Retrieved:", retrieved.to_dict())

        # Test validation
        try:
            invalid_record = DynamicData(identifier="", data="invalid")
            session.add(invalid_record)
            session.commit()
        except ValueError as e:
            print(f"Validation Error: {e}")