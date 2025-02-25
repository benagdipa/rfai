from sqlalchemy import Column, Integer, String, Enum, DateTime, Index, ForeignKey
from sqlalchemy.orm import validates
from utils.database import Base
from utils.logger import logger
from datetime import datetime
from typing import Dict, Any, Optional
import enum

# Define severity levels as an Enum
class SeverityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Issue(Base):
    """Model representing issues detected by the multi-agent system."""
    
    __tablename__ = "issues"

    # Primary fields
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, doc="Unique identifier for the issue")
    identifier = Column(String, index=True, nullable=False, doc="Unique identifier linking to the data source or context")
    description = Column(String, nullable=False, doc="Description of the detected issue")
    severity = Column(Enum(SeverityLevel), nullable=False, default=SeverityLevel.MEDIUM, doc="Severity level of the issue")

    # Metadata fields
    agent_id = Column(String, nullable=True, doc="ID of the agent that detected this issue")
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, doc="Timestamp when the issue was detected")
    resolved_at = Column(DateTime, nullable=True, doc="Timestamp when the issue was resolved")
    status = Column(String, default="open", nullable=False, doc="Current status of the issue (e.g., 'open', 'resolved')")

    # Define composite index for efficient querying
    __table_args__ = (
        Index("ix_issues_identifier_detected_at", "identifier", "detected_at"),
    )

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

    @validates("description")
    def validate_description(self, key: str, value: str) -> str:
        """
        Validate the description field.

        Args:
            key (str): Field name ('description').
            value (str): Value to validate.

        Returns:
            str: Validated description.

        Raises:
            ValueError: If description is empty.
        """
        if not value or len(value.strip()) == 0:
            logger.error("Description cannot be empty")
            raise ValueError("Description cannot be empty")
        return value

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        """
        Validate the status field.

        Args:
            key (str): Field name ('status').
            value (str): Value to validate.

        Returns:
            str: Validated status.

        Raises:
            ValueError: If status is invalid.
        """
        valid_statuses = {"open", "resolved", "in_progress"}
        if value.lower() not in valid_statuses:
            logger.warning(f"Invalid status: {value}; defaulting to 'open'")
            return "open"
        return value.lower()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the model instance to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the instance.
        """
        return {
            "id": self.id,
            "identifier": self.identifier,
            "description": self.description,
            "severity": self.severity.value if self.severity else None,
            "agent_id": self.agent_id,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], agent_id: Optional[str] = None) -> "Issue":
        """
        Create an Issue instance from a dictionary.

        Args:
            data (Dict[str, Any]): Data dictionary with fields.
            agent_id (str, optional): ID of the agent detecting the issue.

        Returns:
            Issue: New instance of the model.
        """
        try:
            instance = cls(
                identifier=data["identifier"],
                description=data["description"],
                severity=data.get("severity", "medium"),
                agent_id=agent_id or data.get("agent_id"),
                detected_at=datetime.fromisoformat(data["detected_at"]) if data.get("detected_at") else datetime.utcnow(),
                resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
                status=data.get("status", "open")
            )
            return instance
        except Exception as e:
            logger.error(f"Failed to create Issue from dict: {e}")
            raise ValueError(f"Invalid data for Issue: {e}")

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
            "identifier": "test_data",
            "description": "Performance degradation detected",
            "severity": "medium",
            "agent_id": "issue_detection_agent_1"
        }
        issue = Issue.from_dict(test_data)
        session.add(issue)
        session.commit()

        # Test retrieval
        retrieved = session.query(Issue).first()
        print("Retrieved:", retrieved.to_dict())

        # Test validation
        try:
            invalid_issue = Issue(identifier="", description="")
            session.add(invalid_issue)
            session.commit()
        except ValueError as e:
            print(f"Validation Error: {e}")