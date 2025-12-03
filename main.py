import logging
import asyncio
import json

import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = "8330526731:AAEzeStk08GKV-ETRmLnERadgtyEfgldqCE"
ADMIN_IDS = [383222956, 233536337]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_PATH = "/etc/secrets/credentials"

creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
gs = gspread.authorize(creds)

USERS_SHEET = "Users"
users_table = gs.open(USERS_SHEET).sheet1

# Polls: poll_id | code | title | reward | questions_json
POLLS_SHEET = "Polls"
polls_table = gs.open(POLLS_SHEET).sheet1

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.data = {}


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити опитування")],
            [KeyboardButton(text="Розіслати опитування")],
            [KeyboardButton(text="Оглянути/Редагувати анкету")],
            [KeyboardButton(text="Експорт відповідей")],
            [KeyboardButton(text="Статистика")],
        ],
        resize_keyboard=True,
    )


def user_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Почати опитування")],
            [KeyboardButton(text="Переглянути баланс")],
        ],
        resize_keyboard=True,
    )


# ---------- РЕЄСТРАЦІЯ ----------

@dp.message(Command("start"))
async def start(message: types.Message):
    logger.info("Received /start from %s", message.from_user.id)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
    )
    await message.answer("👋 Вітаю! Поділіться номером для реєстрації:", reply_markup=kb)


@dp.message(lambda m: m.contact is not None)
async def contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    logger.info("Got contact from %s: %s", user_id, phone)

    vals = users_table.col_values(1)
    if str(user_id) in vals:
        await message.answer("Ви вже зареєстровані ✅", reply_markup=user_menu())
        return

    users_table.append_row([user_id, phone, "", "", "", "", ""])
    logger.info("User %s added to Users sheet", user_id)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Чоловік")], [KeyboardButton(text="Жінка")]],
        resize_keyboard=True,
    )
    await message.answer("Ваша стать?", reply_markup=kb)


@dp.message(lambda m: m.text in ["Чоловік", "Жінка"])
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


@dp.message(lambda m: m.text.isdigit() and 1920 < int(m.text) < 2020)
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


@dp.message(lambda m: m.text in ["Середня", "Вища", "Учена ступінь"])
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
        keyboard=[[KeyboardButton(text="Місто")], [KeyboardButton(text="Село")]],
        resize_keyboard=True,
    )
    await message.answer("Місце проживання?", reply_markup=kb)


@dp.message(lambda m: m.text in ["Місто", "Село"])
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


CITY_SIZES = [
    "До 10 тис.",
    "10–50 тис.",
    "50–100 тис.",
    "100–500 тис.",
    "500 тис.–1 000 000",
    "Більше 1 000 000",
]


@dp.message(lambda m: m.text in CITY_SIZES)
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


