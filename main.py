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
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
gs = gspread.authorize(creds)
USERS_SHEET = "Users"
users_table = gs.open(USERS_SHEET).sheet1

def admin_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Створити опитування")],
            [KeyboardButton("Оглянути опитування")],
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

# ------------- Адмін меню ---------------
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Меню адміністратора:", reply_markup=admin_menu())

# ------- Створення нового опитування з розгалуженням по унікальній альтернативі
@dp.message(lambda msg: msg.text == "Створити опитування" and msg.from_user.id in ADMIN_IDS)
async def poll_create_start(message: types.Message):
    dp.data[message.from_user.id] = {"step": 0, "poll": {}}
    await message.answer("Введіть назву опитування:")

@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and "step" in dp.data.get(msg.from_user.id, {}))
async def poll_create_steps(message: types.Message):
    data = dp.data[message.from_user.id]
    poll = data["poll"]
    if data["step"] == 0:
        poll['title'] = message.text.strip()
        poll['questions'] = []
        data["step"] = 1
        await message.answer("Скільки питань? (число)")
        return
    if data["step"] == 1:
        try:
            poll['n'] = int(message.text)
            poll['current'] = 0
            data["step"] = 2
            await message.answer(f"Введіть текст питання № 1:")
        except:
            await message.answer("Введіть число!")
        return
    if data["step"] == 2:
        poll.setdefault('qbuf', {})
        poll['qbuf']['text'] = message.text
        kb = ReplyKeyboardMarkup([
            [KeyboardButton("Один вибір")], [KeyboardButton("Мультивибір")]
        ], resize_keyboard=True)
        data["step"] = 3
        await message.answer("Виберіть тип питання:", reply_markup=kb)
        return
    if data["step"] == 3:
        poll['qbuf']['type'] = "multi" if "мульти" in message.text.lower() else "radio"
        await message.answer(
"""Введіть варіанти відповіді через кому.
Для виключаючої альтернативи додайте ! (наприклад: Варіант1, Варіант2, Інше, “Жодного!”).
Після цього позначте дію ПІСЛЯ вибору виключаючої альтернативи:
— не дійте (звичайний варіант),
— перейти до наступного питання,
— завершити опитування (“ви не підходите для цього дослідження”).
""")
        data["step"] = 4
        return
    if data["step"] == 4:
        # Маємо: варіанти + розгалуження
        if "->" in message.text:
            opts_part, logic_part = message.text.split("->", 1)
        else:
            opts_part = message.text
            logic_part = "next"
        opts_raw = [o.strip() for o in opts_part.split(",")]
        opts, excl = [], None
        for o in opts_raw:
            if o.endswith("!"):
                excl = o.rstrip("!").strip()
                opts.append(excl)
            else:
                opts.append(o)
        logic = logic_part.strip().lower()
        q = {
            "text": poll['qbuf']['text'],
            "type": poll['qbuf']['type'],
            "options": opts
        }
        # Якщо є виключаюча опція — підключити логіку:
        if excl:
            q["exclusive"] = excl
            if "заверш" in logic or "ви не підходите" in logic:
                q["exclusive_action"] = "break"
            elif "наступ" in logic or "next" in logic:
                q["exclusive_action"] = "next"
            else:
                q["exclusive_action"] = "simple"
        poll["questions"].append(q)
        poll["current"] += 1
        if poll["current"] < poll["n"]:
            data["step"] = 2
            await message.answer(f"Введіть текст питання №{poll['current']+1}:")
            return
        # Створити таблицю!
        file_title = f"Answers_Survey_{poll['title']}"
        sheet = gs.create(file_title)
        sheet.share(creds.service_account_email, perm_type="user", role="writer")
        ws = sheet.get_worksheet(0)
        ws.append_row(
            ["user_id"] + [q["text"] for q in poll["questions"]] +
            ["phone", "sex", "birth_year", "education", "residence"]
        )
        ws.append_row(["meta"] + [str(q) for q in poll["questions"]])
        await message.answer(f"Опитування створено!\nТаблиця: {file_title}", reply_markup=admin_menu())
        del dp.data[message.from_user.id]

# ----------- Фільтрована розсилка (місто, стать) ---------------
@dp.message(lambda msg: msg.text == "Розіслати опитування" and msg.from_user.id in ADMIN_IDS)
async def admin_poll_send(message: types.Message):
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    if not files:
        await message.answer("Опитувань нема!")
        return
    polls = [f.replace("Answers_Survey_", "") for f in files]
    kb = ReplyKeyboardMarkup([[KeyboardButton(f"Розіслати {i}")] for i in polls], resize_keyboard=True)
    await message.answer("Оберіть опитування для розсилки:", reply_markup=kb)

