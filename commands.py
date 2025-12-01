# commands.py
import os
from dotenv import load_dotenv
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

load_dotenv()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# Команди для звичайних користувачів
USER_COMMANDS = [
    BotCommand(command="start", description="Почати участь у розіграші"),
    BotCommand(command="rules", description="Показати актуальні правила"),
    BotCommand(command="help",  description="Список команд"),
]

# Повний стек адмін-команд
ADMIN_COMMANDS = [
    BotCommand(command="ping",          description="Перевірка бота (pong)"),
    BotCommand(command="version",       description="Версія бота"),
    BotCommand(command="stats",         description="Статистика (БД + Google Sheet)"),
    BotCommand(command="export",        description="Експорт учасників у XLSX"),
    BotCommand(command="backup",        description="Бекап файлу БД"),
    BotCommand(command="clear",         description="Очистити БД та Google Sheet"),
    BotCommand(command="set_rules",     description="Встановити правила розіграшу"),
    BotCommand(command="get_rules",     description="Показати поточні правила"),
    BotCommand(command="random_winner", description="Рандомний переможець"),
    BotCommand(command="winners",       description="Список переможців"),
    BotCommand(command="broadcast",     description="Розсилка всім учасникам"),
    BotCommand(command="help",          description="Список адмін-команд"),
]

async def setup_bot_commands(bot):
    # дефолтні команди для всіх користувачів
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())

    # окремий набір тільки для чатів з адмінами (їм випадає повний список)
    for admin_id in ADMIN_IDS:
        await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id))
