import logging
import asyncio

import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = "8330526731:AAHDXrNmgrYJ3hHpNj1jIdGc7pYZzrHBGjk"
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

# Очікується структура колонок:
# 1: user_id
# 2: phone
# 3: sex
# 4: birth_year
# 5: education
# 6: residence_type (Місто/Село)
# 7: city_size (До 10 тис. / 10–50 тис. / ...)

# ------------ BOT ------------

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


def admin_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити опитування")],
            [KeyboardButton(text="Оглянути/Редагувати анкету")],
            [KeyboardButton(text="Розіслати опитування")],
            [KeyboardButton(text="Експорт відповідей")],
            [KeyboardButton(text="Статистика")],
        ],
        resize_keyboard=True,
    )
    return kb


def user_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Почати опитування")],
            [KeyboardButton(text="Переглянути баланс")],
        ],
        resize_keyboard=True,
    )
    return kb


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

    # user_id, phone, sex, birth_year, education, residence_type, city_size
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
            [KeyboardButton(text="500 тис. і більше")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Розмір населеного пункту?", reply_markup=kb)


@dp.message(lambda msg: msg.text in [
    "До 10 тис.",
    "10–50 тис.",
    "50–100 тис.",
    "100–500 тис.",
    "500 тис. і більше",
])
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


# ------------ АДМІН / ECHO ------------

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Адмін-меню (поки що тест):", reply_markup=admin_menu())


@dp.message()
async def echo(message: types.Message):
    logger.info("Echo message from %s: %s", message.from_user.id, message.text)
    await message.answer("Тестовий echo: " + message.text)


# ------------ ЗАПУСК ------------

async def main():
    logger.info("Bot starting with registration & Users (city size)...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception("Bot crashed with exception: %s", e)


if __name__ == "__main__":
    logger.info("main.py __name__ == '__main__', starting asyncio.run")
    asyncio.run(main())
