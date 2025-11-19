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
— звичайно (далі по списку)."""
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
        # Створення анкети!
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
        # Додавання питання і подальших питань
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

# ------------- Огляд/редагування анкети перед розсилкою --------------
@dp.message(lambda msg: msg.text == "Оглянути/Редагувати анкету" and msg.from_user.id in ADMIN_IDS)
async def survey_view(msg: types.Message):
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    surveys = [f.replace("Answers_Survey_", "") for f in files]
    kb = ReplyKeyboardMarkup([[KeyboardButton(f"Огляд {s}")] for s in surveys], resize_keyboard=True)
    await msg.answer("Оберіть анкету:", reply_markup=kb)

@dp.message(lambda msg: msg.text.startswith("Огляд ") and msg.from_user.id in ADMIN_IDS)
async def survey_questions(msg: types.Message):
    sid = msg.text.replace("Огляд ", "")
    sheet = gs.open(f"Answers_Survey_{sid}").sheet1
    meta = sheet.row_values(2)
    questions = []
    for idx, v in enumerate(meta[1:], 1):
        if v:
            try:
                qobj = eval(v)
                logic = ""
                if qobj.get("exclusive"):
                    ex = qobj["exclusive"]
                    act = qobj["exclusive_action"]
                    nextq = qobj.get("exclusive_next")
                    logic = f" (Виключаюча: '{ex}', дія: {act}, наступне: {nextq})"
                questions.append(f"{idx}. {qobj['text']} | {qobj['type']} | Варіанти: {', '.join(qobj['options'])}{logic}")
            except: continue
    txt = "\n".join(questions) if questions else "Помилка анкети."
    await msg.answer(f"Питання анкети '{sid}':\n{txt}\n\nДля редагування — відправ потрібний текст/варіант, а далі повторно анкету.", reply_markup=admin_menu())

# ======== Розсилка з фільтром: місто / стать / діапазон років =======
@dp.message(lambda msg: msg.text == "Розіслати опитування" and msg.from_user.id in ADMIN_IDS)
async def admin_poll_send(message: types.Message):
    files = [f['name'] for f in gs.list_spreadsheet_files() if f['name'].startswith("Answers_Survey_")]
    if not files:
        await message.answer("Опитувань нема!")
        return
    surveys = [f.replace("Answers_Survey_", "") for f in files]
    kb = ReplyKeyboardMarkup([[KeyboardButton(f"Розіслати {i}")] for i in surveys], resize_keyboard=True)
    await message.answer("Оберіть опитування для розсилки:", reply_markup=kb)

@dp.message(lambda msg: msg.text.startswith("Розіслати ") and msg.from_user.id in ADMIN_IDS)
async def admin_send_with_filter(message: types.Message):
    poll_title = msg.text.split("Розіслати ")[1]
    kb = ReplyKeyboardMarkup([
        [KeyboardButton("Стать: Чоловік")],
        [KeyboardButton("Стать: Жінка")],
        [KeyboardButton("Місто")],
        [KeyboardButton("Село")],
        [KeyboardButton("Всі")],
        [KeyboardButton("Рік народження: діапазон")]
    ], resize_keyboard=True)
    dp.data[msg.from_user.id] = {"poll_title": poll_title}
    await msg.answer("Оберіть фільтр для розсилки:", reply_markup=kb)

@dp.message(lambda msg: msg.text.startswith("Рік народження:") and msg.from_user.id in ADMIN_IDS)
async def admin_filter_year(msg: types.Message):
    try:
        r = msg.text.split(":")[1].strip()
        s, e = [int(x.strip()) for x in r.split("-")]
        vals = users_table.get_all_values()
        target_ids = [row[0] for row in vals[1:] if s <= int(row[3]) <= e]
        poll_title = dp.data[msg.from_user.id]["poll_title"]
        for uid in target_ids:
            try:
                kb = ReplyKeyboardMarkup([[KeyboardButton(f"{poll_title}")]], resize_keyboard=True)
                await bot.send_message(uid, f"Запрошення до нового опитування!", reply_markup=kb)
            except Exception: pass
        await msg.answer("Розсилка виконана по діапазону років!", reply_markup=admin_menu())
        del dp.data[msg.from_user.id]
    except:
        await msg.answer("Помилка формату. Наприклад: Рік народження: 1981-1999")

@dp.message(lambda msg: (msg.text == "Всі" or msg.text.startswith("Стать:") or msg.text in ["Місто", "Село"]) and msg.from_user.id in ADMIN_IDS)
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

# ================= Користувач: проходження анкети (розгалуження по діях) ================
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
        sheet.append_row([demo[0]] + state["answers"] + demo[1:] + [str(REWARD_PER_SURVEY)])
        await message.answer(
            f"Дякуємо за участь!\n+{REWARD_PER_SURVEY} грн на баланс.",
            reply_markup=user_menu()
        )
        del dp.data[message.from_user.id]
        return
    q = state["questions"][state["step"]]
    kb = None
    if q["type"] == "multi":
        state["multi_temp"] = []
        state["exclusive"] = q.get("exclusive")
        state["exclusive_action"] = q.get("exclusive_action")
        state["exclusive_next"] = q.get("exclusive_next")
        kb = ReplyKeyboardMarkup([[KeyboardButton(opt)] for opt in q["options"]] + [[KeyboardButton("Завершити")]],
                                resize_keyboard=True)
        await message.answer(
            f"{q['text']} (Q{state['step']+1})\nОберіть один чи кілька, <Завершити> для завершення вибору\n"
            f"{'Виключаюча альтернатива: ' + q['exclusive'] if q.get('exclusive') else ''}",
            reply_markup=kb
        )
    else:
        kb = ReplyKeyboardMarkup([[KeyboardButton(opt)] for opt in q["options"]], resize_keyboard=True)
        state["exclusive"] = q.get("exclusive")
        state["exclusive_action"] = q.get("exclusive_action")
        state["exclusive_next"] = q.get("exclusive_next")
        await message.answer(f"{q['text']} (Q{state['step']+1})", reply_markup=kb)

@dp.message(lambda msg: dp.data.get(msg.from_user.id, None) and
    dp.data[msg.from_user.id]["questions"][dp.data[msg.from_user.id]["step"]]["type"] == "multi")
async def poll_multi_step(message: types.Message):
    state = dp.data[message.from_user.id]
    q = state["questions"][state["step"]]
    choice = message.text
    excl = state.get("exclusive")
    excl_action = state.get("exclusive_action")
    excl_next = state.get("exclusive_next")
    opts = q["options"]
    if choice == "Завершити":
        if not state["multi_temp"]:
            await message.answer("Оберіть хоча б один!")
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
        # Логіка для виключаючої: тут розгалуження
        if excl_action == "break":
            state["finish_text"] = (
                "Дякуємо за участь, але ви не підходите для цього опитування."
            )
        elif excl_action == "goto" and excl_next is not None:
            state["answers"].append(choice)
            state["step"] = excl_next - 1  # -1 бо step індекс з 0
        else:  # next — просто далі
            state["answers"].append(choice)
            state["step"] += 1
        await ask_next(message, state)
        return
    if excl and excl in state["multi_temp"]:
        await message.answer("Уже обрана виключаюча відповідь. Завершіть вибір!")
        return
    if choice in state["multi_temp"]:
        await message.answer("Уже вибрано.")
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
    excl_next = state.get("exclusive_next")
    if choice not in q["options"]:
        await message.answer("Оберіть із списку!")
        return
    if excl and choice == excl:
        if excl_action == "break":
            state["finish_text"] = (
                "Дякуємо за участь, але ви не підходите для цього опитування."
            )
        elif excl_action == "goto" and excl_next is not None:
            state["answers"].append(choice)
            state["step"] = excl_next - 1
        else:
            state["answers"].append(choice)
            state["step"] += 1
        await ask_next(message, state)
        return
    state["answers"].append(choice)
    state["step"] += 1
    await ask_next(message, state)

# ---------- Баланс (сума у Answers_Survey таблицях) ----------
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
                    try: total += float(v)
                    except: pass
    await message.answer(f"Ваш баланс: {total} грн", reply_markup=user_menu())

# ---------- Експорт ----------

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
