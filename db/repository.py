import json
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from db.models.telegram_user import TelegramUser
from sqlalchemy_celery_beat.models import (
    PeriodicTask,
    IntervalSchedule,
    CrontabSchedule,
    PeriodicTaskChanged,
    ModelBase,
)

logger = logging.getLogger(__name__)


def create_telegram_user(data: dict, db: Session):
    user = db.query(TelegramUser).filter_by(chat_id=data["chat_id"]).first()
    if not user:
        user = TelegramUser(**data)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_all_telegram_users(db: Session):
    return db.query(TelegramUser).all()


def update_telegram_user(chat_id: str, updates: dict, db: Session):
    user = db.query(TelegramUser).filter_by(chat_id=chat_id).first()
    if not user:
        return None
    for key, value in updates.items():
        if value is None:
            continue
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def create_or_update_periodic_task(db: Session, chat_id: str, text: str, interval_seconds: int = None,
                                   schedule_type: str = "interval", schedule_value: dict = None):
    if schedule_type == "interval":
        if interval_seconds is None:
            raise ValueError("interval_seconds is required for interval schedule")
        schedule_obj = db.query(IntervalSchedule).filter_by(every=interval_seconds, period="seconds").first()
        if not schedule_obj:
            schedule_obj = IntervalSchedule(every=interval_seconds, period="seconds")
            db.add(schedule_obj)
            db.commit()
            db.refresh(schedule_obj)
    elif schedule_type == "crontab":
        if not schedule_value:
            raise ValueError("schedule_value is required for crontab schedule")
        schedule_obj = db.query(CrontabSchedule).filter_by(
            minute=schedule_value.get("minute", "0"),
            hour=schedule_value.get("hour", "0"),
            day_of_week=schedule_value.get("day_of_week", "0"),
            day_of_month=schedule_value.get("day_of_month", "*"),
            month_of_year=schedule_value.get("month_of_year", "*"),
            timezone=schedule_value.get("timezone", "UTC")
        ).first()
        if not schedule_obj:
            schedule_obj = CrontabSchedule(
                minute=schedule_value.get("minute", "0"),
                hour=schedule_value.get("hour", "0"),
                day_of_week=schedule_value.get("day_of_week", "0"),
                day_of_month=schedule_value.get("day_of_month", "*"),
                month_of_year=schedule_value.get("month_of_year", "*"),
                timezone=schedule_value.get("timezone", "UTC")
            )
            db.add(schedule_obj)
            db.commit()
            db.refresh(schedule_obj)
    else:
        raise ValueError("Unsupported schedule type")

    name = f"periodic_{chat_id}"
    periodic_task = db.query(PeriodicTask).filter_by(name=name).first()
    if not periodic_task:
        periodic_task = PeriodicTask(
            name=name,
            task="managers.telegram_manager.send_message_task",
            one_off=False,
            enabled=True,
        )
        db.add(periodic_task)

    periodic_task.schedule_model = schedule_obj
    periodic_task.kwargs = json.dumps({"chat_id": chat_id, "message_text": text})
    periodic_task.enabled = True
    periodic_task.start_time = datetime.utcnow()

    db.commit()
    db.refresh(periodic_task)
    return periodic_task


def disable_periodic_task(db: Session, chat_id: str):
    name = f"periodic_{chat_id}"
    task = db.query(PeriodicTask).filter_by(name=name).first()
    if not task:
        logger.warning(f"Task {name} not found")
        return False

    logger.info(f"Task disable {name}")
    task.enabled = False
    db.commit()

    from sqlalchemy_celery_beat.models import PeriodicTaskChanged
    change_record = db.query(PeriodicTaskChanged).get(1)
    if not change_record:
        change_record = PeriodicTaskChanged(id=1, last_update=datetime.utcnow())
        db.add(change_record)
    else:
        change_record.last_update = datetime.utcnow()
    db.commit()
    return True


def list_periodic_tasks(db: Session):
    return db.query(PeriodicTask).all()


def update_periodic_task(db: Session, task_id: int, interval_seconds: int = None, text: str = None,
                         schedule_type: str = "interval", schedule_value: dict = None):
    task = db.query(PeriodicTask).filter_by(id=task_id).first()
    if not task:
        return None
    if schedule_type == "interval":
        if interval_seconds is None:
            raise ValueError("interval_seconds is required for interval schedule")
        schedule_obj = db.query(IntervalSchedule).filter_by(every=interval_seconds, period="seconds").first()
        if not schedule_obj:
            schedule_obj = IntervalSchedule(every=interval_seconds, period="seconds")
            db.add(schedule_obj)
            db.commit()
            db.refresh(schedule_obj)
    elif schedule_type == "crontab":
        if not schedule_value:
            raise ValueError("schedule_value is required for crontab schedule")
        schedule_obj = db.query(CrontabSchedule).filter_by(
            minute=schedule_value.get("minute", "0"),
            hour=schedule_value.get("hour", "0"),
            day_of_week=schedule_value.get("day_of_week", "0"),
            day_of_month=schedule_value.get("day_of_month", "*"),
            month_of_year=schedule_value.get("month_of_year", "*"),
            timezone=schedule_value.get("timezone", "UTC")
        ).first()
        if not schedule_obj:
            schedule_obj = CrontabSchedule(
                minute=schedule_value.get("minute", "0"),
                hour=schedule_value.get("hour", "0"),
                day_of_week=schedule_value.get("day_of_week", "0"),
                day_of_month=schedule_value.get("day_of_month", "*"),
                month_of_year=schedule_value.get("month_of_year", "*"),
                timezone=schedule_value.get("timezone", "UTC")
            )
            db.add(schedule_obj)
            db.commit()
            db.refresh(schedule_obj)
    else:
        raise ValueError("Unsupported schedule type")

    task.schedule_model = schedule_obj
    old_data = {}
    if task.kwargs:
        try:
            old_data = json.loads(task.kwargs)
        except:
            pass
    if text is not None:
        old_data.update({"message_text": text})
    task.kwargs = json.dumps(old_data)
    task.enabled = True
    db.commit()
    db.refresh(task)
    return task


def delete_periodic_task_by_chat_id(db: Session, chat_id: str):
    name = f"periodic_{chat_id}"
    task = db.query(PeriodicTask).filter_by(name=name).first()
    if task:
        interval_id = task.schedule_id
        db.delete(task)
        db.commit()
        remaining_tasks = db.query(PeriodicTask).filter_by(schedule_id=interval_id).count()
        if remaining_tasks == 0:
            from sqlalchemy_celery_beat.models import IntervalSchedule, CrontabSchedule
            schedule_obj = db.query(IntervalSchedule).filter_by(id=interval_id).first()
            if not schedule_obj:
                schedule_obj = db.query(CrontabSchedule).filter_by(id=interval_id).first()
            if schedule_obj:
                db.delete(schedule_obj)
                db.commit()
        return True
    return False


def delete_periodic_task_by_id(db: Session, task_id: int):
    task = db.query(PeriodicTask).filter_by(id=task_id).first()
    if task:
        interval_id = task.schedule_id
        db.delete(task)
        db.commit()
        remaining_tasks = db.query(PeriodicTask).filter_by(schedule_id=interval_id).count()
        if remaining_tasks == 0:
            from sqlalchemy_celery_beat.models import IntervalSchedule, CrontabSchedule
            interval_obj = db.query(IntervalSchedule).filter_by(id=interval_id).first()
            if not interval_obj:
                interval_obj = db.query(CrontabSchedule).filter_by(id=interval_id).first()
            if interval_obj:
                db.delete(interval_obj)
                db.commit()
        return True
    return False
