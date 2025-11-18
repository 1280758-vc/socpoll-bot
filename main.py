import logging
import asyncio
import pandas as pd
import aiosqlite
import json

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
)
from aiogram.filters import Command, CommandObject

API_TOKEN = "8330526731:AAFK3hBMI4L3BvmrXpp7NlDPFYDK98EMuSE"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
ADMIN_IDS = [383222956, 233536337]

user_steps = {}

### --- База даних --- ###
async def db_setup():
    async with aiosqlite.connect("socbot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone TEXT,
                sex TEXT,
                birth_year INTEGER,
                education TEXT,
                residence TEXT,
                balance REAL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payouts (
                user_id INTEGER,
                amount REAL,
                status TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS surveys (
                survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                amount REAL,
                questions TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                user_id INTEGER,
                survey_id INTEGER,
                answer_data TEXT
            )
        """)
        await db.commit()

# --- Головне меню для адміна ---
def admin_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити опитування")],
            [KeyboardButton(text="Переглянути опитування")],
            [KeyboardButton(text="Розіслати опитування")]
        ],
        resize_keyboard=True
    )
    return kb

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Доступно лише адміністратору.")
        return
    await message.answer("Вітаю в адмін-кабінеті!", reply_markup=admin_menu())
    user_steps[message.from_user.id] = {"menu": "admin"}

@dp.message(lambda msg: msg.text == "Створити опитування")
async def start_create_poll(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    user_steps[message.from_user.id] = {"menu": "create_poll"}
    await message.answer("Введіть назву опитування:")

@dp.message(lambda msg: user_steps.get(msg.from_user.id, {}).get("menu") == "create_poll" and "title" not in user_steps[msg.from_user.id])
async def get_poll_title(message: types.Message):
    user_steps[message.from_user.id]["title"] = message.text
    await message.answer("Введіть суму винагороди (грн):")

@dp.message(lambda msg: user_steps.get(msg.from_user.id, {}).get("menu") == "create_poll" and "title" in user_steps[msg.from_user.id] and "amount" not in user_steps[msg.from_user.id])
async def get_poll_amount(message: types.Message):
    try:
        amount = float(message.text.replace(",", "."))
    except:
        await message.answer("Введіть коректну суму!")
        return
    user_steps[message.from_user.id]["amount"] = amount
    user_steps[message.from_user.id]["questions"] = []
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Додати питання")],
            [KeyboardButton(text="Завершити створення")]
        ],
        resize_keyboard=True
    )
    await message.answer("Додайте питання або завершіть створення!", reply_markup=kb)

@dp.message(lambda msg: msg.text == "Додати питання")
async def add_question_type(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Текст")],
            [KeyboardButton(text="Один варіант")],
            [KeyboardButton(text="Мультиваріант")],
            [KeyboardButton(text="Шкала")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True
    )
    user_steps[message.from_user.id]["q_partial"] = {}
    await message.answer("Виберіть тип питання:", reply_markup=kb)

@dp.message(lambda msg: msg.text in ["Текст", "Один варіант", "Мультиваріант", "Шкала"])
async def select_qtype(message: types.Message):
    user_steps[message.from_user.id]["q_partial"]["type"] = message.text
    await message.answer("Введіть текст питання:", reply_markup=ReplyKeyboardRemove())

@dp.message(lambda msg: "q_partial" in user_steps.get(msg.from_user.id, {}) and "type" in user_steps[msg.from_user.id]["q_partial"] and "question" not in user_steps[msg.from_user.id]["q_partial"])
async def input_qtext(message: types.Message):
    user_steps[message.from_user.id]["q_partial"]["question"] = message.text
    qtype = user_steps[message.from_user.id]["q_partial"]["type"]
    if qtype == "Текст":
        user_steps[message.from_user.id]["questions"].append({
            "type": "text",
            "question": message.text
        })
        await finish_q_add(message)
    elif qtype in ["Один варіант", "Мультиваріант"]:
        await message.answer("Введіть варіанти відповіді (через кому):")
    elif qtype == "Шкала":
        await message.answer("Введіть межі шкали (наприклад: 1, 11):")

@dp.message(lambda msg: "q_partial" in user_steps.get(msg.from_user.id, {}) and user_steps[msg.from_user.id]["q_partial"].get("type") in ["Один варіант", "Мультиваріант"] and "question" in user_steps[msg.from_user.id]["q_partial"] and "options" not in user_steps[msg.from_user.id]["q_partial"])
async def input_options(message: types.Message):
