import logging
import asyncio

import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = "8330526731:AAHzpqLfO0JewWvH0msy1FF-Hk0IBYJDN8M"
ADMIN_IDS = [383222956, 233536337]

# ------------ GOOGLE SHEETS ------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_PATH = "/etc/secrets/credentials"

creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
gs = gspread.authorize(creds)

USERS_SHEET = "Users"
users_table = gs.open(USERS_SHEET).sheet1

POLLS_SHEET = "Polls"  # таблица со списком опросов и их структурой
try:
    polls_table = gs.open(POLLS_SHEET).sheet1
except gspread.SpreadsheetNotFound:
    sh = gs.create(POLLS_SHEET)
    sh.share(creds.service_account_email, perm_type="user", role="writer")
    polls_table = sh.sheet1
    polls_table.append_row(["poll_id", "title", "questions_json"])

# ------------ BOT ------------

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.data = {}


def admin_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити опитування")],
            [KeyboardButton(text="Оглянути/Редагувати анкету")],
            [KeyboardButton(text="Розіслати опитування")],
            [KeyboardButton(text="Експорт відповідей")],
            [KeyboardButton(text="Статистика")],
        ],
        resize_keyboard=True,
    )
    return kb


def user_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Почати опитування")],
            [KeyboardButton(text="Переглянути баланс")],
        ],
        resize_keyboard=True,
    )
    return kb


# ------------ РЕЄСТРАЦІЯ В Users ------------

@dp.message(Command("start"))
async def start(message: types.Message):
    logger.info("Received /start from %s", message.from_user.id)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
    )
    await message.answer("👋 Вітаю! Поділіться номером для реєстрації:", reply_markup=kb)


@dp.message(lambda msg: msg.contact is not None)
async def contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    logger.info("Got contact from %s: %s", user_id, phone)

    vals = users_table.col_values(1)
    if str(user_id) in vals:
        await message.answer("Ви вже зареєстровані ✅", reply_markup=user_menu())
        return

    # user_id, phone, sex, birth_year, education, residence_type, city_size
    users_table.append_row([user_id, phone, "", "", "", "", ""])
    logger.info("User %s added to Users sheet", user_id)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Чоловік")],
            [KeyboardButton(text="Жінка")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Ваша стать?", reply_markup=kb)


@dp.message(lambda msg: msg.text in ["Чоловік", "Жінка"])
async def input_sex(message: types.Message):
    user_id = message.from_user.id
    sex = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 3, sex)
    logger.info("User %s sex saved: %s", user_id, sex)
    await message.answer("Ваш рік народження?", reply_markup=ReplyKeyboardRemove())


@dp.message(lambda msg: msg.text.isdigit() and 1920 < int(msg.text) < 2020)
async def input_birth(message: types.Message):
    user_id = message.from_user.id
    birth_year = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 4, birth_year)
    logger.info("User %s birth_year saved: %s", user_id, birth_year)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Середня")],
            [KeyboardButton(text="Вища")],
            [KeyboardButton(text="Учена ступінь")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Ваша освіта?", reply_markup=kb)


@dp.message(lambda msg: msg.text in ["Середня", "Вища", "Учена ступінь"])
async def input_education(message: types.Message):
    user_id = message.from_user.id
    edu = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 5, edu)
    logger.info("User %s education saved: %s", user_id, edu)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Місто")],
            [KeyboardButton(text="Село")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Місце проживання?", reply_markup=kb)


@dp.message(lambda msg: msg.text in ["Місто", "Село"])
async def input_residence_type(message: types.Message):
    user_id = message.from_user.id
    residence_type = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 6, residence_type)
    logger.info("User %s residence type saved: %s", user_id, residence_type)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="До 10 тис.")],
            [KeyboardButton(text="10–50 тис.")],
            [KeyboardButton(text="50–100 тис.")],
            [KeyboardButton(text="100–500 тис.")],
            [KeyboardButton(text="500 тис.–1 000 000")],
            [KeyboardButton(text="Більше 1 000 000")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Розмір населеного пункту?", reply_markup=kb)


@dp.message(lambda msg: msg.text in [
    "До 10 тис.",
    "10–50 тис.",
    "50–100 тис.",
    "100–500 тис.",
    "500 тис.–1 000 000",
    "Більше 1 000 000",
])
async def input_city_size(message: types.Message):
    user_id = message.from_user.id
    city_size = message.text
    vals = users_table.col_values(1)
    if str(user_id) not in vals:
        await message.answer("Спочатку натисніть /start і поділіться номером.")
        return
    row = vals.index(str(user_id)) + 1
    users_table.update_cell(row, 7, city_size)
    logger.info("User %s city_size saved: %s", user_id, city_size)

    await message.answer("Реєстрація завершена ✅", reply_markup=user_menu())


# ------------ АДМІН: СТВОРЕННЯ ОПИТУВАННЯ ------------

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Адмін-меню:", reply_markup=admin_menu())


@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and msg.text == "Створити опитування")
async def create_poll_start(message: types.Message):
    dp.data[message.from_user.id] = {"step": "title", "poll": {"questions": []}}
    await message.answer("Введіть назву опитування:", reply_markup=ReplyKeyboardRemove())


