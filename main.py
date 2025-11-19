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

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDENTIALS_PATH = "/etc/secrets/credentials"  # ключ із Render Secret Files
creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
gs = gspread.authorize(creds)
USERS_SHEET = "Users"
users_table = gs.open(USERS_SHEET).sheet1

REWARD_PER_SURVEY = 10  # сума за проходження опитування, змінюється адміном

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

# ========= Адмін: Створення опитування з логікою переходів =========
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Меню адміністратора:", reply_markup=admin_menu())

@dp.message(lambda msg: msg.text == "Створити опитування" and msg.from_user.id in ADMIN_IDS)
async def poll_create_start(message: types.Message):
    dp.data[message.from_user.id] = {"step": 0, "poll": [], "title": None}
    await message.answer("Введіть назву опитування:")

@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and "step" in dp.data.get(msg.from_user.id, {}))
async def poll_create_steps(message: types.Message):
    state = dp.data[message.from_user.id]
    if state["step"] == 0:
        state["title"] = message.text.strip()
        state["step"] = 1
        await message.answer("Скільки питань? (число)")
        return
    if state["step"] == 1:
        try:
            state["n"] = int(message.text)
            state["num"] = 1
            state["step"] = 2
            await message.answer(f"Введіть текст питання №{state['num']} (далі лише через кнопки-кроки):")
        except:
            await message.answer("Введіть число!")
        return
    # Поетапно: питання, тип, варіанти, логіка переходу (для виключаючої)
    if state["step"] == 2:
        state.setdefault("qbuf", {})
        state["qbuf"]["text"] = message.text.strip()
        kb = ReplyKeyboardMarkup([[KeyboardButton("Один вибір")], [KeyboardButton("Мультивибір")]], resize_keyboard=True)
        state["step"] = 3
        await message.answer("Тип питання:", reply_markup=kb)
        return
    if state["step"] == 3:
        tp = "multi" if "мульти" in message.text.lower() else "radio"
        state["qbuf"]["type"] = tp
        await message.answer(
"""Введіть варіанти через кому. ВИКЛЮЧАЮЧУ опцію — через '!' (Напр: Вар1, Вар2, Інше, Не підходить!).
Бот запитає дію ПІД ЧАС створення виключаючої: 
— завершити опитування/показати текст,
— перейти до №питання,
— далі по списку."""
        )
        state["step"] = 4
        return
    if state["step"] == 4:
        opts_raw = [o.strip() for o in message.text.split(",")]
        opts, excl = [], None
        for o in opts_raw:
            if o.endswith("!"):
                excl = o.rstrip("!").strip()
                opts.append(excl)
            else:
                opts.append(o)
        state["qbuf"]["options"] = opts
        state["excl"] = excl
        if excl:
            kb = ReplyKeyboardMarkup([
                [KeyboardButton("Завершити анкету")],
                [KeyboardButton("Перейти до питання №")],
                [KeyboardButton("Далі по списку")]
            ], resize_keyboard=True)
            state["step"] = 5
            await message.answer(f"Дія якщо вибрано '{excl}':", reply_markup=kb)
            return
        # якщо нема виключаючої — завершити додавання питання
        state["qbuf"]["exclusive"] = None
        state["qbuf"]["exclusive_action"] = None
        state["qbuf"]["exclusive_next"] = None
        state["poll"].append(state["qbuf"])
        state["num"] += 1
        if state["num"] <= state["n"]:
            state["step"] = 2
            await message.answer(f"Введіть текст питання №{state['num']}:")
            state["qbuf"] = {}
            return
        create_survey(message, state)
        return
    if state["step"] == 5:  # логіка для виключаючої
        act = message.text.lower()
        next_id = ""
        if "питання" in act:
            await message.answer("Вкажіть номер питання для переходу:")
            state["step"] = 6
            return
        if "завершити" in act:
            state["qbuf"]["exclusive"] = state["excl"]
            state["qbuf"]["exclusive_action"] = "break"
            state["qbuf"]["exclusive_next"] = None
        else:
            state["qbuf"]["exclusive"] = state["excl"]
            state["qbuf"]["exclusive_action"] = "next"
            state["qbuf"]["exclusive_next"] = None
        state["poll"].append(state["qbuf"])
        state["num"] += 1
        if state["num"] <= state["n"]:
            state["step"] = 2
            await message.answer(f"Введіть текст питання №{state['num']}:")
            state["qbuf"] = {}
            return
        create_survey(message, state)
        return
    if state["step"] == 6:
        try:
            next_id = int(message.text.strip())
            state["qbuf"]["exclusive"] = state["excl"]
            state["qbuf"]["exclusive_action"] = "goto"
            state["qbuf"]["exclusive_next"] = next_id
        except:
            await message.answer("Вкажіть коректний номер питання!")
            return
        state["poll"].append(state["qbuf"])
        state["num"] += 1
        if state["num"] <= state["n"]:
            state["step"] = 2
            await message.answer(f"Введіть текст питання №{state['num']}:")
            state["qbuf"] = {}
            return
        create_survey(message, state)

def create_survey(message, state):
    poll_questions = state["poll"]
    title = state["title"]
    sheet_title = f"Answers_Survey_{title}"
    sheet = gs.create(sheet_title)
    sheet.share(creds.service_account_email, perm_type="user", role="writer")
    ws = sheet.get_worksheet(0)
    ws.append_row(
        ["user_id"] + [f"Q{idx+1}: {q['text']}" for idx, q in enumerate(poll_questions)] +
        ["phone", "sex", "birth_year", "education", "residence"]
    )
    ws.append_row(["meta"] + [str(q) for q in poll_questions])
    message.answer(f"Анкета створена!\nПеред розсилкою натисни “Оглянути/Редагувати анкету” щоб переглянути/змінити логіку.", reply_markup=admin_menu())
    del dp.data[message.from_user.id]

# Далі весь код як у попередній роботі: проходження анкет, розсилка, експорт, баланс...
# (Залиш усе інше без змін; головне — шлях CREDENTIALS_PATH !)
# Тобі потрібно просто скопіювати цей main.py і перезапустити Render!
