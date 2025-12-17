# handlers/start.py
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from db import get_rules

router = Router()

WELCOME = (
    "🎄 <b>Новорічна акція Soska Bar × InBottle</b> 🎄\n\n"
    "З <b>18.12</b> по <b>31.12</b> у всіх магазинах Soska Bar діє святкова акція спільно з InBottle.\n"
    "На вас чекають <b>3 рівні призів</b> — гарантовані подарунки, розіграші та виконання бажань ✨\n\n"
    "⬇️ Усі детальні умови та подарунки — нижче"
)


def _rules_block() -> str:
    rules = get_rules()
    if not rules:
        return "ℹ️ Правила ще не встановлені адміністратором."
    return f"📋 <b>Актуальні правила:</b>\n{rules}"

@router.message(CommandStart())
async def start_cmd(m: Message):
    await m.answer(WELCOME)

    await m.answer(_rules_block())

    await m.answer("Готовий брати участь? Надсилай фото чека 📸")

@router.message(Command("rules"))
@router.message(Command("get_rules"))
async def show_rules_cmd(m: Message):
    await m.answer(_rules_block())
