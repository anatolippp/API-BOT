import logging
import os
import httpx

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.handlers.states import GoMenuStates, ProjectMenuStates

WEB_API_URL = os.getenv("WEB_API_URL", "http://app:8000")
logger = logging.getLogger(__name__)
router = Router()


async def get_user_id_by_chat_id(chat_id: str) -> int | None:
    async with httpx.AsyncClient() as client:
        url = f"{WEB_API_URL}/api/bot/find_user_by_chat_id?chat_id={chat_id}"
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            if "error" not in data:
                return data["id"]
    return None


@router.message(Command("go"))
async def cmd_go(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="One-time request by key", callback_data="go_once"))
    builder.add(InlineKeyboardButton(text="Create project", callback_data="create_project"))
    builder.add(InlineKeyboardButton(text="Select project", callback_data="choose_project"))
    builder.adjust(1)

    await message.answer("Select action:", reply_markup=builder.as_markup())
    await state.set_state(GoMenuStates.main_menu)


@router.callback_query(GoMenuStates.main_menu, F.data == "create_project")
async def create_project_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the project name:")
    await state.set_state(GoMenuStates.creating_project_name)
    await callback.answer()


@router.message(GoMenuStates.creating_project_name)
async def process_create_project_name(message: types.Message, state: FSMContext):
    project_name = message.text
    chat_id = str(message.from_user.id)

    user_id = await get_user_id_by_chat_id(chat_id)
    if user_id is None:
        await message.answer("You are not registered (do /start).")
        await state.set_state(GoMenuStates.main_menu)
        return

    payload = {"name": project_name}
    async with httpx.AsyncClient() as client:
        url = f"{WEB_API_URL}/api/projects/create?user_id={user_id}"
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            project_id = data["project_id"]
            await state.update_data(project_id=project_id)
            await message.answer(
                f"Project created (ID={project_id}). Enter members (@username) separated by space:"
            )
            await state.set_state(GoMenuStates.adding_members)
        else:
            await message.answer("Project creation failed.")
            await state.set_state(GoMenuStates.main_menu)


@router.message(GoMenuStates.adding_members)
async def process_adding_members(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    project_id = user_data.get("project_id")
    splitted = message.text.split()

    payload = {"usernames": splitted}
    async with httpx.AsyncClient() as client:
        url = f"{WEB_API_URL}/api/projects/{project_id}/add_members"
        r = await client.post(url, json=payload)
        if r.status_code == 200:
            d = r.json()
            added = d["added"]
            await message.answer(f"Users added: {added}")
        else:
            await message.answer("Error adding users.")

    await message.answer(
        "The project is ready. You can make queries here, /history, /schedule."
        "\nEnter the command /projectsearch to start search."
    )
    await state.set_state(ProjectMenuStates.menu)


@router.callback_query(GoMenuStates.main_menu, F.data == "choose_project")
async def choose_project_callback(callback: types.CallbackQuery, state: FSMContext):
    chat_id = str(callback.from_user.id)
    user_id = await get_user_id_by_chat_id(chat_id)
    if user_id is None:
        await callback.message.answer("You are not registered (do /start).")
        await callback.answer()
        return

    async with httpx.AsyncClient() as client:
        url = f"{WEB_API_URL}/api/users/{user_id}/projects"
        resp = await client.get(url)
        if resp.status_code != 200:
            await callback.message.answer("Mistake getting projects.")
            await callback.answer()
            return
        projects = resp.json()
        if not projects:
            await callback.message.answer("No projects found.")
            await callback.answer()
            return

        builder = InlineKeyboardBuilder()
        for p in projects:
            cb_data = f"selectproj:{p['id']}"
            builder.add(InlineKeyboardButton(text=p["name"], callback_data=cb_data))
        builder.adjust(1)

        await callback.message.answer("YOUR PROJECTS:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("selectproj:"))
async def callback_select_project(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    project_id = parts[1]
    await state.update_data(project_id=project_id)
    await callback.message.answer(
        f"Project {project_id} selected.\n"
        "Use /projectsearch, /history, /schedule."
    )
    await state.set_state(ProjectMenuStates.menu)
    await callback.answer()
