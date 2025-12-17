# db.py
import os
import sqlite3
from datetime import date

DB_PATH = os.path.join("data", "bot.db")


def _connect():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols


def init_db():
    """Створює таблиці, якщо вони відсутні + м'які міграції"""
    with _connect() as conn:
        cur = conn.cursor()

        # participants
        cur.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_user_id INTEGER,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                photo_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ✅ міграція: додаємо store_no, якщо його ще нема
        if not _column_exists(cur, "participants", "store_no"):
            cur.execute("ALTER TABLE participants ADD COLUMN store_no INTEGER")

        # rules
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # winners
        cur.execute("""
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(participant_id) REFERENCES participants(id)
            )
        """)

        # ✅ довідник магазинів (по номеру)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stores (
                store_no INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        conn.commit()


# ==========================================
#   Додавання та отримання учасників
# ==========================================

def save_participant(username: str, full_name: str, phone: str, photo_id: str = None, store_no: int = None):
    """
    ⚠️ Legacy-метод.
    Тепер теж пише store_no, але tg_user_id тут нема.
    Рекомендація: використовуй add_participant(...) щоб broadcast працював.
    """
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO participants (username, full_name, phone, photo_id, store_no)
            VALUES (?, ?, ?, ?, ?)
        """, (username, full_name, phone, photo_id, store_no))
        conn.commit()
        return cur.lastrowid


def add_participant(tg_user_id: int, username: str, full_name: str, phone: str, photo_id: str = None, store_no: int = None):
    """Основний метод реєстрації: зберігає tg_user_id + store_no"""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO participants (tg_user_id, username, full_name, phone, photo_id, store_no)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tg_user_id, username, full_name, phone, photo_id, store_no))
        conn.commit()
        return cur.lastrowid


def get_participants():
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, tg_user_id, username, full_name, phone, photo_id, store_no, created_at
            FROM participants
            ORDER BY id ASC
        """)
        return cur.fetchall()


# ==========================================
#   Підрахунок кількості учасників
# ==========================================

def count_participants():
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM participants")
        return cur.fetchone()[0]


def count_participants_today():
    today = date.today().isoformat()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM participants
            WHERE DATE(created_at) = DATE(?)
        """, (today,))
        return cur.fetchone()[0]


def get_all_user_ids():
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT tg_user_id, id FROM participants WHERE tg_user_id IS NOT NULL")
        return cur.fetchall()


# ==========================================
#   Магазини (довідник + статистика)
# ==========================================

def upsert_store(store_no: int, name: str):
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO stores (store_no, name)
            VALUES (?, ?)
            ON CONFLICT(store_no) DO UPDATE SET name=excluded.name
        """, (store_no, name))
        conn.commit()


def get_stores():
    """Повертає довідник магазинів: (store_no, name)"""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT store_no, COALESCE(name,'') FROM stores ORDER BY store_no ASC")
        return cur.fetchall()


def get_store_stats():
    """
    Повертає список: (store_no, name, registrations_count)
    Включає:
    - магазини з довідника stores
    - магазини, які вже зустрілись у participants (навіть якщо нема назви)
    """
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH nums AS (
              SELECT store_no FROM participants WHERE store_no IS NOT NULL
              UNION
              SELECT store_no FROM stores
            )
            SELECT
              n.store_no,
              COALESCE(s.name, '') AS name,
              (SELECT COUNT(*) FROM participants p WHERE p.store_no = n.store_no) AS cnt
            FROM nums n
            LEFT JOIN stores s ON s.store_no = n.store_no
            WHERE n.store_no IS NOT NULL
            ORDER BY n.store_no ASC
        """)
        return cur.fetchall()


# ==========================================
#   Правила розіграшу
# ==========================================

def set_rules(text: str):
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM rules")
        cur.execute("INSERT INTO rules (text) VALUES (?)", (text,))
        conn.commit()


def get_rules():
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT text FROM rules ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None


# ==========================================
#   Очистка таблиць
# ==========================================

def table_counts():
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM participants")
        p = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM rules")
        r = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM winners")
        w = cur.fetchone()[0]
        return p, r, w


def clear_tables():
    stats = {
        "before_participants": 0,
        "before_rules": 0,
        "before_winners": 0,
        "deleted_participants": 0,
        "deleted_rules": 0,
        "deleted_winners": 0,
    }
    with _connect() as conn:
        cur = conn.cursor()
        for tbl, key in [("participants", "participants"), ("rules", "rules"), ("winners", "winners")]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            stats[f"before_{key}"] = cur.fetchone()[0]

        cur.execute("DELETE FROM participants")
        stats["deleted_participants"] = cur.rowcount
        cur.execute("DELETE FROM rules")
        stats["deleted_rules"] = cur.rowcount
        cur.execute("DELETE FROM winners")
        stats["deleted_winners"] = cur.rowcount

        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('participants','rules','winners')")
        except sqlite3.OperationalError:
            pass

        conn.commit()

    with _connect() as conn:
        conn.execute("VACUUM")
    return stats


# ==========================================
#   Переможці
# ==========================================

def pick_random_winner():
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.username, p.full_name, p.phone, p.created_at, p.store_no
            FROM participants p
            LEFT JOIN winners w ON w.participant_id = p.id
            WHERE w.participant_id IS NULL
            ORDER BY RANDOM()
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            return None
        return {
            "participant_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "phone": row[3],
            "created_at": row[4],
            "store_no": row[5],
        }


def save_winner(participant_id: int):
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO winners (participant_id) VALUES (?)", (participant_id,))
        conn.commit()


def get_winners(limit: int = 20):
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT w.created_at, p.id, p.username, p.full_name, p.phone, p.store_no
            FROM winners w
            JOIN participants p ON p.id = w.participant_id
            ORDER BY w.id DESC
            LIMIT ?
        """, (limit,))
        return cur.fetchall()
