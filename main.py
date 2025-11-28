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

POLLS_SHEET = "Polls"  # має існувати з колонками: poll_id | title | questions_json
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


@dp.message(lambda m: m.contact is not None)
async def contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    logger.info("Got contact from %s: %s", user_id, phone)

    vals = users_table.col_values(1)
    if str(user_id) in vals:
        await message.answer("Ви вже зареєстровані ✅", reply_markup=user_menu())
        return

    users_table.append_row([user_id, phone, "", "", "", "", ""])
    logger.info("User %s added to Users sheet