# ---------- АДМІН: ОПИТУВАННЯ (code + title + reward) ----------

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Адмін-меню:", reply_markup=admin_menu())


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and m.text == "Створити опитування")
async def create_poll_start(message: types.Message):
    dp.data[message.from_user.id] = {"step": "code", "poll": {"questions": []}}
    await message.answer("Введіть числовий код опитування (наприклад, 126):", reply_markup=ReplyKeyboardRemove())


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "code")
async def create_poll_set_code(message: types.Message):
    state = dp.data[message.from_user.id]
    if not message.text.isdigit():
        await message.answer("Код має бути числом. Введіть ще раз.")
        return
    state["poll"]["code"] = message.text.strip()
    state["step"] = "title"
    await message.answer("Введіть текстову назву опитування (для себе):")


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "title")
async def create_poll_set_title(message: types.Message):
    state = dp.data[message.from_user.id]
    state["poll"]["title"] = message.text.strip()
    state["step"] = "reward"
    await message.answer("Вкажіть суму винагороди за це опитування (грн):")


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "reward")
async def create_poll_set_reward(message: types.Message):
    state = dp.data[message.from_user.id]
    try:
        reward = float(message.text.replace(",", "."))
        if reward < 0:
            raise ValueError
        state["poll"]["reward"] = reward
        state["step"] = "count"
        await message.answer("Скільки питань буде в опитуванні? Введіть число.")
    except ValueError:
        await message.answer("Введіть коректну суму (наприклад: 10 або 15.5).")


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "count")
async def create_poll_set_count(message: types.Message):
    state = dp.data[message.from_user.id]
    try:
        n = int(message.text)
        if n <= 0:
            raise ValueError
        state["poll"]["n"] = n
        state["poll"]["qidx"] = 1
        state["step"] = "q_text"
        await message.answer("Введіть текст питання №1:")
    except ValueError:
        await message.answer("Введіть, будь ласка, додатне число.")


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "q_text")
async def create_poll_q_text(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    poll["qbuf"] = {"index": poll["qidx"], "text": message.text.strip()}
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Один вибір")],
            [KeyboardButton(text="Мультивибір")],
            [KeyboardButton(text="Текст")],
            [KeyboardButton(text="Шкала")],
        ],
        resize_keyboard=True,
    )
    state["step"] = "q_kind"
    await message.answer("Оберіть тип питання:", reply_markup=kb)


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "q_kind")
async def create_poll_q_kind(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    kind_text = message.text.lower()

    if "один" in kind_text:
        poll["qbuf"]["kind"] = "radio"
    elif "мульти" in kind_text:
        poll["qbuf"]["kind"] = "multi"
    elif "текст" in kind_text:
        poll["qbuf"]["kind"] = "text"
    elif "шкала" in kind_text:
        poll["qbuf"]["kind"] = "scale"
    else:
        await message.answer("Будь ласка, оберіть один із варіантів типу.")
        return

    kind = poll["qbuf"]["kind"]

    if kind in ["radio", "multi"]:
        await message.answer(
            "Введіть варіанти відповіді через кому. Наприклад: Варіант 1, Варіант 2, Варіант 3"
        )
        state["step"] = "q_options"
    elif kind == "text":
        poll["qbuf"]["options"] = []
        poll["qbuf"]["scale_min"] = None
        poll["qbuf"]["scale_max"] = None
        poll["qbuf"]["exclusive_option"] = None
        poll["qbuf"]["on_exclusive"] = None
        await finalize_question_and_maybe_next(message)
    elif kind == "scale":
        state["step"] = "q_scale_range"
        await message.answer(
            "Введіть мінімальне та максимальне значення шкали через дефіс. Наприклад: 1-5 або 0-10"
        )


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "q_options")
async def create_poll_q_options(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    opts_raw = [o.strip() for o in message.text.split(",") if o.strip()]
    if not opts_raw:
        await message.answer("Введіть хоча б один варіант.")
        return
    poll["qbuf"]["options"] = opts_raw

    if poll["qbuf"]["kind"] == "multi":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Так, є виключна опція")],
                [KeyboardButton(text="Ні, немає виключної опції")],
            ],
            resize_keyboard=True,
        )
        state["step"] = "q_multi_exclusive_yesno"
        await message.answer(
            "Чи є серед варіантів виключна опція (типу 'Жоден з наведених')?", reply_markup=kb
        )
    else:
        poll["qbuf"]["scale_min"] = None
        poll["qbuf"]["scale_max"] = None
        poll["qbuf"]["exclusive_option"] = None
        poll["qbuf"]["on_exclusive"] = None
        await finalize_question_and_maybe_next(message)


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "q_multi_exclusive_yesno")
async def create_poll_q_multi_exclusive_yesno(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    text = message.text.lower()

    if "так" in text:
        state["step"] = "q_multi_exclusive_text"
        await message.answer(
            "Введіть точно той текст варіанту, який є виключним (наприклад: Жоден з наведених).",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        poll["qbuf"]["exclusive_option"] = None
        poll["qbuf"]["on_exclusive"] = None
        poll["qbuf"]["scale_min"] = None
        poll["qbuf"]["scale_max"] = None
        await finalize_question_and_maybe_next(message)


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "q_multi_exclusive_text")
async def create_poll_q_multi_exclusive_text(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    excl_text = message.text.strip()

    if excl_text not in poll["qbuf"]["options"]:
        await message.answer(
            "Цієї опції немає в списку варіантів. Введіть текст ще раз точно так, як у варіантах."
        )
        return

    poll["qbuf"]["exclusive_option"] = excl_text

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Далі (наступне питання)")],
            [KeyboardButton(text="Завершити опитування")],
            [KeyboardButton(text="Перейти до питання №...")],
        ],
        resize_keyboard=True,
    )
    state["step"] = "q_multi_on_exclusive"
    await message.answer(
        "Що робити, якщо користувач обирає цю виключну опцію?", reply_markup=kb
    )


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "q_multi_on_exclusive")
async def create_poll_q_multi_on_exclusive(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    text = message.text.lower()

    if "завершити" in text:
        poll["qbuf"]["on_exclusive"] = "finish"
        poll["qbuf"]["scale_min"] = None
        poll["qbuf"]["scale_max"] = None
        await finalize_question_and_maybe_next(message)
    elif "наступ" in text:
        poll["qbuf"]["on_exclusive"] = "next"
        poll["qbuf"]["scale_min"] = None
        poll["qbuf"]["scale_max"] = None
        await finalize_question_and_maybe_next(message)
    elif "перейти" in text:
        state["step"] = "q_multi_on_exclusive_goto"
        await message.answer(
            "Введіть номер питання (1..N), до якого треба перейти при виборі виключної опції.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer(
            "Будь ласка, оберіть: наступне, завершити, або перейти до питання №..."
        )


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "q_multi_on_exclusive_goto")
async def create_poll_q_multi_on_exclusive_goto(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    try:
        goto_idx = int(message.text)
        if goto_idx <= 0:
            raise ValueError
        poll["qbuf"]["on_exclusive"] = f"goto:{goto_idx}"
        poll["qbuf"]["scale_min"] = None
        poll["qbuf"]["scale_max"] = None
        await finalize_question_and_maybe_next(message)
    except ValueError:
        await message.answer("Введіть коректний номер питання (додатне число).")


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("step") == "q_scale_range")
async def create_poll_q_scale_range(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    text = message.text.replace(" ", "")
    if "-" not in text:
        await message.answer("Введіть діапазон у форматі мін-макс, наприклад: 1-5")
        return
    left, right = text.split("-", 1)
    try:
        s_min = int(left)
        s_max = int(right)
        if s_min >= s_max:
            raise ValueError
    except ValueError:
        await message.answer("Діапазон некоректний. Приклад: 1-5 або 0-10.")
        return

    poll["qbuf"]["scale_min"] = s_min
    poll["qbuf"]["scale_max"] = s_max
    poll["qbuf"]["options"] = []
    poll["qbuf"]["exclusive_option"] = None
    poll["qbuf"]["on_exclusive"] = None
    await finalize_question_and_maybe_next(message)


async def finalize_question_and_maybe_next(message: types.Message):
    state = dp.data[message.from_user.id]
    poll = state["poll"]
    q = {
        "index": poll["qbuf"]["index"],
        "kind": poll["qbuf"]["kind"],
        "text": poll["qbuf"]["text"],
        "options": poll["qbuf"].get("options", []),
        "scale_min": poll["qbuf"].get("scale_min"),
        "scale_max": poll["qbuf"].get("scale_max"),
        "exclusive_option": poll["qbuf"].get("exclusive_option"),
        "on_exclusive": poll["qbuf"].get("on_exclusive"),
    }
    poll["questions"].append(q)
    poll["qidx"] += 1

    if poll["qidx"] <= poll["n"]:
        state["step"] = "q_text"
        await message.answer(f"Введіть текст питання №{poll['qidx']}:")
    else:
        questions_json = json.dumps(poll["questions"], ensure_ascii=False)
        existing = polls_table.get_all_values()
        try:
            ids = [int(r[0]) for r in existing[1:] if r and r[0].isdigit()]
            next_id = max(ids) + 1 if ids else 1
        except Exception:
            next_id = 1

        code = poll["code"]
        title = poll["title"]
        reward = poll.get("reward", 0)

        polls_table.append_row([next_id, code, title, reward, questions_json])
        await message.answer(
            f"Опитування '{title}' (код {code}) створено.\n"
            f"Винагорода: {reward} грн.\n"
            f"Питань: {len(poll['questions'])}.",
            reply_markup=admin_menu(),
        )
        del dp.data[message.from_user.id]


# ---------- РОЗСИЛКА ЗАПРОШЕННЯ (INLINE КНОПКИ) ----------

@dp.message(lambda m: m.from_user.id in ADMIN_IDS and m.text == "Розіслати опитування")
async def admin_broadcast_start(message: types.Message):
    dp.data[message.from_user.id] = {"stage": "broadcast_code"}
    await message.answer(
        "Введіть код опитування, яке треба розіслати (наприклад, 126):",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(lambda m: m.from_user.id in ADMIN_IDS and dp.data.get(m.from_user.id, {}).get("stage") == "broadcast_code")
async def admin_broadcast_send(message: types.Message):
    code = message.text.strip()
    if not code.isdigit():
        await message.answer("Код має бути числом. Введіть ще раз.")
        return

    rows = polls_table.get_all_values()
    poll_row = None
    for r in rows[1:]:
        if len(r) >= 2 and r[1] == code:
            poll_row = r
            break

    if not poll_row:
        await message.answer("Опитування з таким кодом не знайдено.", reply_markup=admin_menu())
        dp.data.pop(message.from_user.id, None)
        return

    title = poll_row[2] if len(poll_row) >= 3 else ""
    reward = poll_row[3] if len(poll_row) >= 4 else "0"

    users = users_table.col_values(1)[1:]
    sent = 0
    for uid in users:
        try:
            uid_int = int(uid)
        except ValueError:
            continue
        try:
            text = (
                "Вас запрошено до опитування:\n"
                f"Код: {code}\n"
                f"Назва: {title}\n"
                f"Винагорода: {reward} грн.\n\n"
                "Натисніть кнопку нижче, щоб почати або відмовитися."
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Почати опитування",
                            callback_data=f"start_poll:{code}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Відмовитися",
                            callback_data=f"decline_poll:{code}",
                        )
                    ],
                ]
            )
            await bot.send_message(chat_id=uid_int, text=text, reply_markup=kb)
            sent += 1
        except Exception as e:
            logger.warning("Failed to send invite to %s: %s", uid, e)

    dp.data.pop(message.from_user.id, None)
    await message.answer(
        f"Розсилка завершена. Повідомлень надіслано: {sent}.",
        reply_markup=admin_menu(),
    )


