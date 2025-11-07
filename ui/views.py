import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import date


class MainView(ttk.Frame):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.categories = ["Narzędzia", "IT", "Oprogramowanie", "Wyposażenie biurowe", "Transport", "BHP", "Meble", "Inne"]
        self._build_pages()
        self.show_list()

    # --------- budowa stron ---------
    def _build_pages(self):
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        # Strona: Lista
        self.list_page = ttk.Frame(self.container)
        self._build_list_page(self.list_page)

        # Strona: Dodawanie
        self.add_page = ttk.Frame(self.container)
        self._build_add_page(self.add_page)

    def _build_list_page(self, parent: ttk.Frame):
        # Górny pasek akcji
        actions = ttk.Frame(parent)
        actions.pack(fill="x", padx=10, pady=(10, 6))

        # Zawsze widoczne
        self.btn_add = ttk.Button(actions, text="Dodaj", command=self.show_add)
        self.btn_add.pack(side="left")

        # Pojawiają się dopiero po zaznaczeniu wiersza
        self.btn_delete = ttk.Button(actions, text="Usuń zaznaczony", command=self.on_delete)
        self.btn_edit = ttk.Button(actions, text="Edytuj", command=self.on_edit)

        # Zawsze widoczny i zawsze ostatni na pasku
        self.btn_refresh = ttk.Button(actions, text="Odśwież", command=self.refresh)
        self.btn_refresh.pack(side="left", padx=(6, 0))

        # Tabela + scrollbar
        table_wrap = ttk.Frame(parent)
        table_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        columns = ("id", "name", "category", "purchase_date", "serial_number", "description")
        self.tree = ttk.Treeview(table_wrap, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Przedmiot")
        self.tree.heading("category", text="Kategoria")
        self.tree.heading("purchase_date", text="Data zakupu")
        self.tree.heading("serial_number", text="Numer seryjny")
        self.tree.heading("description", text="Opis")

        self.tree.column("id", width=20, anchor="center")
        self.tree.column("name", width=200, anchor="w")
        self.tree.column("category", width=105, anchor="w")
        self.tree.column("purchase_date", width=60, anchor="center")
        self.tree.column("serial_number", width=130, anchor="w")
        self.tree.column("description", width=95 , anchor="w")

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        # Reaguj na zmianę zaznaczenia
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_selection_actions())

        # Upewnij się, że na starcie przyciski selekcyjne są ukryte
        self._update_selection_actions()

    def _build_add_page(self, parent: ttk.Frame):
        header = ttk.Label(parent, text="Dodaj zasób", font=("Arial", 12, "bold"))
        header.pack(anchor="w", padx=10, pady=(10, 5))

        form = ttk.Frame(parent)
        form.pack(fill="x", padx=10, pady=10)

        self.add_name_var = tk.StringVar()
        self.add_category_var = tk.StringVar()
        self.add_serial_number_var = tk.StringVar()
        self.add_description_var = tk.StringVar()

        # Nazwa
        ttk.Label(form, text="Przedmiot").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.add_name_var, width=30).grid(row=0, column=1, padx=6, pady=4, sticky="w")

        # Kategoria
        ttk.Label(form, text="Kategoria").grid(row=1, column=0, sticky="w")
        self.add_category_cb = ttk.Combobox(form, textvariable=self.add_category_var, values=self.categories, state="readonly", width=28)
        self.add_category_cb.grid(row=1, column=1, padx=6, pady=4, sticky="w")

        # Data zakupu
        ttk.Label(form, text="Data zakupu").grid(row=2, column=0, sticky="w")
        self.add_date_cb = DateEntry(form, date_pattern="yyyy-mm-dd", state="readonly", width=12, firstweekday="monday", showweeknumbers=False)
        self.add_date_cb.grid(row=2, column=1, padx=6, pady=4, sticky="w")

        # Numer seryjny
        ttk.Label(form, text="Numer seryjny").grid(row=3, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.add_serial_number_var, width=30).grid(row=3, column=1, padx=6, pady=4, sticky="w")

        # Opis
        ttk.Label(form, text="Opis").grid(row=4, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.add_description_var, width=30).grid(row=4, column=1, padx=6, pady=4, sticky="w")

        # Przyciski akcji
        buttons = ttk.Frame(parent)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="Zapisz", command=self.on_add_submit).pack(side="left")
        ttk.Button(buttons, text="Anuluj", command=self.on_add_cancel).pack(side="left", padx=6)

        form.grid_columnconfigure(1, weight=1)

    # --------- nawigacja między stronami ---------
    def _hide_all(self):
        for child in (self.list_page, self.add_page):
            child.pack_forget()

    def show_list(self):
        self._hide_all()
        self.list_page.pack(fill="both", expand=True)
        self.refresh()

    def show_add(self):
        self._hide_all()
        self.add_page.pack(fill="both", expand=True)
        # ustaw domyślne wartości
        self.add_name_var.set("")
        self.add_category_cb.current(0)
        self.add_date_cb.set_date(date.today())
        self.add_serial_number_var.set("")
        self.add_description_var.set("")

    # --------- operacje na liście ---------
    def refresh(self):
        # wyczyść tabelę
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # pobierz i wstaw dane
        try:
            rows = self.db.list_items()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się pobrać danych: {e}")
            return

        for r in rows:
            self.tree.insert(
                "", "end", iid=str(r["id"]),
                values=(r["id"], r["name"], r.get("category", "") or "", r.get("purchase_date", "") or "", r.get("serial_number", "") or "", r.get("description", "") or "")
            )

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def on_delete(self):
        item_id = self._selected_id()

        if not messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz usunąć ten wiersz?"):
            return

        try:
            self.db.delete_item(item_id)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się usunąć: {e}")
            return

        self.refresh()
    
    def _update_selection_actions(self):
        has_sel = bool(self.tree.selection())
        if has_sel:
            # wstaw przed przyciskiem 'Odśwież', żeby kolejność była: Dodaj, Usuń, Edytuj, Odśwież
            if not self.btn_delete.winfo_ismapped():
                self.btn_delete.pack(side="left", padx=(6, 0), before=self.btn_refresh)
                self.btn_edit.pack(side="left", padx=(6, 0), before=self.btn_refresh)
        else:
            # ukryj, jeśli były widoczne
            if self.btn_delete.winfo_ismapped():
                self.btn_delete.pack_forget()
                self.btn_edit.pack_forget()
    def on_edit(self):
        pass

    # --------- zapis na stronie Dodawanie ---------
    def on_add_submit(self):
        name = self.add_name_var.get().strip()
        category = self.add_category_var.get().strip()
        purchase_date = self.add_date_cb.get_date().strftime("%Y-%m-%d")
        serial_number = self.add_serial_number_var.get().strip()
        description = self.add_description_var.get().strip()

        if not name:
            messagebox.showwarning("Walidacja", "Nazwa jest wymagana.")
            return

        try:
            self.db.add_item(
                name=name,
                category=category,
                purchase_date=purchase_date,
                serial_number=serial_number,
                description=description
            )
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się dodać zasobu: {e}")
            return

        # po zapisie wróć na listę i odśwież
        self.show_list()

    def on_add_cancel(self):
        self.show_list()