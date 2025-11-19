import logging
import asyncio
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
)
from aiogram.filters import Command

API_TOKEN = "8330526731:AAHYuQliBPflpZbWRC5e4COdD2uHiQMtcdg"
ADMIN_IDS = [383222956, 233536337]
logging.basicConfig(level=logging.INFO)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDENTIALS_PATH = "/etc/secrets/credentials"
creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
gs = gspread.authorize(creds)
USERS_SHEET = "Users"
users_table = gs.open(USERS_SHEET).sheet1

REWARD_PER_SURVEY = 10

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def admin_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити опитування")],
            [KeyboardButton(text="Оглянути/Редагувати анкету")],
            [KeyboardButton(text="Розіслати опитування")],
            [KeyboardButton(text="Експорт відповідей")],
            [KeyboardButton(text="Статистика")]
        ],
        resize_keyboard=True
    )
    return kb

def user_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Почати опитування")],
            [KeyboardButton(text="Переглянути баланс")]
        ],
        resize_keyboard=True
    )
    return kb

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поділитися номером", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer("👋 Вітаю! Поділіться номером для реєстрації:", reply_markup=kb)

@dp.message(lambda msg: msg.contact is not None)
async def contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    vals = users_table.col_values(1)
    if str(user_id) in vals:
        await message.answer("Ви вже зареєстровані!", reply_markup=user_menu())
        return
    users_table.append_row([user_id, phone, "", "", "", ""])
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Чоловік")], [KeyboardButton(text="Жінка")]],
        resize_keyboard=True
    )
    await message.answer("Ваша стать?", reply_markup=kb)

@dp.message(lambda msg: msg.text in ["Чоловік", "Жінка"])
async def input_sex(message: types.Message):
    user_id = message.from_user.id
    vals = users_table.col_values(1)
    idx = vals.index(str(user_id)) + 1
    users_table.update_cell(idx, 3, message.text)
    await message.answer("Ваш рік народження?", reply_markup=ReplyKeyboardRemove())

@dp.message(lambda msg: msg.text.isdigit() and 1920 < int(msg.text) < 2020)
async def input_birth(message: types.Message):
    user_id = message.from_user.id
    vals = users_table.col_values(1)
    idx = vals.index(str(user_id)) + 1
    users_table.update_cell(idx, 4, message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Середня")],
            [KeyboardButton(text="Вища")],
            [KeyboardButton(text="Учена ступінь")]
        ],
        resize_keyboard=True
    )
    await message.answer("Ваша освіта?", reply_markup=kb)

@dp.message(lambda msg: msg.text in ["Середня", "Вища", "Учена ступінь"])
async def input_education(message: types.Message):
    user_id = message.from_user.id
    vals = users_table.col_values(1)
    idx = vals.index(str(user_id)) + 1
    users_table.update_cell(idx, 5, message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Місто")],
            [KeyboardButton(text="Село")]
        ],
        resize_keyboard=True
    )
    await message.answer("Місце проживання?", reply_markup=kb)

@dp.message(lambda msg: msg.text in ["Місто", "Село"])
async def input_residence(message: types.Message):
    user_id = message.from_user.id
    vals = users_table.col_values(1)
    idx = vals.index(str(user_id)) + 1
    users_table.update_cell(idx, 6, message.text)
    await message.answer("Реєстрація завершена!", reply_markup=user_menu())

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Меню адміністратора:", reply_markup=admin_menu())

ADMIN_CMDS = [
    "Створити опитування",
    "Оглянути/Редагувати анкету",
    "Розіслати опитування",
    "Експорт відповідей",
    "Статистика"
]

@dp.message(lambda msg: msg.text in ADMIN_CMDS)
async def admin_stub(message: types.Message):
    await message.answer(f"Обрана функція “{message.text}”. Ця дія поки не реалізована. Якщо потрібна конкретна — напиши!")

@dp.message(lambda msg: msg.text == "Почати опитування")
async def poll_start(message: types.Message):
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    if not files:
        await message.answer("Немає активних опитувань.")
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"{name.replace('Answers_Survey_', '')}")] for name in files],
        resize_keyboard=True
    )
    await message.answer("Оберіть опитування:", reply_markup=kb)

@dp.message(lambda msg: msg.text == "Переглянути баланс")
async def balance(message: types.Message):
    user_id = message.from_user.id
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    total = 0
    for poll in files:
        sheet = gs.open(poll).sheet1
        data = sheet.get_all_values()
        for row in data[2:]:
            if len(row) >= 1 and str(row[0]) == str(user_id):
                if len(row) > len(data[0]):
                    v = row[-1]
                    try:
                        total += float(v)
                    except:
                        pass
    await message.answer(f"Ваш баланс: {total} грн", reply_markup=user_menu())

@dp.message(lambda msg: True)
async def fallback(message: types.Message):
    await message.answer("Бот працює. Це повідомлення не оброблено спеціальним хендлером.")

async def main():
    dp.data = {}
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