# ---------- ПРОХОДЖЕННЯ ПО INLINE-КНОПЦІ + ОДИН РАЗ ----------

def get_poll_by_code(code: str):
    rows = polls_table.get_all_values()
    for row in rows[1:]:
        if len(row) >= 5 and row[1] == code:
            poll_id = int(row[0])
            title = row[2]
            reward = float(row[3]) if row[3] else 0.0
            questions = json.loads(row[4])
            return poll_id, title, reward, questions
    return None, "", 0.0, []


@dp.callback_query(F.data.startswith("decline_poll:"))
async def cb_decline_poll(callback: CallbackQuery):
    await callback.answer("Добре, це опитування можна пройти пізніше.")
    await callback.message.edit_reply_markup(reply_markup=None)


@dp.callback_query(F.data.startswith("start_poll:"))
async def cb_start_poll(callback: CallbackQuery):
    user_id = callback.from_user.id
    code = callback.data.split(":", 1)[1]

    poll_id, title, reward, questions = get_poll_by_code(code)
    if not questions:
        await callback.answer("Опитування не знайдено.", show_alert=True)
        return

    file_name = f"Answers_survey_{code}"
    try:
        ans_sheet = gs.open(file_name).sheet1
    except gspread.SpreadsheetNotFound:
        await callback.answer(
            "Технічна помилка: немає таблиці для цього опитування.", show_alert=True
        )
        return

    data = ans_sheet.get_all_values()
    for r in data[1:]:
        if r and str(r[0]) == str(user_id):
            await callback.answer(
                "Ви вже проходили це опитування.", show_alert=True
            )
            return

    dp.data[user_id] = {
        "stage": "in_poll",
        "poll_id": poll_id,
        "poll_code": code,
        "poll_title": title,
        "reward": reward,
        "questions": questions,
        "current_index": 1,
        "answers": {},
    }

    await callback.answer()
    await callback.message.answer(
        f"Починаємо опитування: {title} (код {code}).", reply_markup=user_menu()
    )
    await ask_next_question(callback.message)


