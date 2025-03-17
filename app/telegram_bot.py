from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import os

from app.handlers.one_time_search import router as onetime_router
from app.handlers.go_menu import router as go_menu_router
from app.handlers.project import router as project_router
from app.handlers.start_stop import router as start_stop_router

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(onetime_router)
    dp.include_router(go_menu_router)
    dp.include_router(project_router)
    dp.include_router(start_stop_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
