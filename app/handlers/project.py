import logging
import os
import io
import json
import xlsxwriter
import httpx
from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, FSInputFile

from app.handlers.states import (
    GoMenuStates,
    ProjectMenuStates,
    ProjectSearchStates,
    ScheduleState
)

from config.countries import COUNTRIES
from config.languages import LANGUAGES
from config.domains import DOMAINS

from services.openai_service import analyze_results_with_openai

logger = logging.getLogger(__name__)
router = Router()

WEB_API_URL = os.getenv("WEB_API_URL", "http://app:8000")


async def get_user_id_by_chat_id(chat_id: str) -> int | None:
    async with httpx.AsyncClient() as client:
        url = f"{WEB_API_URL}/api/bot/find_user_by_chat_id?chat_id={chat_id}"
        r = await client.get(url)
        if r.status_code == 200:
            data = r.json()
            if "error" not in data:
                return data["id"]
    return None


project_search_cache = {}


@router.message(ProjectMenuStates.menu, Command("projectsearch"))
async def cmd_project_search(message: types.Message, state: FSMContext):
    await message.answer("Enter your search query.")
    await state.set_state(ProjectSearchStates.waiting_for_query)


@router.message(ProjectSearchStates.waiting_for_query)
async def project_query_input(message: types.Message, state: FSMContext):
    await state.update_data(search_query=message.text)
    builder = InlineKeyboardBuilder()
    for emoji_flag, country_name, cb_data in COUNTRIES:
        button_text = f"{emoji_flag} {country_name}"
        builder.add(InlineKeyboardButton(text=button_text, callback_data=cb_data))
    builder.adjust(3)
    await message.answer("Select country:", reply_markup=builder.as_markup())
    await state.set_state(ProjectSearchStates.waiting_for_country)


