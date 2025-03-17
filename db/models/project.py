from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    creator_id = Column(Integer, ForeignKey("telegram_users.id"), nullable=False)

    creator = relationship("TelegramUser", back_populates="created_projects")
    members = relationship("ProjectMember", back_populates="project")
