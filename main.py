import logging
import pandas as pd
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
import asyncio

API_TOKEN = "8330526731:AAGrxqGzS8VBCGMBkJ6cjjLvmfPXB-j-7ck"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

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

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Поділитися номером", request_contact=True))
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
    await ask_demography(message)

async def ask_demography(message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Чоловік", "Жінка")
    await message.answer("Ваша стать?", reply_markup=kb)
    dp.data["demostep"] = "sex"

@dp.message(lambda msg: dp.data.get("demostep") == "sex")
async def demosex(message: types.Message):
    if message.text not in ["Чоловік", "Жінка"]:
        await message.answer("Оберіть одну відповідь!")
        return
    user_id = message.from_user.id
    async with aiosqlite.connect("socbot.db") as db:
        await db.execute("UPDATE users SET sex=? WHERE user_id=?", (message.text, user_id))
        await db.commit()
    dp.data["demostep"] = "birth"
    await message.answer("Ваш рік народження?", reply_markup=ReplyKeyboardRemove())

@dp.message(lambda msg: dp.data.get("demostep") == "birth")
async def demobirth(message: types.Message):
    try:
        year = int(message.text)
        assert 1920 < year < 2020
    except:
        await message.answer("Вкажіть рік народження (числом)!")
        return
    user_id = message.from_user.id
    async with aiosqlite.connect("socbot.db") as db:
        await db.execute("UPDATE users SET birth_year=? WHERE user_id=?", (year, user_id))
        await db.commit()
    dp.data["demostep"] = "education"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        "Середня",
        "Неокончена вища",
        "Вища",
        "Учена ступінь",
        "Неокончена середня",
        "Середня спеціальна (коледж)"
    )
    await message.answer("Освіта?", reply_markup=kb)

@dp.message(lambda msg: dp.data.get("demostep") == "education")
async def demoedu(message: types.Message):
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
    user_id = message.from_user.id
    async with aiosqlite.connect("socbot.db") as db:
        await db.execute("UPDATE users SET education=? WHERE user_id=?", (message.text, user_id))
        await db.commit()
    dp.data["demostep"] = "residence"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Місто 1 млн +", "500000-1 млн", "300-500 тис", "100-200 тис", "5-50 тис", "Село")
    await message.answer("Місце проживання?", reply_markup=kb)

@dp.message(lambda msg: dp.data.get("demostep") == "residence")
async def demoresidence(message: types.Message):
    reskey = ["Місто 1 млн +", "500000-1 млн", "300-500 тис", "100-200 тис", "5-50 тис", "Село"]
    if message.text not in reskey:
        await message.answer("Оберіть з варіантів!")
        return
    user_id = message.from_user.id
    async with aiosqlite.connect("socbot.db") as db:
        await db.execute("UPDATE users SET residence=? WHERE user_id=?", (message.text, user_id))
        await db.commit()
    dp.data.pop("demostep", None)
    await message.answer(
        "Реєстрація завершена!\n"
        "Ви можете отримати доступ до опитувань та переглядати свій баланс.\n"
        "Для цього використовуйте команду /balance."
    )

@dp.message(Command("balance"))
async def balance(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("socbot.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    bal = row[0] if row else 0
    await message.answer(f"Баланс: {bal:.2f} грн\nМін. сума для виводу — 50 грн.\nЩоб подати заявку на вивід, напишіть /withdraw")

@dp.message(Command("withdraw"))
async def withdraw(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("socbot.db") as db:
        async with db.execute("SELECT balance, phone FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        bal = row[0] if row else 0
        phone = row[1] if row else ""
        if bal < 50:
            await message.answer("Недостатньо коштів для виводу. Мінімум 50 грн.")
            return
        await db.execute("INSERT INTO payouts (user_id, amount, status) VALUES (?, ?, ?)", (user_id, bal, "pending"))
        await db.execute("UPDATE users SET balance=0 WHERE user_id=?", (user_id,))
        await db.commit()
    await message.answer(f"Заявку на вивід {bal:.2f} грн на номер {phone} прийнято. Адмін зв'яжеться для поповнення.")

async def main():
    await db_setup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
