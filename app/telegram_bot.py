import os
import logging
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_API_URL = os.getenv("WEB_API_URL", "http://app:8000")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    payload = {"chat_id": str(chat_id)}

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{WEB_API_URL}/bot/start", json=payload)
        if resp.status_code == 200:
            await message.answer("Bot active!")
        else:
            await message.answer(f"Start error: {resp.text}")


@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    chat_id = message.chat.id
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{WEB_API_URL}/bot/stop", params={"chat_id": chat_id})
        if resp.status_code == 200:
            await message.answer("Bot stopped!")
        else:
            await message.answer(f"Stop error: {resp.text}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
