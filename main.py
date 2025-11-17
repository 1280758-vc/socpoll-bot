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

API_TOKEN = "8330526731:AAGrxqGzS8VBCGMBkJ6cjjLvmfPXB-j-7ck"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
ADMIN_IDS = [383222956]  # <-- user_id адміністратора!

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

### --- Реєстрація, демографія --- ###
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
    dp.data[str(message.from_user.id)] = {"demostep": "sex"}

@dp.message()
async def demodata(message: types.Message):
    user_id = message.from_user.id
    key = str(user_id)
    # Демографія
    if key in dp.data and dp.data[key].get("demostep"):
        step = dp.data[key]["demostep"]
        if step == "sex":
            if message.text not in ["Чоловік", "Жінка"]:
                await message.answer("Оберіть одну відповідь!")
                return
            async with aiosqlite.connect("socbot.db") as db:
                await db.execute("UPDATE users SET sex=? WHERE user_id=?", (message.text, user_id))
                await db.commit()
            dp.data[key]["demostep"] = "birth"
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
            dp.data[key]["demostep"] = "education"
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
            dp.data[key]["demostep"] = "residence"
            kb = ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("Місто 1 млн +", "500000-1 млн", "300-500 тис", "100-200 тис", "5-50 тис", "Село")
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
            del dp.data[key]
            await message.answer(
                "Реєстрація завершена!\n"
                "Ви можете отримати доступ до опитувань та переглядати свій баланс.\n"
                "Для цього використовуйте команду /balance."
            )
            return
    # Логіка опитувань далі ↓

    # --- ПРОХОДЖЕННЯ ОПИТУВАННЯ ---
    if key in dp.data and dp.data[key].get("poll"):
        ses = dp.data[key]["poll"]
        qobj = ses["questions"][ses["step"]]
        ans = message.text

        # Мультивибір
        if qobj.get("type") == "multi":
            selected = [x.strip() for x in ans.split(",") if x.strip() in qobj["options"]]
            if len(selected) == 0 or len(selected) > qobj.get("max", len(qobj["options"])):
                await message.answer(f"Виберіть від 1 до {qobj.get('max', len(qobj['options']))} варіантів, через кому!")
                return
            ans = selected
        # Ексклюзивний варіант
        if qobj.get("type") == "radio" and "exclusive" in qobj:
            if ans == qobj["exclusive"]:
                ses["answers"].append(ans)
                ses["step"] = len(ses["questions"])  # завершити опитування
            else:
                ses["answers"].append(ans)
                ses["step"] += 1
        else:
            ses["answers"].append(ans)
            ses["step"] += 1

        # Наступне питання або кінець
        if ses["step"] >= len(ses["questions"]):
            async with aiosqlite.connect("socbot.db") as db:
                await db.execute(
                    "INSERT INTO answers (user_id, survey_id, answer_data) VALUES (?, ?, ?)",
                    (user_id, ses["poll_id"], json.dumps(ses["answers"]))
                )
                await db.execute(
                    "UPDATE users SET balance=balance+? WHERE user_id=?",
                    (ses["amount"], user_id)
                )
                await db.commit()
            del dp.data[key]["poll"]
            await message.answer("Дякуємо за участь! Винагорода зарахована на баланс. /balance")
            return
        # Показати наступне питання
        await ask_poll_question(message, ses)
        return

### --- BALANCE --- ###
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

### --- АДМІНКА: створення, розсилка, запуск опитування, експорт --- ###
@dp.message(Command("newpoll"))
async def newpoll(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Доступно лише адміністратору.")
        return
    try:
        data = command.args.split('|', 2)
        title = data[0].strip()
        amount = float(data[1].replace(",", "."))
        questions = json.loads(data[2])
    except Exception:
        await message.answer("Помилка у форматі! Синтаксис: /newpoll Тема|сума|json_питань")
        return
    async with aiosqlite.connect("socbot.db") as db:
        await db.execute(
            "INSERT INTO surveys (title, amount, questions) VALUES (?, ?, ?)",
            (title, amount, json.dumps(questions))
        )
        await db.commit()
    await message.answer(f"Опитування '{title}' створено та збережено.")

@dp.message(Command("sendpoll"))
async def sendpoll(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Доступно лише адміністратору.")
        return
    try:
        poll_id = int(command.args.strip())
    except Exception:
        await message.answer("Вкажіть ID опитування: /sendpoll 1")
        return
    async with aiosqlite.connect("socbot.db") as db:
        async with db.execute("SELECT title, amount FROM surveys WHERE survey_id=?", (poll_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            await message.answer("Опитування не знайдено.")
            return
        title, amount = row
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()
        for (uid,) in users:
            try:
                await bot.send_message(
                    uid,
                    f"🚩 Запрошення на опитування '{title}'\nВинагорода: {amount} грн.\nЩоб долучитись, напишіть /poll {poll_id}"
                )
            except Exception:
                pass  # юзер заблокував/помилка — ігноруємо
    await message.answer(f"Оголошення про опитування {poll_id} розіслано.")

@dp.message(Command("poll"))
async def poll_start(message: types.Message, command: CommandObject):
    try:
        poll_id = int(command.args.strip())
    except Exception:
        await message.answer("Неправильний формат! Синтаксис: /poll 1")
        return
    user_id = message.from_user.id
    key = str(user_id)
    async with aiosqlite.connect("socbot.db") as db:
        async with db.execute("SELECT title, amount, questions FROM surveys WHERE survey_id=?", (poll_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            await message.answer("Опитування не знайдено.")
            return
        _, amount, questions = row
        dp.data[key] = {"poll": {
            "poll_id": poll_id,
            "questions": json.loads(questions),
            "step": 0,
            "answers": [],
            "amount": amount
        }}
    await ask_poll_question(message, dp.data[key]["poll"])

async def ask_poll_question(message, ses):
    q = ses["questions"][ses["step"]]
    text = f"{q['question']}"
    kb = None
    if q.get('options'):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for opt in q['options']:
            kb.add(opt)
    elif q.get('scale'):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        rng = range(*q['scale']) if isinstance(q['scale'], list) else range(1, 12)
        for i in rng:
            kb.add(str(i))
    elif q.get("type") == "multi":
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for opt in q['options']:
            kb.add(opt)
        text += f"\n(Виберіть до {q.get('max', len(q['options']))} через кому)"
    await message.answer(text, reply_markup=kb or ReplyKeyboardRemove())

@dp.message(Command("export"))
async def export_answers(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Доступно лише адміністратору.")
        return
    async with aiosqlite.connect("socbot.db") as db:
        q = "SELECT a.user_id, a.survey_id, a.answer_data, u.sex, u.birth_year, u.education, u.residence FROM answers a JOIN users u ON a.user_id=u.user_id"
        df = pd.read_sql_query(q, db)
    df.to_excel("export.xlsx", index=False)
    await message.answer_document(FSInputFile("export.xlsx"), caption="Результати опитувань (Excel)")

### --- Запуск --- ###
async def main():
    await db_setup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
