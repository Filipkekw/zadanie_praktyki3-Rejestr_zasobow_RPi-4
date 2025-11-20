import sqlite3
from pathlib import Path
import requests

class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._ensure_schema()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT '',
                    purchase_date TEXT DEFAULT '',
                    serial_number TEXT DEFAULT '',
                    description TEXT DEFAULT ''
                );
                """
            )

    # -------------------- operacje na danych --------------------
    def list_items(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT id, name, category, purchase_date, serial_number, description FROM inventory ORDER BY id ASC"
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def add_item(self, name: str, category: str, purchase_date: str,
                 serial_number: str, description: str) -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO inventory (name, category, purchase_date, serial_number, description) VALUES (?, ?, ?, ?, ?)",
                (name, category, purchase_date, serial_number, description),
            )
            conn.commit()
            new_id = cur.lastrowid
        self.notify_reload()  # ⬅️ zawołaj broadcast po zmianie
        return new_id

    def update_item(self, item_id: int, name: str, category: str,
                    purchase_date: str, serial_number: str, description: str) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE inventory SET name=?, category=?, purchase_date=?, serial_number=?, description=? WHERE id=?",
                (name, category, purchase_date, serial_number, description, item_id),
            )
            conn.commit()
        self.notify_reload()

    def delete_item(self, item_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            conn.commit()
        self.notify_reload()

    # -------- powiadomienie FastAPI --------
    def notify_reload(self):
        """Po każdej zmianie w bazie Tkinter powiadamia serwer FastAPI."""
        try:
            requests.post("http://127.0.0.1:8000/notify_reload", timeout=1)
            print("🔁 notify_reload -> wysłano do serwera FastAPI")
        except Exception as e:
            print("⚠️ Nie udało się powiadomić serwera:", e)