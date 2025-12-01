# handlers/admin.py
import io
import os
import asyncio
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.text_decorations import html_decoration as hd

from db import (
    get_participants, clear_tables, table_counts, DB_PATH,
    count_participants, count_participants_today,
    get_all_user_ids, pick_random_winner, save_winner, get_winners,
    set_rules, get_rules
)
# ⬇️ додано gs_diagnostics
from gs import clear_gsheet_keep_header, SHEET_NAME, sheet_row_count, gs_diagnostics

load_dotenv()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
VERSION = os.getenv("BOT_VERSION", "1.0.0")

router = Router()

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def spoiler(x: str) -> str:
    x = x or ""
    return f"<tg-spoiler>{hd.quote(x)}</tg-spoiler>"

# ==============================
#        /help_admin
# ==============================
@router.message(Command("help_admin"))
async def help_admin_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    commands = [
        ("📊 /stats", "Показує статистику по учасниках і базі."),
        ("📤 /export", "Експортує учасників у Excel."),
        ("🧷 /backup", "Завантажує файл бази даних."),
        ("🧹 /clear", "Очищає всі таблиці (та Google Sheet)."),
        ("📋 /set_rules", "Задати правила розіграшу."),
        ("📖 /get_rules", "Показати поточні правила."),
        ("🏆 /random_winner", "Випадковий переможець."),
        ("🎖 /winners", "Показує останніх переможців."),
        ("📢 /broadcast", "Надіслати повідомлення всім учасникам."),
        ("🧪 /gs_diag", "Діагностика доступу до Google Sheets."),
        ("🧽 /gs_clear", "Очистити аркуш у Google Sheets, лишити шапку."),
        ("💡 /version", "Показує версію бота."),
        ("🏓 /ping", "Перевірка працездатності."),
    ]
    text = "<b>⚙️ Команди для адмінів:</b>\n\n" + "\n".join(
        [f"{cmd} — {desc}" for cmd, desc in commands]
    )
    await m.answer(text)

# ==============================
#        /ping
# ==============================
@router.message(Command("ping"))
async def ping_cmd(m: Message):
    await m.answer("pong 🏓")

# ==============================
#        /version
# ==============================
@router.message(Command("version"))
async def version_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    await m.answer(f"🤖 Bot version: <b>{VERSION}</b>")

# ==============================
#        /stats
# ==============================
@router.message(Command("stats"))
async def stats_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    total = count_participants()
    today = count_participants_today()
    try:
        gs_rows = sheet_row_count()
    except Exception:
        gs_rows = "—"
    p, r, w = table_counts()
    txt = (
        "📊 <b>Статистика</b>\n"
        f"Учасників всього: <b>{total}</b> (сьогодні: {today})\n"
        f"Google Sheet «{SHEET_NAME}»: {gs_rows} рядків\n"
        f"Таблиці: participants={p}, rules={r}, winners={w}\n"
        f"📄 БД: <code>{DB_PATH}</code>"
    )
    await m.answer(txt)

# ==============================
#        /export
# ==============================
@router.message(Command("export"))
async def export_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    rows = get_participants()  # (id, username, full_name, phone, photo_id, created_at)
    cleaned_rows = [row[:4] + row[5:] for row in rows]  # без photo_id
    df = pd.DataFrame(cleaned_rows, columns=["№", "Telegram", "Ім’я", "Телефон", "Дата"])
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    fname = f"participants_{datetime.now():%Y%m%d_%H%M}.xlsx"
    file = BufferedInputFile(buf.getvalue(), filename=fname)
    await m.answer_document(file, caption="📤 Експорт готовий ✅")

# ==============================
#        /backup
# ==============================
@router.message(Command("backup"))
async def backup_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    if not os.path.exists(DB_PATH):
        return await m.answer("⚠️ Файл бази не знайдено.")
    with open(DB_PATH, "rb") as f:
        data = f.read()
    file = BufferedInputFile(data, filename=f"bot_backup_{datetime.now():%Y%m%d_%H%M}.db")
    await m.answer_document(file, caption="🧷 Бекап бази")

