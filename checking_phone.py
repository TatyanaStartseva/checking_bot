import os
import asyncio
import re
from telethon import TelegramClient
from dotenv import load_dotenv
from telethon.sessions import StringSession
from aiogram.utils import executor
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext, filters
from aiogram.contrib.fsm_storage.memory import MemoryStorage

load_dotenv()
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("HASH_ID")
bot_token = os.getenv("BOT_TOKEN")

bot = Bot(token=bot_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply(
        "Нажмите на команду /checking_phone_number в меню и отправьте список номеров телефонов. Бот проверит, заблокированы ли пользователи в Telegram по этим номерам."
    )


class PhoneNumberState(StatesGroup):
    awaiting_phone_numbers = State()


@dp.message_handler(commands=["checking_phone_number"])
async def start_checking_phone_number(message: types.Message):
    await message.reply(
        "Отправьте список телефонных номеров, разделенных запятыми или пробелами:"
    )
    await PhoneNumberState.awaiting_phone_numbers.set()


@dp.message_handler(state=PhoneNumberState.awaiting_phone_numbers)
async def process_phone_numbers(message: types.Message, state: FSMContext):
    try:
        phone_numbers_text = message.text
        phones = re.split(r"[,\s\n]+", phone_numbers_text.strip())
        blocked_phones = []
        active_phones = []
        invalide_phones = []
        tasks = []
        for phone_number in phones:
            phone_number = re.sub(r"[^\+\d]", "", phone_number)
            tasks.append(
                check_phone(
                    phone_number, active_phones, blocked_phones, invalide_phones
                )
            )

        await asyncio.gather(*tasks)
        response = (
            "Активные номера:\n"
            + "\n".join(active_phones)
            + "\nЗаблокированные номера:\n"
            + "\n".join(blocked_phones)
        )
        if invalide_phones:
            response += "\nНеправильные номера:\n" + "\n".join(invalide_phones)
        await message.reply(response)
        await state.finish()
    except Exception as e:
        print(f"Ошибка при проверке номера: {e}")


async def check_phone(phone_number, active_phones, blocked_phones, invalide_phones):
    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        await client.sign_in(phone=phone_number)
        active_phones.append(phone_number)
    except Exception as e:
        if "The used phone number has been banned from Telegram" in str(e):
            blocked_phones.append(phone_number)
        elif "The phone number is invalid" in str(e):
            invalide_phones.append(phone_number)
        elif "A wait of " in str(e):
            blocked_phones.append(phone_number)
        else:
            print(f"Ошибка при проверке номера {phone_number}: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
