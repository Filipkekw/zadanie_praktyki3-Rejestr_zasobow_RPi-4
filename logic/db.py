import sqlite3
from pathlib import Path
import requests


class Database:
    def __init__(self, db_path: str | Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self):
        self.conn.execute(
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

    def list_items(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT id, name, category, purchase_date, serial_number, description FROM inventory ORDER BY id ASC"
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def add_item(self, name: str, category: str, purchase_date: str, serial_number: str, description: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO inventory (name, category, purchase_date, serial_number, description) VALUES (?, ?, ?, ?, ?)",
            (name, category, purchase_date, serial_number, description),
        )
        self.conn.commit()
        try:
            requests.post("http://localhost:8000/notify_reload")
        except Exception as e:
            print("Nie udało się wysłać sygnału reload:", e)
        return cur.lastrowid

    def delete_item(self, item_id: int) -> None:
        self.conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        self.conn.commit()
        try:
            requests.post("http://localhost:8000/notify_reload")
        except Exception as e:
            print("Nie udało się wysłać sygnału reload:", e)

    def update_item(self, item_id: int, name: str, category: str, purchase_date: str, serial_number: str, description:str) -> None:
        self.conn.execute(
            "UPDATE inventory SET name=?, category=?, purchase_date=?, serial_number=?, description=? WHERE id=?",
            (name, category, purchase_date, serial_number, description, item_id),
        )
        self.conn.commit()
        try:
            requests.post("http://localhost:8000/notify_reload")
        except Exception as e:
            print("Nie udało się wysłać sygnału reload:", e)

    def close(self):
        self.conn.close()