@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and dp.data.get(msg.from_user.id, {}).get("step") == "title")
async def create_poll_set_title(message: types.Message):
    state = dp.data[message.from_user.id]
    state["poll"]["title"] = message.text.strip()
    state["step"] = "count"
    await message.answer("Скільки питань буде в опитуванні? Введіть число.")


@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and dp.data.get(msg.from_user.id, {}).get("step") == "count")
async def create_poll_set_count(message: types.Message):
    state = dp.data[message.from_user.id]
    try:
        n = int(message.text)
        state["poll"]["n"] = n
        state["poll"]["qidx"] = 1
        state["step"] = "q_text"
        await message.answer("Введіть текст питання №1:")
    except ValueError:
        await message.answer("Введіть, будь ласка, число.")


@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and dp.data.get(msg.from_user.id, {}).get("step") == "q_text")
async def create_poll_q_text(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    poll.setdefault("qbuf", {})
    poll["qbuf"]["text"] = message.text.strip()
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Один вибір")],
            [KeyboardButton(text="Мультивибір")],
        ],
        resize_keyboard=True,
    )
    state["step"] = "q_type"
    await message.answer("Тип питання:", reply_markup=kb)


@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and dp.data.get(msg.from_user.id, {}).get("step") == "q_type")
async def create_poll_q_type(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    text = message.text.lower()
    poll["qbuf"]["type"] = "multi" if "мульти" in text else "radio"
    await message.answer("Введіть варіанти відповіді через кому. Виключаючу опцію позначте знаком '!' в кінці.")
    state["step"] = "q_options"


@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and dp.data.get(msg.from_user.id, {}).get("step") == "q_options")
async def create_poll_q_options(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    opts_raw = [o.strip() for o in message.text.split(",")]
    opts, excl = [], None
    for o in opts_raw:
        if o.endswith("!"):
            excl = o.rstrip("!").strip()
            opts.append(excl)
        else:
            opts.append(o)

    q = {
        "text": poll["qbuf"]["text"],
        "type": poll["qbuf"]["type"],
        "options": opts,
    }
    if excl and poll["qbuf"]["type"] == "multi":
        q["exclusive"] = excl

    poll["questions"].append(q)
    poll["qidx"] += 1

    if poll["qidx"] <= poll["n"]:
        poll["qbuf"] = {}
        state["step"] = "q_text"
        await message.answer(f"Введіть текст питання №{poll['qidx']}:")
        return

    # Зберігаємо структуру опитування в таблицю Polls
    import json
    poll_id = polls_table.row_count
    polls_table.append_row([poll_id, poll["title"], json.dumps(poll["questions"], ensure_ascii=False)])
    await message.answer(f"Опитування '{poll['title']}' створено і збережено в Polls.", reply_markup=admin_menu())
    del dp.data[message.from_user.id]


# ------------ КНОПКИ КОРИСТУВАЧА (заглушки поки що) ------------

@dp.message(lambda msg: msg.text == "Почати опитування")
async def user_start_poll(message: types.Message):
    await message.answer("Функція проходження опитувань буде додана пізніше. Зараз реєстрація вже працює.", reply_markup=user_menu())


@dp.message(lambda msg: msg.text == "Переглянути баланс")
async def user_balance(message: types.Message):
    await message.answer("Баланс ще не рахуємо. Цю функцію додамо після підключення відповідей по опитуванням.", reply_markup=user_menu())


# ------------ ЗАПАСНИЙ ECHO ДЛЯ УСЬОГО ІНШОГО ------------

@dp.message()
async def fallback(message: types.Message):
    logger.info("Fallback message from %s: %s", message.from_user.id, message.text)
    await message.answer("Команда не розпізнана. Використовуйте меню або /start.")


# ------------ ЗАПУСК ------------

async def main():
    logger.info("Bot starting with registration, city size & admin poll creation...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception("Bot crashed with exception: %s", e)


if __name__ == "__main__":
    logger.info("main.py __name__ == '__main__', starting asyncio.run")
    asyncio.run(main())
