from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    
    username = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    reason = Column(String, nullable=True)
