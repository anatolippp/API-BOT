import os
import logging
import json
import asyncio
from datetime import datetime

from celery import shared_task
from aiogram import Bot
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models.telegram_user import TelegramUser
from config.logging_config import setup_logging
setup_logging()


logger = logging.getLogger("managers.telegram_manager")

@shared_task(name="managers.telegram_manager.send_message_task")
def send_message_task(chat_id: str, message_text: str = "Hello!"):
    logger.info(f"[Celery] Attempting send message to chat_id={chat_id}")


    db = SessionLocal()
    try:
        user = db.query(TelegramUser).filter(TelegramUser.chat_id == chat_id).first()
        if not user:
            logger.warning(f"User {chat_id} not found.")
            return
        if not user.active:
            logger.info(f"User {chat_id} is not active.")
            return

        message_text = user.message_text
    except Exception as e:
        logger.error(f"Error checking user status for {chat_id}: {e}")
        return
    finally:
        db.close()


    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

    async def _send():
        try:
            await bot.send_message(chat_id, message_text)
        except Exception as e:
            logger.error(f"Failed send message to {chat_id}: {e}")
        finally:
            await bot.session.close()

    loop.run_until_complete(_send())
    loop.close()


def revoke_tasks_for_chat(current_app, chat_id: str, states: list):
    for state in states:
        try:
            inspector = current_app.control.inspect(timeout=2) or {}
            tasks_dict = getattr(inspector, state)() or {}
            for worker, tasks in tasks_dict.items():
                for task in tasks:
                    req = task.get("request") if "request" in task else task
                    if req and "kwargs" in req:
                        try:
                            task_kwargs = json.loads(req["kwargs"])
                            if task_kwargs.get("chat_id") == chat_id:
                                task_id = req.get("id")
                                current_app.control.revoke(task_id, terminate=True, signal="SIGKILL")
                                logger.info(f"Revoked task {task_id} for chat_id {chat_id} from {state}")
                        except Exception as e:
                            logger.error(f"Error revoking task from {state}: {e}")
        except Exception as e:
            logger.error(f"Failed to inspect {state} tasks: {e}")


def restart_worker_pool(current_app):
    try:
        current_app.control.broadcast("pool_restart", reply=True, timeout=10)
        logger.info("Worker pool restart success")
    except Exception as e:
        logger.error(f"Error restart worker pool: {e}")
