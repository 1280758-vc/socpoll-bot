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
ADMIN_IDS = [383222956, 233536337]  # <-- Два user_id адміністратора

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
    opts = [x.strip() for x in message.text.split(",") if x.strip()]
    if not opts:
        await message.answer("Введіть хоча б один варіант!")
        return
    qtype = user_steps[message.from_user.id]["q_partial"]["type"]
    q = {
        "type": "radio" if qtype=="Один варіант" else "multi",
        "question": user_steps[message.from_user.id]["q_partial"]["question"],
        "options": opts
    }
    if qtype == "Мультиваріант":
        await message.answer("Введіть максимум допустимих виборів (число):")
        user_steps[message.from_user.id]["q_partial"]["options"] = opts
        user_steps[message.from_user.id]["q_partial"]["_qobj"] = q
    else:
        user_steps[message.from_user.id]["questions"].append(q)
        await finish_q_add(message)

@dp.message(lambda msg: "q_partial" in user_steps.get(msg.from_user.id, {}) and user_steps[msg.from_user.id]["q_partial"].get("type") == "Мультиваріант" and "_qobj" in user_steps[msg.from_user.id]["q_partial"] and "options" in user_steps[msg.from_user.id]["q_partial"])
async def input_multi_max(message: types.Message):
    try:
        max_choice = int(message.text)
        q = user_steps[message.from_user.id]["q_partial"]["_qobj"]
        q["max"] = max_choice
        user_steps[message.from_user.id]["questions"].append(q)
        await finish_q_add(message)
    except:
        await message.answer("Введіть коректне число!")

@dp.message(lambda msg: "q_partial" in user_steps.get(msg.from_user.id, {}) and user_steps[msg.from_user.id]["q_partial"].get("type") == "Шкала" and "question" in user_steps[msg.from_user.id]["q_partial"])
async def input_scale(message: types.Message):
    try:
        parts = [int(x) for x in message.text.split(",")]
        if len(parts) != 2 or parts[0] >= parts[1]:
            raise ValueError
        q = {
            "type": "scale",
            "question": user_steps[message.from_user.id]["q_partial"]["question"],
            "scale": parts
        }
        user_steps[message.from_user.id]["questions"].append(q)
        await finish_q_add(message)
    except:
        await message.answer("Введіть 2 числа через кому, наприклад: 1, 11")

async def finish_q_add(message):
    del user_steps[message.from_user.id]["q_partial"]
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Додати питання")],
            [KeyboardButton(text="Завершити створення")]
        ],
        resize_keyboard=True
    )
    await message.answer("Питання додано. Додайте наступне питання або завершіть!", reply_markup=kb)

@dp.message(lambda msg: msg.text == "Завершити створення")
async def finish_poll(message: types.Message):
    data = user_steps.get(message.from_user.id, {})
    if "title" in data and "questions" in data and "amount" in data:
        async with aiosqlite.connect("socbot.db") as db:
            await db.execute(
                "INSERT INTO surveys (title, amount, questions) VALUES (?, ?, ?)",
                (data["title"], data["amount"], json.dumps(data["questions"]))
            )
            await db.commit()
        await message.answer(f"Опитування '{data['title']}' створено!", reply_markup=admin_menu())
    else:
        await message.answer("Недостатньо даних!")
    user_steps[message.from_user.id] = {"menu": "admin"}

### --- Реєстрація, демографія --- ###
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поділитися номером", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer(
        "👋 Вітаємо у боті для соціологічних опитувань!\n"
        "1. Для роботи поділіться, будь ласка, вашим номером телефона:",
        reply_markup=kb
    )

@dp.message(lambda msg: msg.contact is not None)
async def contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    async with aiosqlite.connect("socbot.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, phone) VALUES (?,?)", (user_id, phone))
        await db.commit()
    user_steps[user_id] = {"demostep": "sex"}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Чоловік")], [KeyboardButton(text="Жінка")]],
        resize_keyboard=True
    )
    await message.answer("Ваша стать?", reply_markup=kb)

@dp.message()
async def demodata(message: types.Message):
    user_id = message.from_user.id
    key = user_id
    # Демографія
    if key in user_steps and user_steps[key].get("demostep"):
        step = user_steps[key]["demostep"]
        if step == "sex":
            if message.text not in ["Чоловік", "Жінка"]:
                await message.answer("Оберіть одну відповідь!")
                return
            async with aiosqlite.connect("socbot.db") as db:
                await db.execute("UPDATE users SET sex=? WHERE user_id=?", (message.text, user_id))
                await db.commit()
            user_steps[key]["demostep"] = "birth"
            await message.answer("Ваш рік народження?", reply_markup=ReplyKeyboardRemove())
            return
        if step == "birth":
            try:
                year = int(message.text)
                assert 1920 < year < 2020
            except Exception:
                await message.answer("Вкажіть рік народження (числом)!")
                return
            async with aiosqlite.connect("socbot.db") as db:
                await db.execute("UPDATE users SET birth_year=? WHERE user_id=?", (year, user_id))
                await db.commit()
            user_steps[key]["demostep"] = "education"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=x)] for x in [
                        "Середня",
                        "Неокончена вища",
                        "Вища",
                        "Учена ступінь",
                        "Неокончена середня",
                        "Середня спеціальна (коледж)"
                    ]
                ],
                resize_keyboard=True
            )
            await message.answer("Освіта?", reply_markup=kb)
            return
        if step == "education":
            edukey = [
                "Середня",
                "Неокончена вища",
                "Вища",
                "Учена ступінь",
                "Неокончена середня",
                "Середня спеціальна (коледж)"
            ]
            if message.text not in edukey:
                await message.answer("Оберіть з варіантів!")
                return
            async with aiosqlite.connect("socbot.db") as db:
                await db.execute("UPDATE users SET education=? WHERE user_id=?", (message.text, user_id))
                await db.commit()
            user_steps[key]["demostep"] = "residence"
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=x)] for x in [
                    "Місто 1 млн +", "500000-1 млн", "300-500 тис", "100-200 тис", "5-50 тис", "Село"
                ]],
                resize_keyboard=True
            )
            await message.answer("Місце проживання?", reply_markup=kb)
            return
        if step == "residence":
            reskey = ["Місто 1 млн +", "500000-1 млн", "300-500 тис", "100-200 тис", "5-50 тис", "Село"]
            if message.text not in reskey:
                await message.answer("Оберіть з варіантів!")
                return
            async with aiosqlite.connect("socbot.db") as db:
                await db.execute("UPDATE users SET residence=? WHERE user_id=?", (message.text, user_id))
                await db.commit()
            del user_steps[key]
            await message.answer(
                "Реєстрація завершена!\n"
                "Ви можете отримати доступ до опитувань та переглядати свій баланс.\n"
                "Для цього використовуйте команду /balance."
            )
            return
    # Опитування нижче ↓
    if key in user_steps and user_steps[key].get("poll"):
        ses = user_steps[key]["poll"]
        qobj = ses["questions"][ses["step"]]
        ans = message.text
        if qobj.get("type") == "multi":
            selected = [x.strip() for x in ans.split(",") if x.strip() in qobj["options"]]
            if len(selected) == 0 or len(selected) > qobj.get("max", len(qobj["options"])):
                await message.answer(f"Виберіть від 1 до {qobj.get('max', len(qobj['options']))} варіантів, через кому!")
                return
            ans = selected
