import logging
import asyncio
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

API_TOKEN = "8330526731:AAHYuQliBPflpZbWRC5e4COdD2uHiQMtcdg"
ADMIN_IDS = [383222956, 233536337]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
gs = gspread.authorize(creds)

USERS_SHEET = "Users"

def open_answers_table(num):
    return gs.open(f"Answers_Survey_{num}").sheet1

users_table = gs.open(USERS_SHEET).sheet1

def user_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Переглянути баланс")],
            [KeyboardButton("Почати опитування")],
        ],
        resize_keyboard=True
    )
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Учасники")],
            [KeyboardButton("Оглянути результати опитувань")],
            [KeyboardButton("Розіслати опитування")],
            [KeyboardButton("Експорт")]
        ],
        resize_keyboard=True
    )
    return kb

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Меню адміністратора:", reply_markup=admin_menu())

# =================== РЕЄСТРАЦІЯ ТА ДЕМОГРАФІЯ =========================

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup([[KeyboardButton("Поділитися номером", request_contact=True)]], resize_keyboard=True)
    await message.answer("👋 Вітаю! Поділіться номером для реєстрації:", reply_markup=kb)

@dp.message(lambda msg: msg.contact is not None)
async def contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    kb = ReplyKeyboardMarkup([[KeyboardButton("Чоловік")], [KeyboardButton("Жінка")]], resize_keyboard=True)
    vals = users_table.col_values(1)
    if str(user_id) in vals:
        await message.answer("Ви вже зареєстровані!", reply_markup=user_menu())
        return
    users_table.append_row([user_id, phone, "", "", "", ""])
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

# =================== КОРИСТУВАЧ МЕНЮ ===========================

@dp.message(lambda msg: msg.text == "Переглянути баланс")
async def balance(message: types.Message):
    await message.answer("Тут буде баланс (приклад)", reply_markup=user_menu())

@dp.message(lambda msg: msg.text == "Почати опитування")
async def poll_start(message: types.Message):
    # вибір активного опитування (номери таблиць)
    polls = ["1", "2"]
    kb = ReplyKeyboardMarkup([[KeyboardButton(f"Опитування {i}")] for i in polls], resize_keyboard=True)
    await message.answer("Оберіть дослідження:", reply_markup=kb)

@dp.message(lambda msg: msg.text.startswith("Опитування "))
async def poll_begin(message: types.Message):
    poll_id = message.text.split("Опитування ")[1].strip()
    # Категорія питань — для простоти приклад для двох:
    questions = {
        "1": ["Питання 1 (Опитування 1)", "Питання 2 (Опитування 1)"],
        "2": ["Питання 1 (Опитування 2)", "Питання 2 (Опитування 2)"]
    }
    dp.data.setdefault(message.from_user.id, {
        "poll_id": poll_id,
        "answers": [],
        "step": 0
    })
    await message.answer(questions[poll_id][0])

@dp.message(lambda msg: dp.data.get(msg.from_user.id, None))
async def poll_process(message: types.Message):
    user = dp.data[message.from_user.id]
    poll_id = user["poll_id"]
    questions = {
        "1": ["Питання 1 (Опитування 1)", "Питання 2 (Опитування 1)"],
        "2": ["Питання 1 (Опитування 2)", "Питання 2 (Опитування 2)"]
    }
    user["answers"].append(message.text)
    user["step"] += 1
    if user["step"] < len(questions[poll_id]):
        await message.answer(questions[poll_id][user["step"]])
    else:
        # Запис у відповідну таблицю
        table = open_answers_table(poll_id)
        vals = users_table.col_values(1)
        idx = vals.index(str(message.from_user.id)) + 1
        demo = users_table.row_values(idx)
        table.append_row([demo[0]] + user["answers"] + demo[1:])
        await message.answer("Дякуємо за участь!", reply_markup=user_menu())
        del dp.data[message.from_user.id]

# =================== АДМІН МЕНЮ ===========================

@dp.message(lambda msg: msg.text == "Учасники" and msg.from_user.id in ADMIN_IDS)
async def admin_users(message: types.Message):
    vals = users_table.get_all_values()
    text = "\n".join([f"{row[0]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}" for row in vals[1:]])
    await message.answer("Список учасників:\nuser_id | стать | рік | освіта | місце\n" + text, reply_markup=admin_menu())

@dp.message(lambda msg: msg.text == "Оглянути результати опитувань" and msg.from_user.id in ADMIN_IDS)
async def admin_results(message: types.Message):
    polls = ["1", "2"]
    kb = ReplyKeyboardMarkup([[KeyboardButton(f"Показати відповіді {i}")] for i in polls], resize_keyboard=True)
    await message.answer("Оберіть опитування:", reply_markup=kb)

@dp.message(lambda msg: msg.text.startswith("Показати відповіді") and msg.from_user.id in ADMIN_IDS)
async def admin_poll_view(message: types.Message):
    poll_id = message.text.split("Показати відповіді ")[1].strip()
    table = open_answers_table(poll_id)
    data = table.get_all_values()
    text = "\n".join([", ".join(row) for row in data[1:]])
    await message.answer(f"Відповіді по опитуванню {poll_id}:\n" + text, reply_markup=admin_menu())

@dp.message(lambda msg: msg.text == "Розіслати опитування" and msg.from_user.id in ADMIN_IDS)
async def admin_poll_send(message: types.Message):
    # Фільтр по місту/статі
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("Місто")], [KeyboardButton("Село")], [KeyboardButton("Чоловік")], [KeyboardButton("Жінка")], [KeyboardButton("Всі")]],
        resize_keyboard=True
    )
    await message.answer("Оберіть фільтр для розсилки:", reply_markup=kb)

@dp.message(lambda msg: msg.text in ["Місто", "Село", "Чоловік", "Жінка", "Всі"] and msg.from_user.id in ADMIN_IDS)
async def admin_send_to_filter(message: types.Message):
    vals = users_table.get_all_values()
    filter_type = message.text
    target_ids = []
    if filter_type == "Всі":
        target_ids = [row[0] for row in vals[1:]]
    elif filter_type in ["Місто", "Село"]:
        target_ids = [row[0] for row in vals[1:] if row[5] == filter_type]
    elif filter_type in ["Чоловік", "Жінка"]:
        target_ids = [row[0] for row in vals[1:] if row[2] == filter_type]
    # Розсилка
    for uid in target_ids:
        try:
            kb = ReplyKeyboardMarkup([[KeyboardButton("Почати опитування")]], resize_keyboard=True)
            await bot.send_message(uid, "Вас запрошено до нового опитування!", reply_markup=kb)
        except Exception:
            pass
    await message.answer(f"Розсилка виконана по фільтру: {filter_type}", reply_markup=admin_menu())

@dp.message(lambda msg: msg.text == "Експорт" and msg.from_user.id in ADMIN_IDS)
async def admin_export(message: types.Message):
    # Експорт GoogleSheet через pandas в Excel
    data = users_table.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    df.to_excel("users_export.xlsx", index=False)
    with open("users_export.xlsx", "rb") as f:
        await message.answer_document(types.FSInputFile(f), caption="Експорт демографії (Excel)")
    await message.answer("Готово!", reply_markup=admin_menu())

async def main():
    dp.data = {}
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
