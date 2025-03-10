from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from db.database import Base

class TelegramUser(Base):
    __tablename__ = "telegram_users"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String(255), unique=True, nullable=False)
    active = Column(Boolean, default=True)
    message_text = Column(String(255), default="Hello from DB", nullable=False)
    interval = Column(Integer, default=5, nullable=False)
    last_message_sent = Column(DateTime, server_default=func.now())
