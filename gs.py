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

HEADER: Tuple[str, ...] = ("№", "Telegram user", "Ім’я", "Номер телефону", "Дата")

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
        return sh.add_worksheet(title=WORKSHEET_TITLE, rows=1000, cols=10)

def _ensure_header(ws) -> None:
    vals = ws.get_values("A1:E1")
    if not vals or len(vals[0]) < len(HEADER) or any(vals[0][i] != HEADER[i] for i in range(len(HEADER))):
        ws.update("A1:E1", [list(HEADER)])

def _next_seq(ws) -> int:
    col = ws.col_values(1)[1:]  # без заголовка
    seq = 0
    for v in col:
        try:
            seq = max(seq, int(v))
        except Exception:
            pass
    return seq + 1

def append_participant_row(username: str, full_name: str, phone: str, row_id: int | None = None) -> int:
    gc = _client()
    sh = _open_spreadsheet(gc)
    ws = _open_ws(sh)
    _ensure_header(ws)
    seq = _next_seq(ws)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([seq, username or "", full_name or "", phone or "", now], value_input_option="USER_ENTERED")
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
        ws.update("A1:E1", [list(headers)])
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
