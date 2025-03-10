from pydantic import BaseModel, Field
from typing import Optional, Dict

class TelegramUserBase(BaseModel):
    chat_id: str
    message_text: Optional[str] = "Hello!"
    interval: Optional[int] = 5

class TelegramUserCreate(TelegramUserBase):
    schedule_type: Optional[str] = "interval"
    schedule_value: Optional[Dict] = None

class TelegramUserUpdate(BaseModel):
    message_text: Optional[str] = None
    interval: Optional[int] = None
    schedule_type: Optional[str] = None
    schedule_value: Optional[Dict] = None

class TelegramUserStart(BaseModel):
    chat_id: str = Field(..., description="ID user")
    message_text: str = Field("Hello! Have a nice day", description="basic")