# ==============================
#        /clear
# ==============================
@router.message(Command("clear"))
async def clear_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    stats = clear_tables()
    p_left, r_left, w_left = table_counts()

    # коректні заголовки під наш gs.py (5 колонок)
    headers = ("№", "Telegram user", "Ім’я", "Номер телефону", "Дата")
    ok, gs_info = clear_gsheet_keep_header(headers=headers)
    gs_line = (
        f"Google Sheet: before={gs_info['before']}, after={gs_info['after']}"
        if ok else f"❌ Google Sheet: {gs_info}"
    )
    txt = (
        "🧹 <b>Очищено</b>\n"
        f"До: participants={stats['before_participants']}, rules={stats['before_rules']}, winners={stats['before_winners']}\n"
        f"Видалено: participants={stats['deleted_participants']}, rules={stats['deleted_rules']}, winners={stats['deleted_winners']}\n"
        f"Після: participants={p_left}, rules={r_left}, winners={w_left}\n"
        f"{gs_line}\n"
        f"📄 БД: <code>{DB_PATH}</code>"
    )
    await m.answer(txt)

# ==============================
#        /set_rules + /get_rules
# ==============================
@router.message(Command("set_rules"))
async def set_rules_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    text = m.text.partition(" ")[2].strip()
    if not text:
        return await m.answer("Використай: /set_rules умови (наприклад: сума ≥ 300 грн; дата ≤ 7 днів)")
    set_rules(text)
    await m.answer("✅ Правила оновлено.")

@router.message(Command("get_rules"))
async def get_rules_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    rules = get_rules()
    if not rules:
        return await m.answer("ℹ️ Правила ще не задані.")
    await m.answer(f"📋 Поточні правила:\n{hd.quote(rules)}")

# ==============================
#        /random_winner
# ==============================
@router.message(Command("random_winner"))
async def random_winner_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    cand = pick_random_winner()
    if not cand:
        return await m.answer("😕 Немає кандидатів (усі вже виграли).")
    save_winner(cand["participant_id"])
    await m.answer(
        "🎉 <b>Випадковий переможець</b>\n"
        f"№: {cand['participant_id']}\n"
        f"👤 Ім’я: {hd.quote(cand['full_name'] or '—')}\n"
        f"🧑‍💻 Username: {spoiler('@' + cand['username']) if cand['username'] else '—'}\n"
        f"📞 Телефон: {spoiler(cand['phone'] or '—')}\n"
        f"🕒 {cand['created_at']}"
    )

# ==============================
#        /winners
# ==============================
@router.message(Command("winners"))
async def winners_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    rows = get_winners(limit=20)
    if not rows:
        return await m.answer("Переможців поки нема.")
    lines = ["🏆 <b>Останні переможці</b>"]
    for created_at, pid, username, full_name, phone in rows:
        uname = f"@{username}" if username else "—"
        lines.append(
            f"• #{pid} — {hd.quote(full_name or '—')} | {spoiler(uname)} | {spoiler(phone)} | {created_at}"
        )
    await m.answer("\n".join(lines))

# ==============================
#        /broadcast
# ==============================
@router.message(Command("broadcast"))
async def broadcast_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    text = m.text.partition(" ")[2].strip()
    if not text:
        return await m.answer("Використай: /broadcast ваш текст для всіх.")
    users = get_all_user_ids()
    if not users:
        return await m.answer("Немає користувачів.")
    sent = 0
    fail = 0
    await m.answer(f"🚀 Розсилка на {len(users)} користувачів…")
    for tg_id, pid in users:
        try:
            await m.bot.send_message(tg_id, text)
            sent += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await m.answer(f"✅ Готово. Надіслано: {sent}, помилок: {fail}.")

# ==============================
#        Google Sheets tools
# ==============================
@router.message(Command("gs_diag"))
async def gs_diag_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    d = gs_diagnostics()
    lines = [
        "🧪 <b>GS діагностика</b>",
        f"credentials.json існує: {d.get('creds_file_exists')}",
        f"SHEET_ID: {d.get('sheet_id')}",
        f"SHEET_NAME: {d.get('sheet_name')}",
        f"WORKSHEET: {d.get('worksheet_title')}",
        f"Відкривається книга: {d.get('can_open')}",
        f"Аркуш ок: {d.get('worksheet_ok')}",
        f"Рядків (з хедером): {d.get('row_count_including_header')}",
        f"Помилка: {hd.quote(d.get('error') or '—')}",
    ]
    await m.answer("\n".join(lines))

@router.message(Command("gs_clear"))
async def gs_clear_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("🚫 Тільки для адмінів.")
    headers = ("№", "Telegram user", "Ім’я", "Номер телефону", "Дата")
    ok, info = clear_gsheet_keep_header(headers=headers)
    if ok:
        await m.answer(f"🧽 GS очищено: було {info['before']}, стало {info['after']}.")
    else:
        await m.answer(f"⚠️ GS помилка: {info}")
