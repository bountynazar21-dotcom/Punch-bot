# handlers/start.py
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from db import get_rules

router = Router()

WELCOME = (
    "🎄✨ МАСШТАБНИЙ НОВОРІЧНИЙ РОЗІГРАШ від <b>Punch</b> та <b>Soska Bar</b>! ✨🎄\n\n"
    "На тебе чекає купа святкових подарунків, включно з iPhone 17 Pro, PlayStation та Dyson 🎁\n"
    "А також ексклюзивні подарунки всередині нашої мережі 💜\n\n"
    "⬇️ Усі детальні правила, умови та подарунки ловиш нижче!"
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
