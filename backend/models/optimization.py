from sqlalchemy import Column, Integer, String
from utils.database import Base

class Optimization(Base):
    __tablename__ = "optimizations"
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True)
    proposal = Column(String)
