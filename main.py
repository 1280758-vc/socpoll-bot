import logging
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = "8330526731:AAHDXrNmgrYJ3hHpNj1jIdGc7pYZzrHBGjk"
ADMIN_IDS = [383222956, 233536337]

# ---------- МІНІМАЛЬНИЙ БОТ БЕЗ GOOGLE SHEETS ДЛЯ ТЕСТУ ----------

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити опитування")],
            [KeyboardButton(text="Оглянути/Редагувати анкету")],
            [KeyboardButton(text="Розіслати опитування")],
            [KeyboardButton(text="Експорт відповідей")],
            [KeyboardButton(text="Статистика")]
        ],
        resize_keyboard=True
    )

def user_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Почати опитування")],
            [KeyboardButton(text="Переглянути баланс")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start(message: types.Message):
    logger.info("Received /start from %s", message.from_user.id)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поділитися номером", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer("👋 Тестовий бот працює. Поділіться номером:", reply_markup=kb)

@dp.message(lambda msg: msg.contact is not None)
async def contact(message: types.Message):
    logger.info("Got contact from %s: %s", message.from_user.id, message.contact.phone_number)
    await message.answer("Контакт отримано, бот живий ✅", reply_markup=user_menu())

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Недостатньо прав.")
        return
    await message.answer("Адмін-меню (тест):", reply_markup=admin_menu())

@dp.message()
async def echo(message: types.Message):
    logger.info("Echo message from %s: %s", message.from_user.id, message.text)
    await message.answer("Тестовий echo: " + message.text)

async def main():
    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception("Bot crashed with exception: %s", e)

if __name__ == "__main__":
    logger.info("main.py __name__ == '__main__', starting asyncio.run")
    asyncio.run(main())
