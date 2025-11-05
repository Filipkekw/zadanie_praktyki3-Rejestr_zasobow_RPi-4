from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui.views import MainView
from logic.db import Database


def main():
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "inventory.db"

    db = Database(db_path)

    root = tk.Tk()
    root.title("Rejestr zasobów")
    root.geometry("1000x550")

    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    MainView(root, db=db).pack(fill="both", expand=True)

    def on_close():
        try:
            db.close()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()