@dp.message(lambda m: dp.data.get(m.from_user.id, {}).get("stage") == "in_poll")
async def user_poll_answer(message: types.Message):
    state = dp.data.get(message.from_user.id)
    if not state:
        await message.answer("Сесія опитування втрачена. Почніть заново.", reply_markup=user_menu())
        return

    idx = state["current_index"]
    questions = state["questions"]
    q = next((q for q in questions if q.get("index") == idx), None)
    if not q:
        await finish_poll(message)
        return

    kind = q["kind"]
    text = message.text

    if kind == "scale":
        try:
            val = int(text)
            s_min = q.get("scale_min", 1)
            s_max = q.get("scale_max", 5)
            if not (s_min <= val <= s_max):
                raise ValueError
        except ValueError:
            await message.answer("Введіть число в межах шкали.")
            return

    if kind in ["radio", "multi"]:
        options = q.get("options") or []
        if text not in options:
            await message.answer("Оберіть одну з кнопок.")
            return

    state["answers"][idx] = text

    if kind == "multi" and q.get("exclusive_option") and text == q["exclusive_option"]:
        action = q.get("on_exclusive") or "next"
        if action == "finish":
            await finish_poll(message)
            return
        if action.startswith("goto:"):
            try:
                goto_idx = int(action.split(":", 1)[1])
                state["current_index"] = goto_idx
                await ask_next_question(message)
                return
            except ValueError:
                pass

    state["current_index"] += 1
    await ask_next_question(message)


