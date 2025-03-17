from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base

class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("telegram_users.id"), nullable=False)
    role = Column(String(50), default="admin")

    project = relationship("Project", back_populates="members")
    user = relationship("TelegramUser", back_populates="project_memberships")