@dp.message(lambda msg: msg.text.startswith("Розіслати ") and msg.from_user.id in ADMIN_IDS)
async def admin_send_with_filter(message: types.Message):
    poll_title = msg.text.split("Розіслати ")[1]
    kb = ReplyKeyboardMarkup(
        [
            [KeyboardButton("Стать: Чоловік")],
            [KeyboardButton("Стать: Жінка")],
            [KeyboardButton("Місто")],
            [KeyboardButton("Село")],
            [KeyboardButton("Всі")]
        ],
        resize_keyboard=True
    )
    dp.data[msg.from_user.id] = {"poll_title": poll_title}
    await msg.answer("Оберіть фільтр для розсилки:", reply_markup=kb)

@dp.message(lambda msg: msg.text.startswith("Стать:") or msg.text in ["Місто", "Село", "Всі"] and msg.from_user.id in ADMIN_IDS)
async def admin_send_filtered(msg: types.Message):
    poll_title = dp.data[msg.from_user.id]["poll_title"]
    vals = users_table.get_all_values()
    if msg.text == "Всі":
        target_ids = [row[0] for row in vals[1:]]
    elif msg.text.startswith("Стать:"):
        gen = msg.text.split(":")[1].strip()
        target_ids = [row[0] for row in vals[1:] if row[2]==gen]
    else:
        loc = msg.text
        target_ids = [row[0] for row in vals[1:] if row[5]==loc]
    for uid in target_ids:
        try:
            kb = ReplyKeyboardMarkup([[KeyboardButton(f"{poll_title}")]], resize_keyboard=True)
            await bot.send_message(uid, f"Запрошення до нового опитування!", reply_markup=kb)
        except Exception: pass
    await msg.answer("Розсилка виконана!", reply_markup=admin_menu())
    del dp.data[msg.from_user.id]

# ------------ Почати опитування (для користувача) ---------------
@dp.message(lambda msg: msg.text == "Почати опитування")
async def poll_start(message: types.Message):
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    if not files:
        await message.answer("Немає активних опитувань.")
        return
    kb = ReplyKeyboardMarkup([[KeyboardButton(f"{name.replace('Answers_Survey_', '')}")] for name in files], resize_keyboard=True)
    await message.answer("Оберіть опитування:", reply_markup=kb)

