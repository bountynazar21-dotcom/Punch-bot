# handlers/raffle.py
import re
import os
from dotenv import load_dotenv

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import save_participant

# --- опційний імпорт Google Sheet (якщо є gs.py) ---
try:
    from gs import append_participant_row  # (username, full_name, phone, row_id)
    _GS_AVAILABLE = True
except Exception:
    _GS_AVAILABLE = False

load_dotenv()
router = Router()

# ADMIN_IDS з .env або вшити руками типу: ADMIN_IDS = [111, 222]
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# ===== FSM =====
class Reg(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{6,}$")

def _clean_phone(x: str) -> str:
    return re.sub(r"[^\d+]", "", (x or "")).lstrip("0")

def _spoil(text: str | None) -> str:
    t = (text or "").strip()
    return f"<tg-spoiler>{t}</tg-spoiler>" if t else "—"

# ===== FLOW =====

@router.message(F.photo)
async def handle_receipt_photo(message: Message, state: FSMContext):
    """
    Користувач кидає фото чеку -> просимо ім'я
    """
    photo_id = message.photo[-1].file_id if message.photo else None
    caption = message.caption or ""
    await state.update_data(photo_id=photo_id, caption=caption)
    await message.answer("📸 Бачу чек — напиши, будь ласка, своє ім’я ✍️")
    await state.set_state(Reg.waiting_for_name)


@router.message(Reg.waiting_for_name, F.text)
async def handle_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        return await message.answer("Напиши ім’я текстом, будь ласка ✍️")
    await state.update_data(full_name=name)

    # клавіша для контакту (якщо зробив keyboards/phone.py)
    try:
        from keyboards.phone import request_phone_kb
        kb = request_phone_kb
    except Exception:
        kb = None

    await message.answer(
        "📱 Тепер надішли номер телефону (текстом, напр. +380...) або натисни кнопку нижче ☎️",
        reply_markup=kb
    )
    await state.set_state(Reg.waiting_for_phone)


@router.message(Reg.waiting_for_phone, F.contact)
async def handle_phone_contact(message: Message, state: FSMContext):
    phone = _clean_phone(message.contact.phone_number)
    await _finalize_registration(message, state, phone)


@router.message(Reg.waiting_for_phone, F.text)
async def handle_phone_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not PHONE_RE.match(text):
        return await message.answer("Кинь, будь ласка, коректний номер (приклад: +380XXXXXXXXX) або натисни кнопку 📱")
    phone = _clean_phone(text)
    await _finalize_registration(message, state, phone)


async def _finalize_registration(message: Message, state: FSMContext, phone: str):
    """
    Завершуємо: пишемо в БД, (опційно) у Google Sheet, шлемо адмінам алерт.
    """
    data = await state.get_data()
    full_name = data.get("full_name") or "—"
    photo_id = data.get("photo_id")
    username = message.from_user.username or "—"

    # 1) зберегти в БД
    try:
        row_id = save_participant(
            username=username,
            full_name=full_name,
            phone=phone,
            photo_id=photo_id
        )
    except Exception as e:
        await message.answer(f"⚠️ Помилка збереження: {e}")
        return

    # 2) Google Sheet (опц., якщо підключено)
    if _GS_AVAILABLE:
        try:
            append_participant_row(f"@{username}" if username and username != "—" else "",
                                   full_name, phone, row_id)
        except Exception:
            pass  # не блокуємо флоу

    # 3) Відповідь учаснику
    await message.answer("✅ Дякуємо! Ти успішно зареєстрований у розіграші 💜", reply_markup=None)

    # 4) Нотиф адмінам (з фото, якщо є)
    if ADMIN_IDS:
        caption = (
            "🆕 <b>Нова реєстрація</b>\n"
            f"№: <b>{row_id}</b>\n"
            f"👤 Ім’я: {full_name}\n"
            f"🧑‍💻 Telegram: {_spoil('@' + username if username and username != '—' else '—')}\n"
            f"📞 Телефон: {_spoil(phone)}"
        )
        for admin_id in ADMIN_IDS:
            try:
                if photo_id:
                    await message.bot.send_photo(admin_id, photo_id, caption=caption, parse_mode="HTML")
                else:
                    await message.bot.send_message(admin_id, caption, parse_mode="HTML")
            except Exception:
                # не валимо флоу, якщо комусь із адмінів не відправилось
                pass

    # 5) кінець FSM
    await state.clear()
