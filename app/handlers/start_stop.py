import httpx
import logging
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
import os

logger = logging.getLogger(__name__)

router = Router()

WEB_API_URL = os.getenv("WEB_API_URL", "http://app:8000")


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    payload = {"chat_id": str(chat_id)}

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{WEB_API_URL}/bot/start", json=payload)
        if resp.status_code == 200:
            await message.answer("Bot active!\nUse /go, for start Google-search.")
        else:
            await message.answer(f"Start error: {resp.text}")


@router.message(Command("stop"))
async def cmd_stop(message: types.Message):
    chat_id = message.chat.id
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{WEB_API_URL}/bot/stop", params={"chat_id": chat_id})
        if resp.status_code == 200:
            await message.answer("Bot stopped!")
        else:
            await message.answer(f"Stop error: {resp.text}")