async def ask_next_question(message: types.Message):
    state = dp.data.get(message.from_user.id)
    if not state:
        await message.answer("Сесія опитування втрачена. Почніть заново.", reply_markup=user_menu())
        return

    questions = state["questions"]
    idx = state["current_index"]
    q = next((q for q in questions if q.get("index") == idx), None)
    if not q:
        await finish_poll(message)
        return

    kind = q["kind"]
    text = q["text"]
    options = q.get("options") or []

    if kind in ["radio", "multi"]:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=o)] for o in options],
            resize_keyboard=True,
        )
        await message.answer(text, reply_markup=kb)
    elif kind == "text":
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
    elif kind == "scale":
        s_min = q.get("scale_min", 1)
        s_max = q.get("scale_max", 5)
        row = [KeyboardButton(text=str(i)) for i in range(s_min, s_max + 1)]
        kb = ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)
        await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=ReplyKeyboardRemove())


async def finish_poll(message: types.Message):
    state = dp.data.get(message.from_user.id)
    if not state:
        await message.answer("Опитування завершено.", reply_markup=user_menu())
        return

    user_id = message.from_user.id
    code = state["poll_code"]
    title = state["poll_title"]
    questions = state["questions"]
    answers = state["answers"]
    reward = state.get("reward", 0.0)

    file_name = f"Answers_survey_{code}"
    try:
        ans_sheet = gs.open(file_name).sheet1
    except gspread.SpreadsheetNotFound:
        await message.answer(
            "Технічна помилка: не знайдено таблицю для цього опитування.\n"
            f"Створи в Google Drive таблицю '{file_name}' і дай боту права редактора.",
            reply_markup=user_menu(),
        )
        dp.data.pop(message.from_user.id, None)
        return

    data = ans_sheet.get_all_values()
    for r in data[1:]:
        if r and str(r[0]) == str(user_id):
            await message.answer(
                "Ви вже проходили це опитування. Відповіді вдруге не збережені.",
                reply_markup=user_menu(),
            )
            dp.data.pop(message.from_user.id, None)
            return

    row = [user_id]
    for q in questions:
        val = answers.get(q["index"], "")
        row.append(val)
    row.append(reward)
    ans_sheet.append_row(row)

    total_reward = await calculate_user_balance(user_id)

    await message.answer(
        f"Дякуємо! Ваші відповіді збережені.\n"
        f"Опитування: {title} (код {code}).\n"
        f"Винагорода за це опитування: {reward} грн.\n"
        f"Ваш загальний баланс: {total_reward} грн.",
        reply_markup=user_menu(),
    )
    dp.data.pop(message.from_user.id, None)


async def calculate_user_balance(user_id: int) -> float:
    total = 0.0
    files = [f for f in gs.list_spreadsheet_files() if f["name"].startswith("Answers_survey_")]
    for f in files:
        sh = gs.open(f["name"]).sheet1
        data = sh.get_all_values()
        if not data or len(data[0]) < 2:
            continue
        # припускаємо, що останній стовпчик завжди reward
        reward_col = len(data[0]) - 1
        for r in data[1:]:
            if not r:
                continue
            if str(r[0]) == str(user_id):
                try:
                    total += float(r[reward_col]) if len(r) > reward_col and r[reward_col] else 0.0
                except ValueError:
                    continue
    return total


@dp.message(lambda m: m.text == "Переглянути баланс")
async def user_balance(message: types.Message):
    total = await calculate_user_balance(message.from_user.id)
    await message.answer(f"Ваш поточний баланс: {total} грн.", reply_markup=user_menu())


@dp.message()
async def fallback(message: types.Message):
    logger.info("Fallback from %s: %s", message.from_user.id, message.text)
    await message.answer("Команда не розпізнана. Використовуйте меню або /start.")


async def main():
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