@dp.message(lambda msg: any(msg.text == f['name'].replace('Answers_Survey_', '') for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")))
async def poll_process(message: types.Message):
    poll_sheet_name = f"Answers_Survey_{message.text}"
    sheet = gs.open(poll_sheet_name).sheet1
    meta = sheet.row_values(2)
    questions = []
    for v in meta[1:]:
        if v:
            try:
                qobj = eval(v)
                questions.append(qobj)
            except: continue
    dp.data[message.from_user.id] = {
        "poll_sheet": poll_sheet_name,
        "questions": questions,
        "answers": [],
        "step": 0,
        "multi_temp": [],
        "exclusive": None,
        "finish_text": None
    }
    await ask_next(message, dp.data[message.from_user.id])

async def ask_next(message, state):
    if state["finish_text"]:
        kb = ReplyKeyboardMarkup([[KeyboardButton("Переглянути баланс")]], resize_keyboard=True)
        await message.answer(state["finish_text"], reply_markup=kb)
        del dp.data[message.from_user.id]
        return
    if state["step"] >= len(state["questions"]):
        poll_sheet = state["poll_sheet"]
        vals = users_table.col_values(1)
        idx = vals.index(str(message.from_user.id)) + 1
        demo = users_table.row_values(idx)
        sheet = gs.open(poll_sheet).sheet1
        sheet.append_row([demo[0]] + state["answers"] + demo[1:])
        await message.answer("Дякуємо за участь!", reply_markup=user_menu())
        del dp.data[message.from_user.id]
        return
    q = state["questions"][state["step"]]
    kb = None
    if q["type"] == "multi":
        state["multi_temp"] = []
        state["exclusive"] = q.get("exclusive")
        state["exclusive_action"] = q.get("exclusive_action")
        kb = ReplyKeyboardMarkup([[KeyboardButton(opt)] for opt in q["options"]] + [[KeyboardButton("Завершити")]],
                                resize_keyboard=True)
        await message.answer(
            f"{q['text']} (Оберіть один чи кілька, <Завершити> для завершення вибору)\n"
            f"{'Виключаюча альтернатива: ' + q['exclusive'] if q.get('exclusive') else ''}",
            reply_markup=kb
        )
    else:
        kb = ReplyKeyboardMarkup([[KeyboardButton(opt)] for opt in q["options"]], resize_keyboard=True)
        state["exclusive"] = q.get("exclusive")
        state["exclusive_action"] = q.get("exclusive_action")
        await message.answer(q["text"], reply_markup=kb)

@dp.message(lambda msg: dp.data.get(msg.from_user.id, None) and
                       dp.data[msg.from_user.id]["questions"][dp.data[msg.from_user.id]["step"]]["type"] == "multi")
async def poll_multi_step(message: types.Message):
    state = dp.data[message.from_user.id]
    q = state["questions"][state["step"]]
    choice = message.text
    excl = state.get("exclusive")
    excl_action = state.get("exclusive_action")
    opts = q["options"]
    if choice == "Завершити":
        if not state["multi_temp"]:
            await message.answer("Оберіть хоча б один варіант!")
            return
        state["answers"].append(", ".join(state["multi_temp"]))
        state["step"] += 1
        await ask_next(message, state)
        return
    if choice not in opts:
        await message.answer("Оберіть із списку!")
        return
    if excl and choice == excl:
        if state["multi_temp"]:
            await message.answer(f"Ви не можете обрати '{excl}' разом із іншими варіантами!")
            return
        state["multi_temp"].append(choice)
        # Логіка: яку дію вибрав адмін?
        if excl_action == "break":
            state["finish_text"] = (
                "Дякуємо за участь в опитуванні, але ви не підходите для цього дослідження.\n"
                "Нагадуємо, що ви можете переглянути свій баланс."
            )
            await ask_next(message, state)
            return
        elif excl_action == "next":
            state["answers"].append(choice)
            state["step"] += 1
            await ask_next(message, state)
            return
        else:  # simple — як звичайно, просто залік
            state["answers"].append(choice)
            state["step"] += 1
            await ask_next(message, state)
            return
    if excl and excl in state["multi_temp"]:
        await message.answer("Ви вже обрали виключаючу відповідь. Натисніть <Завершити>!")
        return
    if choice in state["multi_temp"]:
        await message.answer("Варіант уже вибрано. Натисніть <Завершити> або ще виберіть!")
        return
    state["multi_temp"].append(choice)

@dp.message(lambda msg: dp.data.get(msg.from_user.id, None) and
                       dp.data[msg.from_user.id]["questions"][dp.data[msg.from_user.id]["step"]]["type"] == "radio")
async def poll_radio_step(message: types.Message):
    state = dp.data[message.from_user.id]
    q = state["questions"][state["step"]]
    choice = message.text
    excl = state.get("exclusive")
    excl_action = state.get("exclusive_action")
    if choice not in q["options"]:
        await message.answer("Оберіть із списку!")
        return
    if excl and choice == excl:
        if excl_action == "break":
            state["finish_text"] = (
                "Дякуємо за участь в опитуванні, але ви не підходите для цього опитування.\n"
                "Нагадуємо, що ви можете переглянути свій баланс."
            )
            await ask_next(message, state)
            return
        elif excl_action == "next":
            state["answers"].append(choice)
            state["step"] += 1
            await ask_next(message, state)
            return
    state["answers"].append(choice)
    state["step"] += 1
    await ask_next(message, state)

# ------------------ Переглянути баланс ------------------------
@dp.message(lambda msg: msg.text == "Переглянути баланс")
async def balance(message: types.Message):
    # Можеш додати тут підрахунок через Google Sheets
    await message.answer("Ваш баланс: [Тут буде баланс/сума]", reply_markup=user_menu())

# --------- Оглянути опитування, статистика та експорт ----------
@dp.message(lambda msg: msg.text == "Оглянути опитування" and msg.from_user.id in ADMIN_IDS)
async def admin_poll_list(msg: types.Message):
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    polls = [f.replace("Answers_Survey_", "") for f in files]
    text = "\n".join(polls) if polls else "Немає опитувань."
    await msg.answer(f"Опитування:\n{text}", reply_markup=admin_menu())

@dp.message(lambda msg: msg.text == "Експорт відповідей" and msg.from_user.id in ADMIN_IDS)
async def export_answers(msg: types.Message):
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    for poll in files:
        sheet = gs.open(poll).sheet1
        data = sheet.get_all_values()
        df = pd.DataFrame(data[2:], columns=data[0])  # Відкидаємо meta
        fname = f"export_{poll}.xlsx"
        df.to_excel(fname, index=False)
        with open(fname, "rb") as f:
            await msg.answer_document(FSInputFile(f), caption=f"Відповіді: {poll}")
    await msg.answer("Експорт завершено!", reply_markup=admin_menu())

@dp.message(lambda msg: msg.text == "Статистика" and msg.from_user.id in ADMIN_IDS)
async def admin_stats(msg: types.Message):
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    txts = []
    for poll in files:
        sheet = gs.open(poll).sheet1
        data = sheet.get_all_values()
        cnt = len(data[2:])
        txts.append(f"{poll.replace('Answers_Survey_', '')}: Відповідей — {cnt}")
    await msg.answer("\n".join(txts), reply_markup=admin_menu())


async def main():
    dp.data = {}
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
