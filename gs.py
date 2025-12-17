# gs.py
import os
from datetime import datetime
from typing import Tuple

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
CREDS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Rozigrash").strip()
WORKSHEET_TITLE = os.getenv("GOOGLE_WORKSHEET_TITLE", "Лист1").strip()

# ✅ додали "Магазин №"
HEADER: Tuple[str, ...] = ("№", "Telegram user", "Ім’я", "Номер телефону", "Магазин №", "Дата")


def _client() -> gspread.Client:
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def _open_spreadsheet(gc: gspread.Client):
    """Пробуємо спочатку відкрити по ID, якщо нема — по name."""
    if SHEET_ID:
        return gc.open_by_key(SHEET_ID)
    return gc.open(SHEET_NAME)


def _open_ws(sh):
    try:
        return sh.worksheet(WORKSHEET_TITLE)
    except gspread.WorksheetNotFound:
        # cols=10 щоб точно вистачило під майбутні колонки
        return sh.add_worksheet(title=WORKSHEET_TITLE, rows=1000, cols=10)


def _a1_range_for_header(headers: Tuple[str, ...]) -> str:
    # A1 + (len(headers) колонок)
    # 1->A, 2->B, ..., 26->Z, 27->AA ...
    n = len(headers)
    def col_letter(num: int) -> str:
        s = ""
        while num:
            num, r = divmod(num - 1, 26)
            s = chr(65 + r) + s
        return s
    last = col_letter(n)
    return f"A1:{last}1"


def _ensure_header(ws, headers: Tuple[str, ...] = HEADER) -> None:
    rng = _a1_range_for_header(headers)
    vals = ws.get_values(rng)

    need = list(headers)
    if not vals or not vals[0]:
        ws.update(rng, [need])
        return

    row = vals[0]
    # якщо не співпало по довжині або по значеннях — перезаписуємо хедер
    if len(row) < len(need) or any((row[i] if i < len(row) else "") != need[i] for i in range(len(need))):
        ws.update(rng, [need])


def _next_seq(ws) -> int:
    col = ws.col_values(1)[1:]  # без заголовка
    seq = 0
    for v in col:
        try:
            seq = max(seq, int(v))
        except Exception:
            pass
    return seq + 1


def append_participant_row(
    username: str,
    full_name: str,
    phone: str,
    store_no: int | None = None,
    row_id: int | None = None
) -> int:
    """
    ✅ Тепер пишемо і store_no.
    row_id лишив як опційний, щоб не ламати старі виклики.
    """
    gc = _client()
    sh = _open_spreadsheet(gc)
    ws = _open_ws(sh)
    _ensure_header(ws)

    seq = _next_seq(ws)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ws.append_row(
        [seq, username or "", full_name or "", phone or "", (store_no if store_no is not None else ""), now],
        value_input_option="USER_ENTERED"
    )
    return seq


def sheet_row_count() -> int:
    gc = _client()
    sh = _open_spreadsheet(gc)
    ws = _open_ws(sh)
    return len([x for x in ws.col_values(1) if str(x).strip()])


def clear_gsheet_keep_header(headers: Tuple[str, ...] = HEADER) -> tuple[bool, dict | str]:
    try:
        gc = _client()
        sh = _open_spreadsheet(gc)
        ws = _open_ws(sh)

        before = max(len(ws.col_values(1)) - 1, 0)
        ws.clear()

        rng = _a1_range_for_header(headers)
        ws.update(rng, [list(headers)])

        after = max(len(ws.col_values(1)) - 1, 0)
        return True, {"before": before, "after": after}
    except Exception as e:
        return False, str(e)


def gs_diagnostics() -> dict:
    """Повертає детальний стан для логів/команди /gs_diag."""
    info = {
        "creds_file_exists": os.path.exists(CREDS_FILE),
        "sheet_id": SHEET_ID or None,
        "sheet_name": SHEET_NAME or None,
        "worksheet_title": WORKSHEET_TITLE or None,
        "can_open": False,
        "worksheet_ok": False,
        "row_count_including_header": None,
        "error": None,
    }
    try:
        gc = _client()
        sh = _open_spreadsheet(gc)
        info["can_open"] = True
        ws = _open_ws(sh)
        info["worksheet_ok"] = True
        info["row_count_including_header"] = len(ws.col_values(1))
    except Exception as e:
        info["error"] = str(e)
    return info

