import logging
import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

import gspread
from google.oauth2.service_account import Credentials

API_TOKEN = "ТВОЙ_ТЕЛЕГРАМ_ТОКЕН"
ADMIN_IDS = [123456789]  # Вкажи свої айді адмінів

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

#-------------- Google Sheets Setup -------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
gs = gspread.authorize(creds)

USERS_SHEET = "Users"
ANSWERS_SHEET = "Answers_Survey_1"

users_table = gs.open(USERS_SHEET).sheet1
answers_table = gs.open(ANSWERS_SHEET).sheet1

#--------------- DEMO UI -----------------------------

def user_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Переглянути баланс")],
            [KeyboardButton("Почати опитування")],
        ],
        resize_keyboard=True
    )
    return kb

#---------- MAIN FUNCTIONALITY -----------------------

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup([[KeyboardButton("Поділитися номером", request_contact=True)]], resize_keyboard=True)
    await message.answer(
        "👋 Вітаю! Поділіться номером для реєстрації:",
        reply_markup=kb
    )

@dp.message(lambda msg: msg.contact is not None)
async def contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    kb = ReplyKeyboardMarkup([[KeyboardButton("Чоловік")], [KeyboardButton("Жінка")]], resize_keyboard=True)
    # Перевір, чи є вже user_id в таблиці
    vals = users_table.col_values(1)
    if str(user_id) in vals:
        await message.answer("Ви вже зареєстровані!", reply_markup=user_menu())
        return
    # Починай демо-реєстрацію
    users_table.append_row([user_id, phone, "", "", "", ""])  # sex, birth_year, education, residence - пусто
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

@dp.message(lambda msg: msg.text == "Переглянути баланс")
async def balance(message: types.Message):
    await message.answer("Тут буде баланс (приклад)")

@dp.message(lambda msg: msg.text == "Почати опитування")
async def poll_start(message: types.Message):
    user_id = message.from_user.id
    vals = users_table.col_values(1)
    idx = vals.index(str(user_id)) + 1
    # Дістаємо демографію
    demo = users_table.row_values(idx)
    # Запитуємо перше питання опитування
    await message.answer("Питання 1: Який ваш вік?")
    dp.data.setdefault(user_id, {"answers": [], "step": 1, "demo": demo})

@dp.message(lambda msg: dp.data.get(msg.from_user.id, {}).get("step") == 1)
async def poll_q1(message: types.Message):
    dp.data[message.from_user.id]["answers"].append(message.text)
    dp.data[message.from_user.id]["step"] = 2
    await message.answer("Питання 2: Чи подобається вам цей бот?")

@dp.message(lambda msg: dp.data.get(msg.from_user.id, {}).get("step") == 2)
async def poll_q2(message: types.Message):
    dp.data[message.from_user.id]["answers"].append(message.text)
    demo = dp.data[message.from_user.id]["demo"]
    answers = dp.data[message.from_user.id]["answers"]
    # Записуємо в GoogleSheet (user_id, питання1, питання2, + демографія)
    answers_table.append_row([demo[0]] + answers + demo[1:])
    await message.answer("Дякуємо за участь!", reply_markup=user_menu())
    del dp.data[message.from_user.id]

async def main():
    dp.data = {}  # сюди будуть тимчасові сесії опитувань
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
