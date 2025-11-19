import logging
import asyncio
import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
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

# --------------- Реєстрація учасника -----------------
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

# -------------- Адмін меню ------------------------
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Меню адміністратора:", reply_markup=admin_menu())

# -------------- Автоматичне створення нового опитування & MULTI з виключаючою -------------
@dp.message(lambda msg: msg.text == "Створити опитування" and msg.from_user.id in ADMIN_IDS)
async def poll_create_start(message: types.Message):
    dp.data[message.from_user.id] = {"step": 0, "poll": {}}
    await message.answer("Введіть назву опитування:")

@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and "step" in dp.data.get(msg.from_user.id, {}))
async def poll_create_steps(message: types.Message):
    data = dp.data[message.from_user.id]
    poll = data["poll"]
    if data["step"] == 0:
        poll['title'] = message.text
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
        await message.answer("Введіть варіанти відповіді через кому (для мультивибору виключаючу альтернативу додати через '!').\nНаприклад: Варіант1, Варіант2, Інше, Жодного!")
        data["step"] = 4
        return
    if data["step"] == 4:
        opts_raw = [o.strip() for o in message.text.split(",")]
        opts, excl = [], None
        for o in opts_raw:
            if o.endswith("!"):
                excl = o.rstrip("!").strip()
                opts.append(excl)
            else:
                opts.append(o)
        q = {
            "text": poll['qbuf']['text'],
            "type": poll['qbuf']['type'],
            "options": opts
        }
        if excl and poll['qbuf']['type'] == "multi":
            q["exclusive"] = excl
        poll["questions"].append(q)
        poll["current"] += 1
        if poll["current"] < poll["n"]:
            data["step"] = 2
            await message.answer(f"Введіть текст питання №{poll['current']+1}:")
            return
        # Створення таблиці!
        file_title = f"Answers_Survey_{poll['title']}"
        sheet = gs.create(file_title)
        sheet.share(creds.service_account_email, perm_type="user", role="writer")
        ws = sheet.get_worksheet(0)
        ws.append_row(
            ["user_id"] + [q["text"] for q in poll["questions"]] +
            ["phone", "sex", "birth_year", "education", "residence"]
        )
        ws.append_row(
            ["meta"] + [str(q) for q in poll["questions"]]
        )
        await message.answer(f"Опитування створено!\nТаблиця: {file_title}", reply_markup=admin_menu())
        del dp.data[message.from_user.id]

# ------------- Користувачі: старт та мультивибір -----------------
@dp.message(lambda msg: msg.text == "Почати опитування")
async def poll_start(message: types.Message):
    # шукаємо всі Answers_Survey_X
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
        "exclusive": None
    }
    await ask_next(message, dp.data[message.from_user.id])

async def ask_next(message, state):
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
        kb = ReplyKeyboardMarkup([[KeyboardButton(opt)] for opt in q["options"]] + [[KeyboardButton("Завершити")]],
                                resize_keyboard=True)
        await message.answer(
            f"{q['text']} (Оберіть один чи кілька, <Завершити> для завершення вибору)\n"
            f"{'Виключаюча альтернатива: ' + q['exclusive'] if q.get('exclusive') else ''}",
            reply_markup=kb
        )
    else:
        kb = ReplyKeyboardMarkup([[KeyboardButton(opt)] for opt in q["options"]], resize_keyboard=True)
        await message.answer(q["text"], reply_markup=kb)

@dp.message(lambda msg: dp.data.get(msg.from_user.id, None) and
                       dp.data[msg.from_user.id]["questions"][dp.data[msg.from_user.id]["step"]]["type"] == "multi")
async def poll_multi_step(message: types.Message):
    state = dp.data[message.from_user.id]
    q = state["questions"][state["step"]]
    choice = message.text
    excl = state.get("exclusive")
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
        await message.answer("Оберіть один із варіантів!")
        return
    if excl and choice == excl:
        if state["multi_temp"]:
            await message.answer(f"Ви не можете обрати {excl} з іншими відповідями!")
            return
        state["multi_temp"].append(choice)
        state["answers"].append(choice)
        state["step"] += 1
        await ask_next(message, state)
        return
    if excl and excl in state["multi_temp"]:
        await message.answer("Ви вже обрали виключаючу альтернативу. Скиньте вибір <Завершити>!")
        return
    if choice in state["multi_temp"]:
        await message.answer("Уже вибрано!")
        return
    state["multi_temp"].append(choice)

@dp.message(lambda msg: dp.data.get(msg.from_user.id, None) and
                       dp.data[msg.from_user.id]["questions"][dp.data[msg.from_user.id]["step"]]["type"] == "radio")
async def poll_radio_step(message: types.Message):
    state = dp.data[message.from_user.id]
    q = state["questions"][state["step"]]
    choice = message.text
    if choice not in q["options"]:
        await message.answer("Оберіть один із варіантів!")
        return
    state["answers"].append(choice)
    state["step"] += 1
    await ask_next(message, state)

async def main():
    dp.data = {}
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
