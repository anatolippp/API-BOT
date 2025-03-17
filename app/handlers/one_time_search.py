import logging
import io
import xlsxwriter

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.countries import COUNTRIES
from config.languages import LANGUAGES
from config.domains import DOMAINS

from app.handlers.states import OneTimeSearchStates

from services.serper_service import google_search

from services.openai_service import analyze_results_with_openai

logger = logging.getLogger(__name__)
router = Router()

search_cache = {}


@router.callback_query(F.data == "go_once")
async def go_once_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter your search query (one-time):")
    await state.set_state(OneTimeSearchStates.waiting_for_query)
    await callback.answer()


@router.message(OneTimeSearchStates.waiting_for_query)
async def onetime_query_input(message: types.Message, state: FSMContext):
    await state.update_data(search_query=message.text)

    builder = InlineKeyboardBuilder()
    for emoji_flag, country_name, cb_data in COUNTRIES:
        button_text = f"{emoji_flag} {country_name}"
        builder.add(types.InlineKeyboardButton(text=button_text, callback_data=cb_data))
    builder.adjust(3)

    await message.answer("Select country:", reply_markup=builder.as_markup())
    await state.set_state(OneTimeSearchStates.waiting_for_country)


@router.callback_query(OneTimeSearchStates.waiting_for_country)
async def onetime_country(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(country=callback.data)
    await callback.message.edit_text(f"Country selected: {callback.data}")

    builder = InlineKeyboardBuilder()
    for lang_code, lang_label, cb_data in LANGUAGES:
        builder.add(types.InlineKeyboardButton(text=f"{lang_label} ({lang_code})", callback_data=cb_data))
    builder.adjust(2)

    await callback.message.answer("Select language:", reply_markup=builder.as_markup())
    await state.set_state(OneTimeSearchStates.waiting_for_language)
    await callback.answer()


@router.callback_query(OneTimeSearchStates.waiting_for_language)
async def onetime_language(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(language=callback.data)
    await callback.message.edit_text(f"Language selected: {callback.data}")

    builder = InlineKeyboardBuilder()
    for domain_label, domain_cb in DOMAINS:
        builder.add(types.InlineKeyboardButton(text=domain_label, callback_data=domain_cb))
    builder.adjust(2)

    await callback.message.answer("Select google domain:", reply_markup=builder.as_markup())
    await state.set_state(OneTimeSearchStates.waiting_for_domain)
    await callback.answer()


@router.callback_query(OneTimeSearchStates.waiting_for_domain)
async def onetime_domain(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(domain=callback.data)
    await callback.message.edit_text(f"Domain selected: {callback.data}")

    data = await state.get_data()
    query = data["search_query"]
    country = data["country"]
    language = data["language"]
    domain = data["domain"]

    try:
        results = google_search(query=query, country=country, language=language, domain=domain)
    except Exception as e:
        await callback.message.answer(f"Mistake serper query: {e}")
        return

    search_cache[callback.from_user.id] = {"results": results}

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Show results", callback_data="show_results"))
    builder.add(types.InlineKeyboardButton(text="Analyze AI", callback_data="analyze_results"))
    builder.adjust(2)

    await callback.message.answer("What you want?", reply_markup=builder.as_markup())
    await state.set_state(OneTimeSearchStates.show_actions)
    await callback.answer()


@router.callback_query(OneTimeSearchStates.show_actions, F.data == "show_results")
async def onetime_show_results(callback: types.CallbackQuery, state: FSMContext):
    cdata = search_cache.get(callback.from_user.id)
    if not cdata:
        await callback.message.answer("No results.")
        await callback.answer()
        return

    organic = cdata["results"].get("organic", [])
    text_for_user = "Top results:\n"
    for idx, item in enumerate(organic[:10], start=1):
        title = item.get("title", "")
        link = item.get("link", "")
        text_for_user += f"{idx}. {title}\n{link}\n\n"

    await callback.message.answer(text_for_user or "Empty serp")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Save Excel", callback_data="save_excel"))
    builder.add(types.InlineKeyboardButton(text="Repeat", callback_data="repeat_search"))
    builder.add(types.InlineKeyboardButton(text="Exit", callback_data="exit"))
    builder.adjust(1)

    await callback.message.answer("Action:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(OneTimeSearchStates.show_actions, F.data == "analyze_results")
async def onetime_analyze_results(callback: types.CallbackQuery, state: FSMContext):
    cdata = search_cache.get(callback.from_user.id)
    if not cdata:
        await callback.message.answer("No data for analyze.")
        await callback.answer()
        return

    try:
        analyzed_text = analyze_results_with_openai(cdata["results"])
        cdata["analyzed"] = analyzed_text
    except Exception as e:
        await callback.message.answer(f"Mistake API onenAI: {e}")
        await callback.answer()
        return

    await callback.message.answer(f"Analyze result:\n{cdata['analyzed']}")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Repeat", callback_data="repeat_search"))
    builder.add(types.InlineKeyboardButton(text="Exit", callback_data="exit"))
    builder.adjust(1)

    await callback.message.answer("Action", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(OneTimeSearchStates.show_actions, F.data == "save_excel")
async def onetime_save_excel(callback: types.CallbackQuery, state: FSMContext):
    cdata = search_cache.get(callback.from_user.id)
    if not cdata:
        await callback.message.answer("No data for save.")
        await callback.answer()
        return

    organic = cdata["results"].get("organic", [])

    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output)
    ws = wb.add_worksheet("Google Results (OneTime)")

    ws.write(0, 0, "Title")
    ws.write(0, 1, "Link")

    for i, item in enumerate(organic[:10], start=1):
        ws.write(i, 0, item.get("title", ""))
        ws.write(i, 1, item.get("link", ""))

    wb.close()
    output.seek(0)

    doc = FSInputFile(output, filename="google_results.xlsx")
    await callback.message.answer_document(document=doc, caption="Excel with results")

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Repeat", callback_data="repeat_search"))
    builder.add(types.InlineKeyboardButton(text="Exit", callback_data="exit"))
    builder.adjust(1)

    await callback.message.answer("Action:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(OneTimeSearchStates.show_actions, F.data == "repeat_search")
async def onetime_repeat_search(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id in search_cache:
        del search_cache[callback.from_user.id]
    await state.clear()
    await callback.message.answer("Repeat search. Enter your query:")
    await state.set_state(OneTimeSearchStates.waiting_for_query)
    await callback.answer()


@router.callback_query(OneTimeSearchStates.show_actions, F.data == "exit")
async def onetime_exit_search(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id in search_cache:
        del search_cache[callback.from_user.id]
    await state.clear()
    await callback.message.answer("Search ended. Press /go again.")
    await callback.answer()
