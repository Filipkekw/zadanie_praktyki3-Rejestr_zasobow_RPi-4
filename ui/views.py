import tkinter as tk
from tkinter import ttk, messagebox


class MainView(ttk.Frame):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        # Lista dostępnych kategorii
        self.categories = ["Narzędzia", "Meble", "RTV", "AGD", "IT", "Inne"]
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Formularz dodawania
        form = ttk.Frame(self)
        form.pack(fill="x", padx=10, pady=10)

        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.serial_number_var = tk.StringVar()

        ttk.Label(form, text="Nazwa").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.name_var, width=10).grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Kategoria").grid(row=0, column=2, sticky="w")
        # Combobox zamiast Entry + brak możliwości pisania
        self.category_cb = ttk.Combobox(form, textvariable=self.category_var, values=self.categories, state="readonly", width=10)
        self.category_cb.grid(row=0, column=3, padx=5)
        self.category_cb.current(0)  # domyślne: "Narzędzia"

        ttk.Label(form, text="Ilość").grid(row=0, column=4, sticky="w")
        ttk.Entry(form, textvariable=self.quantity_var, width=8).grid(row=0, column=5, padx=5)

        ttk.Label(form, text="Numer seryjny").grid(row=0, column=6, sticky="w")
        ttk.Entry(form, textvariable=self.serial_number_var, width=18).grid(row=0, column=7, padx=5)

        ttk.Button(form, text="Dodaj", command=self.on_add).grid(row=0, column=8, padx=(10, 0))

        # Tabela
        columns = ("id", "name", "category", "quantity", "serial_number")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Nazwa")
        self.tree.heading("category", text="Kategoria")
        self.tree.heading("quantity", text="Ilość")
        self.tree.heading("serial_number", text="Numer seryjny")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("name", width=160, anchor="w")
        self.tree.column("category", width=100, anchor="w")
        self.tree.column("quantity", width=80, anchor="e")
        self.tree.column("serial_number", width=150, anchor="w")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        vsb.pack(side="left", fill="y", pady=(0, 10))

        # Akcje
        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(actions, text="Usuń zaznaczony", command=self.on_delete).pack(anchor="w")
        ttk.Button(actions, text="Odśwież", command=self.refresh).pack(anchor="w", pady=(5,0))

    def refresh(self):
        # Wyczyść tabelę
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # Pobierz dane z DB
        try:
            rows = self.db.list_items()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się pobrać danych: {e}")
            return

        # Wstaw dane
        for r in rows:
            self.tree.insert(
                "", "end", iid=str(r["id"]),
                values=(r["id"], r["name"], r.get("category", "") or "", r.get("quantity", 0), r.get("serial_number", "") or "")
            )

    def on_add(self):
        name = self.name_var.get().strip()
        category = self.category_var.get().strip()  # z Comboboxa
        serial_number = self.serial_number_var.get().strip()
        qty_raw = self.quantity_var.get().strip()

        if not name:
            messagebox.showwarning("Walidacja", "Nazwa jest wymagana.")
            return
        try:
            quantity = int(qty_raw or "0")
            if quantity < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Walidacja", "Ilość musi być liczbą całkowitą >= 0.")
            return

        try:
            self.db.add_item(name=name, category=category, quantity=quantity, serial_number=serial_number)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się dodać zasobu: {e}")
            return

        # Reset formularza i odświeżenie
        self.name_var.set("")
        self.category_cb.current(0)  # wróć do domyślnej kategorii
        self.quantity_var.set("1")
        self.serial_number_var.set("")
        self.refresh()

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
        if not item_id:
            messagebox.showinfo("Informacja", "Zaznacz wiersz do usunięcia.")
            return

        if not messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz usunąć ten wiersz?"):
            return

        try:
            self.db.delete_item(item_id)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się usunąć: {e}")
            return

        self.refresh()