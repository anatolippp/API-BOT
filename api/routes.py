import logging
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db import repository, database
from db.serializers.telegram_user import TelegramUserStart, TelegramUserUpdate
from db.serializers.schedule import ScheduleCreate
from db.models.telegram_user import TelegramUser
from auth.keycloak_auth import KeycloakBearerAuth
from celery import current_app
from managers.telegram_manager import revoke_tasks_for_chat, restart_worker_pool
from config.logging_config import setup_logging

setup_logging()

logger = logging.getLogger("api.routes")

# for test auth
auth_router = APIRouter()


@auth_router.get("/protected", tags=["Auth"], summary="Example for keycloak authentication")
async def protected_route(credentials=Depends(KeycloakBearerAuth())):
    logger.info("Protected route called")
    return {"message": "You are authorized", "token": credentials.credentials}


# for telegram router
telegram_router = APIRouter()


@telegram_router.post("/start", tags=["Telegram Bot"], summary="Start bot for user")
async def start_bot(user_data: TelegramUserStart, db: Session = Depends(database.get_db)):
    try:
        chat_id = user_data.chat_id
        message_text = user_data.message_text
        default_interval = 5

        data = user_data.dict()
        data.setdefault("interval", default_interval)

        user = db.query(TelegramUser).filter_by(chat_id=chat_id).first()
        if user:
            user.active = True
            db.commit()
            db.refresh(user)
        else:
            user = repository.create_telegram_user(data, db)

        repository.create_or_update_periodic_task(
            db=db,
            chat_id=user.chat_id,
            text=user.message_text,
            interval_seconds=user.interval,
            schedule_type="interval",
            schedule_value={}
        )
        from sqlalchemy_celery_beat.models import PeriodicTaskChanged
        PeriodicTaskChanged.update_from_session(db)
        from celery import current_app
        revoke_tasks_for_chat(current_app, user.chat_id, ["scheduled", "reserved"])
        return {"status": "Bot started", "chat_id": user.chat_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@telegram_router.post("/stop", tags=["Telegram Bot"], summary="Stop bot for user")
async def stop_bot(chat_id: int, db: Session = Depends(database.get_db)):
    chat_id_str = str(chat_id)
    logger.info(f"Attempting to stop bot for chat_id: {chat_id_str}")

    user = db.query(TelegramUser).filter(TelegramUser.chat_id == chat_id_str).first()
    if user:
        user.active = False
        db.commit()
        logger.info(f"User {chat_id_str} deactivated")
    else:
        logger.warning(f"User {chat_id_str} not found")

    disabled = repository.disable_periodic_task(db, chat_id_str)
    if not disabled:
        logger.warning(f"Periodic task periodic_{chat_id_str} not found")

    revoke_tasks_for_chat(current_app, chat_id_str, ["scheduled", "active", "reserved"])

    return {"status": "Bot stopped!", "chat_id": chat_id_str}


@telegram_router.get("/users", tags=["Telegram Bot"], summary="Get all users")
async def get_all_users(db: Session = Depends(database.get_db)):
    return repository.get_all_telegram_users(db)


@telegram_router.put("/settings", tags=["Telegram Bot"], summary="Change user options")
async def update_settings(chat_id: str, settings: TelegramUserUpdate, db: Session = Depends(database.get_db)):
    update_data = settings.dict(exclude_unset=True)
    user = repository.update_telegram_user(chat_id, update_data, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.active = True
    db.commit()
    db.refresh(user)

    schedule_type = settings.schedule_type if settings.schedule_type else "interval"
    schedule_value = settings.schedule_value

    if user.active:
        repository.delete_periodic_task_by_chat_id(db, user.chat_id)
        repository.create_or_update_periodic_task(
            db=db,
            chat_id=user.chat_id,
            text=user.message_text,
            interval_seconds=user.interval if schedule_type == "interval" else None,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
        )
        from sqlalchemy_celery_beat.models import PeriodicTaskChanged
        PeriodicTaskChanged.update_from_session(db)

        from celery import current_app
        revoke_tasks_for_chat(current_app, user.chat_id, ["scheduled", "active", "reserved"])
        restart_worker_pool(current_app)

    return {"status": "Updated", "user": user.chat_id}


# Schedule route
scheduler_router = APIRouter()


@scheduler_router.post("/create", tags=["Scheduler"], summary="Set schedule for a user's periodic task")
async def create_schedule(schedule: ScheduleCreate, db: Session = Depends(database.get_db)):
    user = db.query(TelegramUser).filter_by(chat_id=schedule.chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Run /start first.")

    user.message_text = schedule.text
    if schedule.schedule_type == "interval":
        user.interval = schedule.interval_seconds
    db.commit()
    db.refresh(user)

    repository.create_or_update_periodic_task(
        db=db,
        chat_id=user.chat_id,
        text=user.message_text,
        interval_seconds=user.interval if schedule.schedule_type == "interval" else None,
        schedule_type=schedule.schedule_type,
        schedule_value=schedule.schedule_value
    )

    from sqlalchemy_celery_beat.models import PeriodicTaskChanged
    PeriodicTaskChanged.update_from_session(db)

    revoke_tasks_for_chat(current_app, user.chat_id, ["scheduled", "active", "reserved"])
    restart_worker_pool(current_app)

    return {"status": "Schedule crated", "chat_id": user.chat_id}


class ScheduleUpdate(BaseModel):
    interval_seconds: int = None
    text: str = None
    schedule_type: str = "interval"
    schedule_value: dict = None


@scheduler_router.get("/list", tags=["Scheduler"], summary="List all tasks")
async def list_tasks(db: Session = Depends(database.get_db)):
    tasks = repository.list_periodic_tasks(db)
    return tasks


@scheduler_router.put("/update/{task_id}", tags=["Scheduler"], summary="Update PeriodicTask")
async def update_task(task_id: int, updates: ScheduleUpdate, db: Session = Depends(database.get_db)):
    task = repository.update_periodic_task(
        db,
        task_id,
        interval_seconds=updates.interval_seconds if updates.schedule_type == "interval" else None,
        text=updates.text,
        schedule_type=updates.schedule_type,
        schedule_value=updates.schedule_value
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "Task update", "task_id": task.id}


@scheduler_router.delete("/delete/{task_id}", tags=["Scheduler"], summary="Delete task by ID")
async def delete_task(task_id: int, db: Session = Depends(database.get_db)):
    success = repository.delete_periodic_task_by_id(db, task_id)
    if success:
        return {"status": "Schedule delete", "task_id": task_id}
    return {"error": "Schedule not found"}
