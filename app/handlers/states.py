from aiogram.fsm.state import StatesGroup, State

class OneTimeSearchStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_country = State()
    waiting_for_language = State()
    waiting_for_domain = State()
    show_actions = State()

class ProjectSearchStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_country = State()
    waiting_for_language = State()
    waiting_for_domain = State()
    show_actions = State()

class GoMenuStates(StatesGroup):
    main_menu = State()
    creating_project_name = State()
    adding_members = State()
    selecting_project = State()

class ProjectMenuStates(StatesGroup):
    menu = State()

class ScheduleState(StatesGroup):
    waiting_for_schedule_input = State()