from sqlalchemy import Column, Integer, String
from utils.database import Base

class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True)
    description = Column(String)
    severity = Column(String)