@router.callback_query(ProjectSearchStates.waiting_for_country)
async def project_country(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(country=callback.data)
    await callback.message.edit_text(f"Country selected: {callback.data}")
    builder = InlineKeyboardBuilder()
    for lang_code, lang_label, cb_data in LANGUAGES:
        text_btn = f"{lang_label} ({lang_code})"
        builder.add(InlineKeyboardButton(text=text_btn, callback_data=cb_data))
    builder.adjust(2)
    await callback.message.answer("Select language:", reply_markup=builder.as_markup())
    await state.set_state(ProjectSearchStates.waiting_for_language)
    await callback.answer()


@router.callback_query(ProjectSearchStates.waiting_for_language)
async def project_language(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(language=callback.data)
    await callback.message.edit_text(f"Language selected: {callback.data}")
    builder = InlineKeyboardBuilder()
    for domain_lbl, domain_cb in DOMAINS:
        builder.add(InlineKeyboardButton(text=domain_lbl, callback_data=domain_cb))
    builder.adjust(2)
    await callback.message.answer("Select domain:", reply_markup=builder.as_markup())
    await state.set_state(ProjectSearchStates.waiting_for_domain)
    await callback.answer()


@router.callback_query(ProjectSearchStates.waiting_for_domain)
async def project_domain(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(domain=callback.data)
    await callback.message.edit_text(f"Domain selected: {callback.data}")

    data = await state.get_data()
    project_id = data.get("project_id")
    query = data["search_query"]
    country = data["country"]
    language = data["language"]
    domain = data["domain"]

    chat_id = str(callback.from_user.id)
    user_id = await get_user_id_by_chat_id(chat_id)
    if user_id is None:
        await callback.message.answer("You not registerded (please first press /start).")
        return

    payload = {
        "query": query,
        "country": country,
        "language": language,
        "domain": domain,
        "user_id": user_id
    }
    results = {}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{WEB_API_URL}/api/projects/{project_id}/search", json=payload)
        if r.status_code == 200:
            d = r.json()
            results = d.get("results", {})
        else:
            await callback.message.answer("Mistake query to Serper.")
            return

    project_search_cache[callback.from_user.id] = {"results": results}

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="View results", callback_data="show_results_proj"))
    builder.add(InlineKeyboardButton(text="Analyze AI", callback_data="analyze_results_proj"))
    builder.adjust(2)
    await callback.message.answer("What you want to do?", reply_markup=builder.as_markup())
    await state.set_state(ProjectSearchStates.show_actions)
    await callback.answer()


@router.callback_query(ProjectSearchStates.show_actions, F.data == "show_results_proj")
async def project_show_results(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.from_user.id
    cdata = project_search_cache.get(chat_id)
    if not cdata:
        await callback.message.answer("No results.")
        await callback.answer()
        return

    results = cdata["results"]
    organic_results = results.get("organic", [])
    text_for_user = "Top results (Saved in project):\n"
    for idx, item in enumerate(organic_results[:10], start=1):
        title = item.get("title", "")
        link = item.get("link", "")
        text_for_user += f"{idx}. {title}\n{link}\n\n"

    await callback.message.answer(text_for_user or "Empty serp query")

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Save Excel", callback_data="proj_save_excel"))
    builder.add(InlineKeyboardButton(text="Repeat", callback_data="proj_repeat_search"))
    builder.add(InlineKeyboardButton(text="Exit", callback_data="proj_exit"))
    builder.adjust(1)
    await callback.message.answer("Action:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(ProjectSearchStates.show_actions, F.data == "analyze_results_proj")
async def project_analyze_results(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.from_user.id
    cdata = project_search_cache.get(chat_id)
    if not cdata:
        await callback.message.answer("No data for analyze.")
        await callback.answer()
        return

    results = cdata["results"]
    try:
        analyzed_text = analyze_results_with_openai(results)
        cdata["analyzed"] = analyzed_text
    except Exception as e:
        await callback.message.answer(f"Mistake sending in AI: {e}")
        await callback.answer()
        return

    await callback.message.answer(f"Analyze result:\n{cdata['analyzed']}")

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Repeat", callback_data="proj_repeat_search"))
    builder.add(InlineKeyboardButton(text="Exit", callback_data="proj_exit"))
    builder.adjust(1)
    await callback.message.answer("Action:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(ProjectSearchStates.show_actions, F.data == "proj_save_excel")
async def project_save_excel(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.from_user.id
    cdata = project_search_cache.get(chat_id)
    if not cdata:
        await callback.message.answer("No data.")
        await callback.answer()
        return

    organic = cdata["results"].get("organic", [])
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output)
    ws = wb.add_worksheet("Google Results (Project)")

    ws.write(0, 0, "Title")
    ws.write(0, 1, "Link")
    for i, item in enumerate(organic[:10], start=1):
        ws.write(i, 0, item.get("title", ""))
        ws.write(i, 1, item.get("link", ""))
    wb.close()
    output.seek(0)

    doc = FSInputFile(output, filename="project_google_results.xlsx")
    await callback.message.answer_document(document=doc, caption="Excel with results.")

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Repeat", callback_data="proj_repeat_search"))
    builder.add(InlineKeyboardButton(text="Exit", callback_data="proj_exit"))
    builder.adjust(1)
    await callback.message.answer("Action:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(ProjectSearchStates.show_actions, F.data == "proj_repeat_search")
async def project_repeat_search(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id in project_search_cache:
        del project_search_cache[callback.from_user.id]
    await state.set_state(ProjectSearchStates.waiting_for_query)
    await callback.message.answer("Repeat search in project. Please enter new query.")
    await callback.answer()


@router.callback_query(ProjectSearchStates.show_actions, F.data == "proj_exit")
async def project_exit_search(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id in project_search_cache:
        del project_search_cache[callback.from_user.id]
    await callback.message.answer("You close project search. You can press /history, /schedule.")
    await state.set_state(ProjectMenuStates.menu)
    await callback.answer()


@router.message(ProjectMenuStates.menu, Command("history"))
async def cmd_history_in_project(message: types.Message, state: FSMContext):
    data = await state.get_data()
    project_id = data.get("project_id")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{WEB_API_URL}/api/projects/{project_id}/history")
    if r.status_code != 200:
        await message.answer("Mistake ger history.")
        return
    hist_list = r.json()
    if not hist_list:
        await message.answer("History empty.")
        return
    builder = InlineKeyboardBuilder()
    for idx, h in enumerate(hist_list, start=1):
        cb_data = f"history_item:{h['id']}"
        btn_text = f"{idx}. {h['query_text'][:20]} от {h['created_at']}"
        builder.add(InlineKeyboardButton(text=btn_text, callback_data=cb_data))
    builder.adjust(1)
    await message.answer("History:", reply_markup=builder.as_markup())


@router.callback_query(ProjectMenuStates.menu, F.data.startswith("history_item:"))
async def callback_history_item(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    project_id = data.get("project_id")
    item_id = callback.data.split(":")[1]
    async with httpx.AsyncClient() as client:
        url = f"{WEB_API_URL}/api/projects/{project_id}/history/{item_id}"
        resp = await client.get(url)
    if resp.status_code != 200:
        await callback.message.answer("Mistak for get.")
        await callback.answer()
        return
    item = resp.json()
    results_str = item.get("results", "{}")
    try:
        results_json = json.loads(results_str)
    except:
        results_json = {}
    organic = results_json.get("organic", [])
    text_for_user = f"Query: {item['query_text']}\n\n"
    if not organic:
        text_for_user += "No results."
    else:
        for i, entry in enumerate(organic[:10], start=1):
            title = entry.get("title", "")
            link = entry.get("link", "")
            text_for_user += f"{i}. {title}\n{link}\n\n"
    await callback.message.answer(text_for_user)
    await callback.answer()


@router.message(ProjectMenuStates.menu, Command("schedule"))
async def cmd_schedule_in_project(message: types.Message, state: FSMContext):
    await message.answer(
        "Enter the schedule for the request in the format:\n"
        "For one-time (clocked): clocked YYYY-MM-DD HH:MM <request>\n"
        "For recurring (interval): interval <seconds> <request>"
    )
    await state.set_state(ScheduleState.waiting_for_schedule_input)


@router.message(ScheduleState.waiting_for_schedule_input)
async def process_schedule_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(" ", 3)
    if len(parts) < 3:
        await message.answer("Mistake format. Repeat enter.")
        return

    schedule_type = parts[0].lower()
    payload = {}
    if schedule_type == "clocked":
        if len(parts) < 4:
            await message.answer("Invalid format for clocked. Use: clocked YYYY-MM-DD HH:MM <query>")
            return
        dt_str = f"{parts[1]} {parts[2]}"
        search_query = parts[3]
        try:
            scheduled_dt = datetime.fromisoformat(dt_str)
        except Exception:
            await message.answer("Invalid date/time format. Use format: YYYY-MM-DD HH:MM")
            return
        payload = {
            "user_id": None,
            "query": search_query,
            "schedule_type": "clocked",
            "date_time": dt_str,
            "country": (await state.get_data()).get("country", "US"),
            "language": (await state.get_data()).get("language", "en"),
            "domain": (await state.get_data()).get("domain", "google.com")
        }
    elif schedule_type == "interval":
        parts = text.split(" ", 2)
        if len(parts) < 3:
            await message.answer("Invalid format for interval. Use: interval <seconds> <query>")
            return
        try:
            interval_seconds = int(parts[1])
        except Exception:
            await message.answer("Invalid interval format. It must be a number.")
            return
        search_query = parts[2]
        payload = {
            "user_id": None,
            "query": search_query,
            "schedule_type": "interval",
            "interval_seconds": interval_seconds,
            "country": (await state.get_data()).get("country", "US"),
            "language": (await state.get_data()).get("language", "en"),
            "domain": (await state.get_data()).get("domain", "google.com")
        }
    else:
        await message.answer("Unknown schedule type. Use 'clocked' or 'interval'.")
        return

    chat_id = str(message.from_user.id)
    user_id = await get_user_id_by_chat_id(chat_id)
    if user_id is None:
        await message.answer("You are not registered (do /start).")
        return
    payload["user_id"] = user_id

    data = await state.get_data()
    project_id = data.get("project_id")
    async with httpx.AsyncClient() as client:
        url = f"{WEB_API_URL}/api/projects/{project_id}/schedule"
        r = await client.post(url, json=payload)
        if r.status_code == 200:
            await message.answer("The request is scheduled.")
        else:
            await message.answer(f"Error planning query: {r.status_code} {r.text}")
    await state.clear()
