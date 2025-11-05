import sqlite3
from pathlib import Path


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
                quantity INTEGER NOT NULL DEFAULT 0,
                serial_number TEXT DEFAULT ''
            );
            """
        )
        self.conn.commit()

    def list_items(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT id, name, category, quantity, serial_number FROM inventory ORDER BY id ASC"
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def add_item(self, name: str, category: str, quantity: int, serial_number: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO inventory (name, category, quantity, serial_number) VALUES (?, ?, ?, ?)",
            (name, category, quantity, serial_number),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_item(self, item_id: int) -> None:
        self.conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()