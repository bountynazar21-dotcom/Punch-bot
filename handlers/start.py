# handlers/start.py
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from db import get_rules

router = Router()

WELCOME = (
    "🎉 <b>Акція Soska Bar</b>\n\n"
    "У всіх магазинах <b>Soska Bar</b> діє спеціальна промоакція.\n"
    "На вас чекають <b>розіграші, подарунки та приємні бонуси</b> ✨\n\n"
    "Купуйте акційні товари, реєструйте покупки та отримуйте "
    "<b>шанс виграти круті призи</b>.\n\n"
    "⬇️ Усі деталі акції, правила участі та призи — нижче"
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
