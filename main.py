from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ui.views import MainView
from logic.db import Database
import tkinter.font as tkfont


def main():
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "inventory.db"

    db = Database(db_path)

    root = tk.Tk()
    root.title("Rejestr zasobów")
    root.geometry("800x480")

    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")

    default_font = tkfont.nametofont("TkDefaultFont")
    style.configure("Treeview", font=default_font)
    heading_font = tkfont.Font(family=default_font.cget("family"),
                            size=default_font.cget("size"),
                            weight="normal")
    style.configure("Treeview.Heading", font=heading_font)

    style.configure("Fixed.TButton", padding=(4, 4))
    style.configure("Fixed.TButton", width=15)

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