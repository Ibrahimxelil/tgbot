"""
SQLite veritabanı işlemleri
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional
import config


class Database:
    def __init__(self):
        self.db_path = config.DB_PATH
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    chat_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS flights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    airline TEXT,
                    pnr TEXT,
                    lastname TEXT,
                    flight_date TEXT,
                    checkin_time TEXT,
                    status TEXT DEFAULT 'pending',
                    boarding_pass TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                );
            """)

    def add_user(self, telegram_id: int, username: str, first_name: str):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users (telegram_id, username, first_name, chat_id)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, username, first_name, telegram_id))

    def add_flight(self, user_id: int, airline: str, pnr: str,
                   lastname: str, flight_date: datetime) -> int:
        checkin_time = flight_date - timedelta(hours=24)
        with self._conn() as conn:
            cur = conn.execute("""
                INSERT INTO flights (user_id, chat_id, airline, pnr, lastname, flight_date, checkin_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, user_id, airline, pnr, lastname,
                flight_date.strftime("%d.%m.%Y"),
                checkin_time.isoformat()
            ))
            return cur.lastrowid

    def get_flight(self, flight_id: int) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM flights WHERE id = ?", (flight_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_user_flights(self, user_id: int) -> List[dict]:
        status_map = {
            "pending": "Bekliyor ⏳",
            "in_progress": "İşleniyor ⚙️",
            "done": "Tamamlandı ✅",
            "failed": "Başarısız ❌",
        }
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM flights WHERE user_id = ? ORDER BY flight_date DESC",
                (user_id,)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["status_text"] = status_map.get(d["status"], d["status"])
                result.append(d)
            return result

    def get_pending_flights(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM flights WHERE status = 'pending'"
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["checkin_time"] = datetime.fromisoformat(d["checkin_time"])
                result.append(d)
            return result

    def update_flight_status(self, flight_id: int, status: str, boarding_pass: str = None):
        with self._conn() as conn:
            conn.execute(
                "UPDATE flights SET status = ?, boarding_pass = ? WHERE id = ?",
                (status, boarding_pass, flight_id)
            )
