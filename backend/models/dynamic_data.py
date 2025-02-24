from sqlalchemy import Column, Integer, JSON, String, DateTime
from utils.database import Base

class DynamicData(Base):
    __tablename__ = "dynamic_data"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    identifier = Column(String, index=True)
    data = Column(JSON)
