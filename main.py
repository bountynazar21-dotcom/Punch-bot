# main.py
import os
import asyncio
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError

# === локальні модулі ===
from db import init_db
from commands import setup_bot_commands
from handlers.start import router as start_router
from handlers.raffle import router as raffle_router
from handlers.admin import router as admin_router


# ======================================
#  ЛОГІНГ
# ======================================
def setup_logging() -> None:
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)


# ======================================
#  ІНІЦІАЛІЗАЦІЯ БОТА
# ======================================
async def _create_bot() -> Bot:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN відсутній. Додай його в .env (локально) або Railway Variables (прод).")

    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )


# ======================================
#  ГОЛОВНА АСИНХРОННА ФУНКЦІЯ
# ======================================
async def main() -> None:
    setup_logging()
    log = logging.getLogger("main")

    # 1️⃣ Ініціалізуємо базу
    init_db()
    log.info("SQLite ініціалізовано")

    # 2️⃣ Ініціалізуємо бота + диспетчер
    bot = await _create_bot()
    dp = Dispatcher()

    # 3️⃣ Підключаємо всі роутери
    dp.include_router(start_router)
    dp.include_router(raffle_router)
    dp.include_router(admin_router)

    try:
        # ✅ Перевірка: який бот реально запущений
        me = await bot.get_me()
        log.info(f"RUNNING BOT = @{me.username} (id={me.id})")

        # 4️⃣ Меню команд (окремо для юзерів і адмінів)
        await setup_bot_commands(bot)

        # 5️⃣ Лог
        log.info("Polling on 🔥")

        # 6️⃣ Запуск
        await dp.start_polling(bot)

    except TelegramUnauthorizedError:
        log.error("❌ Unauthorized: BOT_TOKEN неправильний/старий. Онови токен в BotFather і встав в Railway Variables.")
        raise

    finally:
        # ✅ щоб не було Unclosed client session
        await bot.session.close()


# ======================================
#  ЗАПУСК СКРИПТА
# ======================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Бот зупинено вручну.")
