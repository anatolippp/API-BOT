from pydantic import BaseModel, validator
from typing import Optional, Dict
from datetime import datetime


class ScheduleCreate(BaseModel):
    chat_id: str
    text: str
    schedule_type: str = "interval"
    interval_seconds: Optional[int] = None
    schedule_value: Optional[Dict] = {}

    @validator("schedule_type")
    def validate_schedule_type(cls, v):
        if v not in ["interval", "crontab", "clocked"]:
            raise ValueError("schedule_type must be 'interval', 'crontab' or 'clocked'")
        return v

    @validator("interval_seconds", always=True)
    def validate_interval(cls, v, values):
        if values.get("schedule_type") == "interval" and (v is None or v <= 0):
            raise ValueError("For interval schedule")
        return v

    @validator("schedule_value", always=True)
    def validate_schedule_value(cls, v, values):
        stype = values.get("schedule_type")
        if stype == "clocked":
            if not v or "clocked_time" not in v:
                raise ValueError("For clocked schedule, schedule_value must in ISO format")
            try:
                datetime.fromisoformat(v["clocked_time"])
            except Exception:
                raise ValueError("clocked_time must be ISO datetime stri")
        if stype == "crontab":
            required_fields = ["minute", "hour", "day_of_week", "day_of_month", "month_of_year", "timezone"]
            missing = [field for field in required_fields if field not in v]
            if missing:
                raise ValueError(f"For crontab schedule: {', '.join(missing)}")
        return v
