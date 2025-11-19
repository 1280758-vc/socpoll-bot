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
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDENTIALS_PATH = "/etc/secrets/credentials"  # для Render Secret Files

creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
gs = gspread.authorize(creds)
USERS_SHEET = "Users"
users_table = gs.open(USERS_SHEET).sheet1

REWARD_PER_SURVEY = 10  # сума за проходження опитування

def admin_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Створити опитування")],
            [KeyboardButton("Оглянути/Редагувати анкету")],
            [KeyboardButton("Розіслати опитування")],
            [KeyboardButton("Експорт відповідей")],
            [KeyboardButton("Статистика")]
        ],
        resize_keyboard=True
    )
    return kb

def user_menu():
    kb = ReplyKeyboardMarkup([
        [KeyboardButton("Почати опитування")],
        [KeyboardButton("Переглянути баланс")]
    ], resize_keyboard=True)
    return kb

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("Поділитися номером", request_contact=True)]],
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
    kb = ReplyKeyboardMarkup([[KeyboardButton("Чоловік")], [KeyboardButton("Жінка")]], resize_keyboard=True)
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
        keyboard=[[KeyboardButton(x)] for x in ["Середня", "Вища", "Учена ступінь"]],
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
        keyboard=[[KeyboardButton(x)] for x in ["Місто", "Село"]],
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

# ---- Далі залиш код із останнього варіанту (адмін, створення анкет, фільтри, експорт, баланс, проходження анкет)
# Включає всі SCOPES, коректний шлях до credentials.json!

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Меню адміністратора:", reply_markup=admin_menu())

# ... Додавай блоки для опитувань, розсилки, фільтрації, балансу, експорт як було раніше ...

async def main():
    dp.data = {}
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
