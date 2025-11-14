import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from tkcalendar import Calendar
from logic.export import export_inventory_to_csv, detect_usb_mount
from pathlib import Path

class MainView(ttk.Frame):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.edit_id = None
        self.categories = ["Narzędzia", "IT", "Oprogramowanie", "Wyposażenie biurowe", "Transport", "BHP", "Meble", "Inne"]
        self.sort_by = "id"
        self.sort_desc = False
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
        actions.pack(fill="x", padx=5, pady=(10, 6))

        # Zawsze widoczne
        self.btn_add = ttk.Button(actions, style="Fixed.TButton", text="Dodaj", command=self.show_add, width=6)
        self.btn_add.pack(side="left")

        # Pojawiają się dopiero po zaznaczeniu wiersza
        self.btn_delete = ttk.Button(actions, style="Fixed.TButton", text="Usuń wybrany", command=self.on_delete, width=13)
        self.btn_edit = ttk.Button(actions, style="Fixed.TButton", text="Edytuj", command=self.show_edit, width=8)

        # Zawsze widoczny i zawsze ostatni na pasku
        self.btn_refresh = ttk.Button(actions, style="Fixed.TButton", text="Odśwież", command=self.refresh, width=8)
        self.btn_refresh.pack(side="left", padx=(6, 0))
        
        ttk.Label(actions, text="Kategoria:").pack(side="left", padx=(4, 4))
        self.filter_category_var = tk.StringVar(value="Wszystkie")
        self.filter_category_cb = ttk.Combobox(actions, textvariable=self.filter_category_var, state="readonly", width=20)
        self.filter_category_cb.pack(side="left")
        self.filter_category_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.btn_export = ttk.Button(actions, text="Eksport CSV", command=self.on_export)
        self.btn_export.pack(side="left", padx=(6, 0))

        search_box = ttk.Frame(actions)
        search_box.pack(side="right", padx=(2, 0))

        ttk.Label(search_box, text="Szukaj:").pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_box, textvariable=self.search_var, width=20)
        self.search_entry.pack(side="left")

        self.search_var.trace_add("write", lambda *args: self.refresh())

        # Tabela + scrollbar
        table_wrap = ttk.Frame(parent)
        table_wrap.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        columns = ("id", "name", "category", "purchase_date", "serial_number", "description")
        self.tree = ttk.Treeview(table_wrap, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Przedmiot")
        self.tree.heading("category", text="Kategoria")
        self.tree.heading("purchase_date", text="Data zakupu", command=self._on_heading_purchase_date)
        self.tree.heading("serial_number", text="Numer seryjny")
        self.tree.heading("description", text="Opis")

        self.tree.column("id", width=15, anchor="center")
        self.tree.column("name", width=170, anchor="w")
        self.tree.column("category", width=125, anchor="w")
        self.tree.column("purchase_date", width=75, anchor="center")
        self.tree.column("serial_number", width=130, anchor="w")
        self.tree.column("description", width=95 , anchor="w")

        self.tree.bind("<B1-Motion>", lambda e: "break")

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        # Reaguj na zmianę zaznaczenia
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_selection_actions())
        self.tree.bind("<Double-1>", lambda e: self.show_edit())
        self.tree.bind("<Delete>", lambda e: self.on_delete())

        # Upewnij się, że na starcie przyciski selekcyjne są ukryte
        self._update_selection_actions()

    def _build_add_page(self, parent: ttk.Frame):
        self.add_header = ttk.Label(parent, text="Dodaj zasób", font=("Arial", 12, "bold"))
        self.add_header.pack(anchor="w", padx=10, pady=(10, 5))

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
        self.add_date_cb = InlineDatePicker(form, date_pattern="yyyy-mm-dd", width=12, firstweekday="monday", showweeknumbers=False)
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
        self.btn_save = ttk.Button(buttons, text="Zapisz", command=self.on_form_submit)
        self.btn_save.pack(side="left")
        self.btn_cancel = ttk.Button(buttons, text="Anuluj", command=self.on_add_cancel)
        self.btn_cancel.pack(side="left", padx=6)

        form.grid_columnconfigure(1, weight=1)

    # --------- nawigacja między stronami ---------
    def _hide_all(self):
        for child in (self.list_page, self.add_page):
            child.pack_forget()

    def show_list(self):
        self._hide_all()
        self.list_page.pack(fill="both", expand=True)
        self.refresh()
        self._update_selection_actions()

    def show_add(self):
        self._hide_all()
        self.add_page.pack(fill="both", expand=True)
        self.edit_id = None
        self.add_header.config(text="Dodaj zasób")
        self.btn_save.config(text="Zapisz")
        # ustaw domyślne wartości
        self.add_name_var.set("")
        self.add_category_cb.current(0)
        self.add_date_cb.set_date(date.today())
        self.add_serial_number_var.set("")
        self.add_description_var.set("")

    def show_edit(self):
        # pobierz ID zaznaczonego wiersza
        sel = self.tree.selection()
        if not sel:
            return
        try:
            item_id = int(sel[0])
        except ValueError:
            return

        # Spróbuj pobrać dane z tabeli (Treeview zawiera wszystkie potrzebne kolumny)
        vals = self.tree.item(sel[0], "values")
        _, name, category, purchase_date, serial_number, description = vals

        # przełącz stan na edycję
        self.edit_id = item_id
        self.add_header.config(text=f"Edytuj zasób (ID: {item_id})")
        self.btn_save.config(text="Zaktualizuj")

        # wypełnij pola formularza
        self.add_name_var.set(name)
        # ustaw kategorię (jeśli nie ma w liście, np. custom → ustaw "Inne")
        if category in self.categories:
            self.add_category_var.set(category)
        else:
            self.add_category_var.set("Inne")

        # ustaw datę
        try:
            d = datetime.strptime(purchase_date, "%Y-%m-%d").date()
            self.add_date_cb.set_date(d)
        except Exception:
            self.add_date_cb.set_date(date.today())

        self.add_serial_number_var.set(serial_number)

        self.add_description_var.set(description)

        # pokaż stronę formularza
        self._hide_all()
        self.add_page.pack(fill="both", expand=True)

    # --------- operacje na liście ---------
    def refresh(self):
        # wyczyść tabelę
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # pobierz dane
        try:
            rows = self.db.list_items()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się pobrać danych: {e}")
            return

        # zasil wartości filtra na podstawie danych
        self._set_filter_values(rows)

        # zastosuj filtr kategorii
        selected_cat = self.filter_category_var.get() if hasattr(self, "filter_category_var") else "Wszystkie"
        if selected_cat != "Wszystkie":
            rows = [r for r in rows if (r.get("category") or "") == selected_cat]
        else:
            # jeśli pokazujemy wszystkie, posortuj po ID rosnąco
            rows = sorted(
                rows,
                key=lambda r: ((r["id"]))
            )
        
        query = (self.search_var.get() if hasattr(self, "search_var") else "").strip().lower()
        if query:
            rows = [r for r in rows if 
                    query in (r.get("name", "") or "").lower()
                    or query in (r.get("serial_number", "") or "").lower()]

        if self.sort_by == "purchase_date":
            rows_with_date = []
            rows_empty = []
            for r in rows:
                s = (r.get("purchase_date") or "").strip()
                try:
                    d = datetime.strptime(s, "%Y-%m-%d").date()
                except Exception:
                    d = None
                if d is None:
                    rows_empty.append(r)
                else:
                    rows_with_date.append((d, r))
            
            rows_with_date.sort(key=lambda t: (t[0], t[1]["id"]), reverse=self.sort_desc)
            rows = [r for _, r in rows_with_date] + rows_empty
        else:
            rows = sorted(rows, key=lambda r: r["id"])

        # wstaw dane
        for r in rows:
            self.tree.insert(
                "", "end", iid=str(r["id"]),
                values=(r["id"], r["name"], r.get("category", "") or "", r.get("purchase_date", "") or "", r.get("serial_number", "") or "", r.get("description", "") or "")
            )
        
        try:
            self.tree.selection_set()
        except Exception:
            for lid in self.tree.selection():
                self.tree.selection_remove(lid)
        self.tree.focus("")
        self._update_selection_actions()
        self._update_sort_indicator()

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

        confirmed = messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz usunąć ten wiersz?")
        if not confirmed:
            self.tree.selection_set()
            self._update_selection_actions()
            return

        try:
            self.db.delete_item(item_id)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się usunąć: {e}")
            return

        self.refresh()

    def on_export(self):
        try:
            default_dir = detect_usb_mount()

            initialdir= str(default_dir) if default_dir else None

            file_path = filedialog.asksaveasfilename(title="Zapisz jako", defaultextension=".csv", initialdir=initialdir, filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")])
            if not file_path:
                return
            rows = self.db.list_items()

            export_inventory_to_csv(rows, Path(file_path))
            messagebox.showinfo("Eksport zakończony", f"Zapisano do pliku:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Błąd eksportu", f"Nie udało się wyeksportować danych:\n{e}")

    def _update_selection_actions(self):
        has_sel = bool(self.tree.selection())
        if has_sel:
            # wstaw przed przyciskiem 'Odśwież', żeby kolejność była: Dodaj, Usuń, Edytuj, Odśwież
            self.btn_delete.pack(side="left", padx=(6,0), before=self.btn_refresh)
            self.btn_edit.pack(side="left", padx=(6,0), before=self.btn_refresh)
        else:
            self.btn_delete.pack_forget()
            self.btn_edit.pack_forget()

    def _set_filter_values(self, rows:list[dict]):
        cats_from_rows = {(r.get("category") or "").strip() for r in rows}
        cats_from_rows.discard("")
        union = set(self.categories) | cats_from_rows
        values = ["Wszystkie"] + sorted(union, key=str.casefold)

        current = self.filter_category_var.get() if hasattr(self, "filter_category_var") else "Wszystkie"
        self.filter_category_cb["values"] = values
        if current not in values:
            self.filter_category_var.set("Wszystkie")

    def _on_heading_purchase_date(self):
        if self.sort_by != "purchase_date":
            self.sort_by = "purchase_date"
            self.sort_desc = False
        elif not self.sort_desc:
            self.sort_desc = True
        else:
            self.sort_by = "id"
            self.sort_desc = False
        self.refresh()

    def _update_sort_indicator(self):
        if self.sort_by == "purchase_date":
            arrow = "▼" if self.sort_desc else "▲"
            self.tree.heading("purchase_date", text=f"Data zakupu {arrow}", command=self._on_heading_purchase_date)
        else:
            self.tree.heading("purchase_date", text="Data zakupu", command=self._on_heading_purchase_date)

    # --------- zapis na stronie Dodawanie ---------
    def on_form_submit(self):
        name = self.add_name_var.get().strip()
        category = self.add_category_var.get().strip()
        purchase_date = self.add_date_cb.get_date().strftime("%Y-%m-%d")
        serial_number = self.add_serial_number_var.get().strip()
        description = self.add_description_var.get().strip()

        if not name:
            messagebox.showwarning("Błąd", "Nazwa jest wymagana.")
            return

        try:
            if self.edit_id is None:
                self.db.add_item(name=name, category=category, purchase_date=purchase_date, serial_number=serial_number, description=description)
            else:
                self.db.update_item(self.edit_id, name=name, category=category, purchase_date=purchase_date, serial_number=serial_number, description=description)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się dodać zasobu: {e}")
            return

        self.edit_id = None
        self.show_list()

    def on_add_cancel(self):
        self.show_list()

# Kalendarz na stronie edycji/dodawania
class InlineDatePicker(ttk.Frame):
    def __init__(self, master, date_pattern="yyyy-mm-dd", width=12,
                 firstweekday="monday", showweeknumbers=False):
        super().__init__(master)
        self._date_pattern = date_pattern
        self._py_pattern = (date_pattern.replace("yyyy", "%Y")
                                         .replace("mm", "%m")
                                         .replace("dd", "%d"))
        self._firstweekday = firstweekday
        self._showweeknumbers = showweeknumbers

        # pole i przycisk
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=width, state="readonly")
        self.entry.pack(side="left")

        self.entry.bind("<Button-1>", self._on_entry_click)

        # stan popupu
        self._overlay = None
        self._popup = None
        self._cal = None
        self._cfg_bind_id = None

    # API zgodne z DateEntry
    def set_date(self, d):
        if isinstance(d, str):
            try:
                d = datetime.strptime(d, self._py_pattern).date()
            except Exception:
                d = None
        if isinstance(d, datetime):
            d = d.date()
        if isinstance(d, date):
            self.var.set(d.strftime(self._py_pattern))
        else:
            self.var.set("")

    def get_date(self):
        s = (self.var.get() or "").strip()
        if not s:
            return date.today()
        try:
            return datetime.strptime(s, self._py_pattern).date()
        except Exception:
            return date.today()

    # wewnętrzne
    def _on_entry_click(self, event):
        self.after(0, self._toggle_overlay)
        return "break"

    def _toggle_overlay(self):
        if self._overlay and self._overlay.winfo_exists():
            self._close_overlay()
        else:
            self._open_overlay()

    def _open_overlay(self):
        root = self.winfo_toplevel()

        # 1) utwórz overlay w miejscu pola daty
        self._overlay = tk.Frame(root, highlightthickness=0, bd=0)
        root.update_idletasks()
        ex = self.entry.winfo_rootx() - root.winfo_rootx()
        ey = self.entry.winfo_rooty() - root.winfo_rooty() + self.entry.winfo_height() + 2
        self._overlay.place(x=ex, y=ey, width=250, height=220)
        self._overlay.lift()
        self._overlay.bind("<Button-1>", self._on_overlay_click, add="+")
        self._overlay.bind("<Escape>", lambda e: self._close_overlay(), add="+")
        self._overlay.focus_set()

        # 2) popup wypełnia overlay (bez dodatkowych przesunięć!)
        self._popup = ttk.Frame(self._overlay, relief="solid", borderwidth=1)
        self._popup.place(x=0, y=0, relwidth=1, relheight=1)

        # 3) zawartość: kalendarz + przyciski
        self._cal = Calendar(
            self._popup,
            selectmode="day",
            firstweekday=self._firstweekday,
            showweeknumbers=self._showweeknumbers
        )
        self._cal.pack(padx=6, pady=6)
        try:
            self._cal.selection_set(self.get_date())
        except Exception:
            pass

        btns = ttk.Frame(self._popup)
        btns.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(btns, text="Anuluj", command=self._close_overlay).pack(side="right")
        ttk.Button(btns, text="Wybierz", command=self._accept_date).pack(side="right", padx=(0, 6))

        # 4) dopasuj rozmiar overlay do rzeczywistych wymiarów popupu
        self._popup.update_idletasks()
        w = self._popup.winfo_width() or self._popup.winfo_reqwidth()
        h = self._popup.winfo_height() or self._popup.winfo_reqheight()
        self._overlay.place_configure(width=w, height=h)

        # 5) bind do repozycjonowania (przy zmianie wielkości/przesunięciu okna)
        self._cfg_bind_id = root.bind("<Configure>", lambda e: self._reposition_overlay(), add="+")
        self._reposition_overlay()

    def _reposition_overlay(self):
        # przesuwamy OVERLAY (nie popup)
        root = self.winfo_toplevel()
        if not (self._overlay and self._overlay.winfo_exists()):
            return
        try:
            root.update_idletasks()
            ex = self.entry.winfo_rootx() - root.winfo_rootx()
            ey = self.entry.winfo_rooty() - root.winfo_rooty() + self.entry.winfo_height() + 2
            self._overlay.place_configure(x=ex, y=ey)
        except Exception:
            pass

    def _on_overlay_click(self, event):
        # zamknij jeśli klik poza popupem
        if self._popup:
            px, py = self._popup.winfo_rootx(), self._popup.winfo_rooty()
            pw, ph = self._popup.winfo_width(), self._popup.winfo_height()
            if not (px <= event.x_root <= px + pw and py <= event.y_root <= py + ph):
                self._close_overlay()
        return "break"  # nie przepuszczaj kliknięcia dalej

    def _accept_date(self):
        try:
            d = self._cal.selection_get()
            self.var.set(d.strftime(self._py_pattern))
        except Exception:
            pass
        self._close_overlay()

    def _close_overlay(self):
        root = self.winfo_toplevel()
        if getattr(self, "_cfg_bind_id", None):
            try:
                root.unbind("<Configure>", self._cfg_bind_id)
            except Exception:
                pass
            self._cfg_bind_id = None

        try:
            if self._popup and self._popup.winfo_exists():
                self._popup.place_forget()
                self._popup.destroy()
        except Exception:
            pass
        try:
            if self._overlay and self._overlay.winfo_exists():
                self._overlay.place_forget()
                self._overlay.destroy()
        except Exception:
            pass
        self._overlay = self._popup = self._cal = None

    def destroy(self):
        self._close_overlay()
        super().destroy()
