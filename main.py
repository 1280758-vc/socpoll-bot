import logging
import asyncio
import json

import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = "8330526731:AAF6gnM2wovo2U_x7HVKd9YGn7hrxOajEsY"
ADMIN_IDS = [383222956, 233536337]

# ------------ GOOGLE SHEETS ------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_PATH = "/etc/secrets/credentials"

creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
gs = gspread.authorize(creds)

USERS_SHEET = "Users"
users_table = gs.open(USERS_SHEET).sheet1

POLLS_SHEET = "Polls"  # таблиця Polls повинна існувати й мати колонки: poll_id | title | questions_json
polls_table = gs.open(POLLS_SHEET).sheet1

# ------------ BOT ------------

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.data = {}


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити опитування")],
            [KeyboardButton(text="Оглянути/Редагувати анкету")],
            [KeyboardButton(text="Розіслати опитування")],
            [KeyboardButton(text="Експорт відповідей")],
            [KeyboardButton(text="Статистика")],
        ],
        resize_keyboard=True,
    )


def user_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Почати опитування")],
            [KeyboardButton(text="Переглянути баланс")],
        ],
        resize_keyboard=True,
    )


# ------------ РЕЄСТРАЦІЯ В Users ------------

@dp.message(Command("start"))
async def start(message: types.Message):
    logger.info("Received /start from %s", message.from_user.id)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
    )
    await message.answer("👋 Вітаю! Поділіться номером для реєстрації:", reply_markup=kb)


@dp.message(lambda msg: msg.contact is not None)
async def contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    logger.info("Got contact from %s: %s", user_id, phone)

    vals = users_table.col_values(1)
    if str(user_id) in vals:
        await message.answer("Ви вже зареєстровані ✅", reply_markup=user_menu())
        return

    users_table.append_row([user_id, phone, "", "", "", "", ""])
    logger.info("User %s added to Users sheet", user_id)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Чоловік")],
            [KeyboardButton(text="Жінка")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Ваша стать?", reply_markup=kb)


@dp.message(lambda msg: msg.text in ["Чоловік", "Жінка"])
async def input_sex(message: types.Message):
    user_id = message.from_user.id
    sex = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 3, sex)
    logger.info("User %s sex saved: %s", user_id, sex)
    await message.answer("Ваш рік народження?", reply_markup=ReplyKeyboardRemove())


@dp.message(lambda msg: msg.text.isdigit() and 1920 < int(msg.text) < 2020)
async def input_birth(message: types.Message):
    user_id = message.from_user.id
    birth_year = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 4, birth_year)
    logger.info("User %s birth_year saved: %s", user_id, birth_year)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Середня")],
            [KeyboardButton(text="Вища")],
            [KeyboardButton(text="Учена ступінь")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Ваша освіта?", reply_markup=kb)


@dp.message(lambda msg: msg.text in ["Середня", "Вища", "Учена ступінь"])
async def input_education(message: types.Message):
    user_id = message.from_user.id
    edu = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 5, edu)
    logger.info("User %s education saved: %s", user_id, edu)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Місто")],
            [KeyboardButton(text="Село")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Місце проживання?", reply_markup=kb)


@dp.message(lambda msg: msg.text in ["Місто", "Село"])
async def input_residence_type(message: types.Message):
    user_id = message.from_user.id
    residence_type = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 6, residence_type)
    logger.info("User %s residence type saved: %s", user_id, residence_type)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="До 10 тис.")],
            [KeyboardButton(text="10–50 тис.")],
            [KeyboardButton(text="50–100 тис.")],
            [KeyboardButton(text="100–500 тис.")],
            [KeyboardButton(text="500 тис.–1 000 000")],
            [KeyboardButton(text="Більше 1 000 000")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Розмір населеного пункту?", reply_markup=kb)


@dp.message(
    lambda msg: msg.text
    in [
        "До 10 тис.",
        "10–50 тис.",
        "50–100 тис.",
        "100–500 тис.",
        "500 тис.–1 000 000",
        "Більше 1 000 000",
    ]
)
async def input_city_size(message: types.Message):
    user_id = message.from_user.id
    city_size = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 7, city_size)
    logger.info("User %s city_size saved: %s", user_id, city_size)

    await message.answer("Реєстрація завершена ✅", reply_markup=user_menu())


# ------------ АДМІН МЕНЮ ------------

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Адмін-меню:", reply_markup=admin_menu())


# ------------ ЕТАП 1: СТВОРЕННЯ ОПИТУВАННЯ (структура в Polls) ------------

@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and msg.text == "Створити опитування")
async def create_poll_start(message: types.Message):
    dp.data[message.from_user.id] = {
        "step": "title",
        "poll": {"questions": []},
    }
    await message.answer("Введіть назву опитування:", reply_markup=ReplyKeyboardRemove())


@dp.message(
    lambda msg: msg.from_user.id in ADMIN_IDS
    and dp.data.get(msg.from_user.id, {}).get("step") == "title"
)
async def create_poll_set_title(message: types.Message):
    state = dp.data[message.from_user.id]
    state["poll"]["title"] = message.text.strip()
    state["step"] = "count"
    await message.answer("Скільки питань буде в опитуванні? Введіть число.")


@dp.message(
    lambda msg: msg.from_user.id in ADMIN_IDS
    and dp.data.get(msg.from_user.id, {}).get("step") == "count"
)
async def create_poll_set_count(message: types.Message):
    state = dp.data[message.from_user.id]
    try:
        n = int(message.text)
        if n <= 0:
            raise ValueError
        state["poll"]["n"] = n
        state["poll"]["qidx"] = 1
        state["step"] = "q_text"
        await message.answer("Введіть текст питання №1:")
    except ValueError:
        await message.answer("Введіть, будь ласка, додатне число.")


@dp.message(
    lambda msg: msg.from_user.id in ADMIN_IDS
    and dp.data.get(msg.from_user.id, {}).get("step") == "q_text"
)
async def create_poll_q_text(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    poll["qbuf"] = {
        "index": poll["qidx"],
        "text": message.text.strip(),
    }
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Один вибір")],
            [KeyboardButton(text="Мультивибір")],
            [KeyboardButton(text="Текст")],
            [KeyboardButton(text="Шкала")],
        ],
        resize_keyboard=True,
    )
    state["step"] = "q_kind"
    await message.answer("Оберіть тип питання:", reply_markup=kb)


@dp.message(
