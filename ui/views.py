from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QStackedWidget, QGridLayout, QCalendarWidget, QRadioButton, QCheckBox, QDialog, QDialogButtonBox, QFileDialog
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QTextCharFormat, QBrush, QColor

from logic.db import Database
from logic.export import export_inventory_to_csv, detect_usb_mount

class ItemCard(QFrame):
    """Ramka reprezentująca pojedynczy element (jak karta we Flutterze)."""

    def __init__(
        self,
        item: dict,
        on_clicked,
        on_double_clicked=None,
        parent: Optional[QWidget] = None,
        delete_mode: bool = False,
        checked: bool = False,
    ):
        super().__init__(parent)
        self.item = item
        self.on_clicked = on_clicked
        self.on_double_clicked = on_double_clicked

        self.setObjectName("itemCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        # checkbox po lewej w trybie usuwania
        self.checkbox: Optional[QCheckBox] = None
        if delete_mode:
            self.checkbox = QCheckBox()
            self.checkbox.setChecked(checked)
            self.checkbox.clicked.connect(lambda _: self.on_clicked(self.item, self))
            layout.addWidget(self.checkbox)

        name_label = QLabel(item.get("name", "") or "")
        name_label.setObjectName("nameLabel")
        category_label = QLabel(item.get("category", "") or "")
        date_label = QLabel(item.get("purchase_date", "") or "")
        sn_label = QLabel(item.get("serial_number", "") or "")

        desc = item.get("description", "") or ""
        if len(desc) > 60:
            desc = desc[:60] + "..."
        desc_label = QLabel(desc)
        desc_label.setObjectName("descLabel")

        name_label.setMinimumWidth(140)
        desc_label.setMinimumWidth(180)

        layout.addWidget(name_label, 2)
        layout.addWidget(category_label, 1)
        layout.addWidget(date_label, 1)
        layout.addWidget(sn_label, 2)
        layout.addWidget(desc_label, 3)

        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_clicked:
            self.on_clicked(self.item, self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_double_clicked:
            self.on_double_clicked(self.item, self)
        super().mouseDoubleClickEvent(event)

class DateDialog(QCalendarWidget):
    """Nie używamy już osobnego QDialog – logika daty jest w DateLineEdit."""


class DateLineEdit(QLineEdit):
    """
    Pole tekstowe tylko do wyświetlania wybranej daty.
    Kliknięcie otwiera kalendarz, użytkownik nie wpisuje nic ręcznie.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self._date = QDate.currentDate()
        self._update_text()

    def _update_text(self):
        if self._date and self._date.isValid():
            self.setText(self._date.toString("yyyy-MM-dd"))
        else:
            self.setText("")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            dlg = QDialog(self)
            dlg.setWindowTitle("Wybierz datę zakupu")
            dlg.resize(300, 250)
            layout = QVBoxLayout(dlg)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(4)

            cal = QCalendarWidget(dlg)
            # ciemny motyw kalendarza
            cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
            fmt = QTextCharFormat()
            fmt.setForeground(QBrush(Qt.white))
            fmt.setBackground(QBrush(QColor("#1E1E1E")))
            cal.setWeekdayTextFormat(Qt.Monday, fmt)
            cal.setWeekdayTextFormat(Qt.Tuesday, fmt)
            cal.setWeekdayTextFormat(Qt.Wednesday, fmt)
            cal.setWeekdayTextFormat(Qt.Thursday, fmt)
            cal.setWeekdayTextFormat(Qt.Friday, fmt)
            cal.setWeekdayTextFormat(Qt.Saturday, fmt)
            cal.setWeekdayTextFormat(Qt.Sunday, fmt)
            cal.setStyleSheet("""
                QCalendarWidget {
                    background-color: #121212;
                    color: #FFFFFF;
                    border: 1px solid #333333;
                }
                QCalendarWidget QWidget#qt_calendar_navigationbar {
                    background-color: #1E1E1E;
                }
                QCalendarWidget QToolButton {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    border: none;
                }
                QCalendarWidget QAbstractItemView:enabled {
                    background-color: #121212;
                    color: #FFFFFF;
                    selection-background-color: #1976D2;
                    selection-color: #FFFFFF;
                    gridline-color: #333333;
                }
                QLabel#status_label {
                    color: #AAAAAA;
                    font-size: 11px;
                } 
            """)
            cal.setSelectedDate(self._date or QDate.currentDate())
            layout.addWidget(cal, 1)

            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dlg
            )
            buttons.accepted.connect(dlg.accept)
            buttons.rejected.connect(dlg.reject)
            layout.addWidget(buttons)

            if dlg.exec_() == QDialog.Accepted:
                d = cal.selectedDate()
                if d.isValid():
                    self._date = d
                    self._update_text()
        super().mousePressEvent(event)

    def setDate(self, date: QDate):
        if date and date.isValid():
            self._date = date
        else:
            self._date = QDate.currentDate()
        self._update_text()

    def date(self) -> QDate:
        return self._date


class MainView(QWidget):
    """Główny widok aplikacji: lista, formularz i strona sortowania/filtrowania."""
            
    reload_signal = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # --- baza danych ---
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "inventory.db"
        self.db = Database(db_path)

        self.items: list[dict] = []
        self.search_query = ""
        self.selected_item: Optional[dict] = None
        self.selected_card: Optional[ItemCard] = None

        self._form_mode = "add"  # 'add' lub 'edit'

        # sortowanie / filtrowanie
        self.sort_mode: str = "id"  # 'id', 'date_asc', 'date_desc'
        self.filter_categories: list[str] = []
        self.all_categories: list[str] = [
            "Narzędzia",
            "IT",
            "Oprogramowanie",
            "Wyposażenie biurowe",
            "Transport",
            "BHP",
            "Meble",
            "Inne",
        ]
        self.action_mode: str = "normal"
        self.delete_mode: bool = False
        self.selected_ids: set[int] = set()

        # elementy strony sortowania (ustawione w _build_sort_page)
        self.rb_sort_id: Optional[QRadioButton] = None
        self.rb_sort_date_asc: Optional[QRadioButton] = None
        self.rb_sort_date_desc: Optional[QRadioButton] = None
        self.cat_checkboxes: list[QCheckBox] = []

        # ---------- STACKED WIDGET: LISTA / FORMULARZ / SORT/FILTR ----------
        self.stack = QStackedWidget(self)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.stack)

        # Strona 0: lista
        self.list_page = QWidget()
        self._build_list_page(self.list_page)
        self.stack.addWidget(self.list_page)

        # Strona 1: formularz
        self.form_page = QWidget()
        self._build_form_page(self.form_page)
        self.stack.addWidget(self.form_page)

        # Strona 2: sortowanie i filtrowanie
        self.sort_page = QWidget()
        self._build_sort_page(self.sort_page)
        self.stack.addWidget(self.sort_page)
        
        # Strona 3: podgląd pojedycznego elementu
        self.preview_page = QWidget()
        self._build_preview_page(self.preview_page)
        self.stack.addWidget(self.preview_page)

        self.preview_item: Optional[dict] = None

        # Styl ciemny
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #FFFFFF;
                font-size: 13px;
            }
            QScrollArea {
                background-color: #121212;
                border: none;
            }
            QFrame#itemCard {
                background-color: #121212;
                border-radius: 6px;
            }
            QFrame#itemCard[selected="true"] {
                background-color: #263238;
            }
            QFrame#itemCard:hover {
                background-color: #1A1A1A;
            }
            QLabel#descLabel {
                color: #CCCCCC;
            }
            QLabel#headerLabel {
                font-weight: bold;
                color: #FFFFFF;
            }
            QLineEdit, QComboBox {
                background-color: #1E1E1E;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 2px 4px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #1976D2;
            }
            QPushButton {
                background-color: #1976D2;
                color: white;
                border-radius: 4px;
                padding: 2px 6px;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
        """)


        self.reload_signal.connect(self.load_items)

        self.load_items()

    # ---------- STRONA LISTY ----------

    def _build_list_page(self, page: QWidget):
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Górny pasek: sort/filtr + szukaj
        top_bar = QWidget()
        top_bar.setFixedHeight(32)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        self.btn_sort_filter = QPushButton("Sortuj / Filtruj")
        self.btn_sort_filter.setFixedHeight(24)
        self.btn_sort_filter.clicked.connect(self.on_sort_filter_clicked)

        self.btn_export = QPushButton("Eksport CSV")
        self.btn_export.setFixedHeight(24)
        self.btn_export.clicked.connect(self.on_export_clicked)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Szukaj po nazwie / SN / opisie...")
        self.search_edit.setFixedHeight(24)
        self.search_edit.textChanged.connect(self.on_search_changed)

        top_layout.addWidget(self.btn_sort_filter)
        top_layout.addWidget(self.btn_export)
        top_layout.addStretch(1)
        top_layout.addWidget(self.search_edit)

        layout.addWidget(top_bar)

        # Nagłówki
        header = QWidget()
        header.setFixedHeight(22)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(6)

        hdr_name = QLabel("Nazwa")
        hdr_cat = QLabel("Kategoria")
        hdr_date = QLabel("Data")
        hdr_sn = QLabel("Nr seryjny")
        hdr_desc = QLabel("Opis")

        for hdr in (hdr_name, hdr_cat, hdr_date, hdr_sn, hdr_desc):
            hdr.setObjectName("headerLabel")

        header_layout.addWidget(hdr_name, 2)
        header_layout.addWidget(hdr_cat, 1)
        header_layout.addWidget(hdr_date, 1)
        header_layout.addWidget(hdr_sn, 2)
        header_layout.addWidget(hdr_desc, 3)

        self.status_label = QLabel("")
        self.status_label.setFixedHeight(16)
        layout.addWidget(self.status_label)

        layout.addWidget(header)

        # Lista
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)

        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area, 1)

        # Dolny pasek
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(36)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)

        self.btn_delete = QPushButton("Usuń")
        self.btn_delete.setFixedHeight(24)
        self.btn_delete.clicked.connect(self.on_delete_clicked)

        self.btn_add = QPushButton("Dodaj")
        self.btn_add.setFixedHeight(24)
        self.btn_add.clicked.connect(self.on_add_clicked)

        self.btn_edit = QPushButton("Edytuj")
        self.btn_edit.setFixedHeight(24)
        self.btn_edit.clicked.connect(self.on_edit_clicked)

        bottom_layout.addWidget(self.btn_delete)
        bottom_layout.addWidget(self.btn_add)
        bottom_layout.addWidget(self.btn_edit)

        layout.addWidget(bottom_bar)

    # ---------- STRONA FORMULARZA ----------

    def _build_form_page(self, page: QWidget):
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self.form_title = QLabel("Dodaj przedmiot")
        self.form_title.setObjectName("headerLabel")
        layout.addWidget(self.form_title)

        self.name_edit = QLineEdit()
        self.category_cb = QComboBox()
        self.category_cb.addItems(self.all_categories)

        self.date_edit = DateLineEdit()
        self.sn_edit = QLineEdit()
        self.desc_edit = QLineEdit()

        for w in (self.name_edit, self.sn_edit, self.desc_edit, self.category_cb):
            w.setMinimumHeight(22)
            w.setMaximumHeight(24)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)

        row = 0
        grid.addWidget(QLabel("Nazwa:"), row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.name_edit, row, 1)
        row += 1

        grid.addWidget(QLabel("Kategoria:"), row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.category_cb, row, 1)
        row += 1

        grid.addWidget(QLabel("Data zakupu:"), row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.date_edit, row, 1)
        row += 1

        grid.addWidget(QLabel("Numer seryjny:"), row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.sn_edit, row, 1)
        row += 1

        grid.addWidget(QLabel("Opis:"), row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.desc_edit, row, 1)
        row += 1

        form_center = QWidget()
        form_center.setLayout(grid)
        layout.addWidget(form_center)
        layout.addStretch(1)

        # pasek przycisków
        buttons_bar = QWidget()
        buttons_layout = QHBoxLayout(buttons_bar)
        buttons_layout.setContentsMargins(0, 2, 0, 0)
        buttons_layout.setSpacing(6)

        self.btn_form_cancel = QPushButton("Anuluj")
        self.btn_form_save = QPushButton("Zapisz")

        for b in (self.btn_form_cancel, self.btn_form_save):
            b.setMinimumHeight(24)
            b.setMaximumHeight(26)

        self.btn_form_cancel.clicked.connect(self.on_form_cancel)
        self.btn_form_save.clicked.connect(self.on_form_save)

        buttons_layout.addWidget(self.btn_form_cancel)
        buttons_layout.addWidget(self.btn_form_save)

        layout.addWidget(buttons_bar)

    # ---------- STRONA SORTOWANIA / FILTROWANIA ----------

    def _build_sort_page(self, page: QWidget):
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        title = QLabel("Sortowanie i filtrowanie")
        title.setObjectName("headerLabel")
        layout.addWidget(title)

        layout.addWidget(QLabel("Sortowanie:"))

        self.rb_sort_id = QRadioButton("Według ID (domyślnie)")
        self.rb_sort_date_asc = QRadioButton("Data zakupu: od najstarszych")
        self.rb_sort_date_desc = QRadioButton("Data zakupu: od najnowszych")

        layout.addWidget(self.rb_sort_id)
        layout.addWidget(self.rb_sort_date_asc)
        layout.addWidget(self.rb_sort_date_desc)

        layout.addSpacing(8)
        layout.addWidget(QLabel("Filtruj po kategoriach:"))

        self.cat_checkboxes = []
        for cat in self.all_categories:
            cb = QCheckBox(cat)
            self.cat_checkboxes.append(cb)
            layout.addWidget(cb)

        layout.addStretch(1)

        # Dolny pasek przycisków
        buttons_bar = QWidget()
        buttons_layout = QHBoxLayout(buttons_bar)
        buttons_layout.setContentsMargins(0, 2, 0, 0)
        buttons_layout.setSpacing(6)

        self.btn_sort_cancel = QPushButton("Anuluj")
        self.btn_sort_apply = QPushButton("Zastosuj")

        self.btn_sort_cancel.clicked.connect(self.on_sort_cancel)
        self.btn_sort_apply.clicked.connect(self.on_sort_apply)

        buttons_layout.addWidget(self.btn_sort_cancel)
        buttons_layout.addWidget(self.btn_sort_apply)

        layout.addWidget(buttons_bar)

    # ---------- STRONA PODGLĄDU ----------
    def _build_preview_page(self, page: QWidget):
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        title = QLabel("Podgląd przedmiotu")
        title.setObjectName("headerLabel")
        layout.addWidget(title)

        # Pola podglądu
        self.prev_name_label = QLabel("")
        self.prev_category_label = QLabel("")
        self.prev_date_label = QLabel("")
        self.prev_sn_label = QLabel("")
        self.prev_desc_label = QLabel("")

        def row(label: str, val_label: QLabel) -> QWidget:
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(6)
            lbl = QLabel(label)
            lbl.setMinimumWidth(110)
            l.addWidget(lbl)
            l.addWidget(val_label, 1)
            return w

        layout.addWidget(row("Nazwa:", self.prev_name_label))
        layout.addWidget(row("Kategoria:", self.prev_category_label))
        layout.addWidget(row("Data zakupu:", self.prev_date_label))
        layout.addWidget(row("Numer seryjny:", self.prev_sn_label))

        desc_container = QWidget()
        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.setSpacing(2)
        desc_layout.addWidget(QLabel("Opis:"))
        desc_layout.addWidget(self.prev_desc_label)
        layout.addWidget(desc_container)

        layout.addStretch(1)

        # Dolny pasek przycisków: Edytuj / Usuń
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 2, 0, 0)
        bottom_layout.setSpacing(6)

        btn_back = QPushButton("Wróć")
        btn_edit = QPushButton("Edytuj")
        btn_delete = QPushButton("Usuń")

        btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(self.list_page))
        btn_edit.clicked.connect(self.on_preview_edit_clicked)
        btn_delete.clicked.connect(self.on_preview_delete_clicked)

        bottom_layout.addWidget(btn_back)
        bottom_layout.addWidget(btn_edit)
        bottom_layout.addWidget(btn_delete)

        layout.addWidget(bottom_bar)

    # ---------- dane / lista ----------

    def load_items(self):
        try:
            self.items = self.db.list_items()
        except Exception as e:
            QMessageBox.critical(self, "Błąd bazy", str(e))
            self.items = []
        self.refresh_list()

    def refresh_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        self.selected_item = None
        self.selected_card = None

        items = list(self.items)

        # wyszukiwanie
        q = (self.search_query or "").strip().lower()
        if q:
            items = [
                it for it in items
                if q in (it.get("name", "") or "").lower()
                or q in (it.get("serial_number", "") or "").lower()
                or q in (it.get("description", "") or "").lower()
            ]

        # filtrowanie po kategoriach
        if self.filter_categories:
            items = [
                it for it in items
                if (it.get("category") or "") in self.filter_categories
            ]

        # sortowanie
        if self.sort_mode == "date_asc":
            items.sort(key=lambda it: it.get("purchase_date", "") or "")
        elif self.sort_mode == "date_desc":
            items.sort(key=lambda it: it.get("purchase_date", "") or "", reverse=True)
        else:  # 'id'
            items.sort(key=lambda it: it.get("id", 0))

        if not items:
            self.list_layout.addWidget(QLabel("Brak danych do wyświetlenia."))
        else:
            for it in items:
                checked = it["id"] in getattr(self, "selected_ids", set())
                card = ItemCard(
                    it,
                    self.on_item_clicked,
                    self.on_item_double_clicked,
                    parent=self.list_container,
                    delete_mode=getattr(self, "delete_mode", False),
                    checked=checked,
                )
                self.list_layout.addWidget(card)

        self.list_layout.addStretch(1)

    def _current_view_items(self) -> list[dict]:
        items = list(self.items)

        # wyszukiwanie
        q = (self.search_query or "").strip().lower()
        if q:
            items = [
                it for it in items
                if q in (it.get("name", "") or "").lower()
                or q in (it.get("serial_number", "") or "").lower()
                or q in (it.get("description", "") or "").lower()
            ]

        # filtrowanie po kategoriach
        if self.filter_categories:
            items = [
                it for it in items
                if (it.get("category") or "") in self.filter_categories
            ]

        # sortowanie
        if self.sort_mode == "date_asc":
            items.sort(key=lambda it: it.get("purchase_date", "") or "")
        elif self.sort_mode == "date_desc":
            items.sort(key=lambda it: it.get("purchase_date", "") or "", reverse=True)
        else:  # 'id'
            items.sort(key=lambda it: it.get("id", 0))

        return items

    # ---------- obsługa UI: lista ----------

    def on_sort_filter_clicked(self):
        # Ustaw stan przy wejściu na stronę sortowania
        if self.sort_mode == "date_asc":
            self.rb_sort_date_asc.setChecked(True)
        elif self.sort_mode == "date_desc":
            self.rb_sort_date_desc.setChecked(True)
        else:
            self.rb_sort_id.setChecked(True)

        # Ustaw checkboxy kategorii
        for cb in self.cat_checkboxes:
            cb.setChecked(cb.text() in self.filter_categories)

        self.stack.setCurrentWidget(self.sort_page)

    def on_search_changed(self, text: str):
        self.search_query = text
        self.refresh_list()

    def on_item_clicked(self, item: dict, card: ItemCard):
        # TRYB USUWANIA – wielokrotny wybór
        if self.delete_mode:
            item_id = item["id"]
            # przełącz zaznaczenie
            if item_id in self.selected_ids:
                self.selected_ids.remove(item_id)
                card.setProperty("selected", "false")
            else:
                self.selected_ids.add(item_id)
                card.setProperty("selected", "true")

            card.style().unpolish(card)
            card.style().polish(card)

            # zaktualizuj komunikat o liczbie zaznaczonych
            if self.selected_ids:
                self.status_label.setText(
                    f"Zaznaczono {len(self.selected_ids)} element(y) do usunięcia."
                )
            else:
                self.status_label.setText("Tryb usuwania: zaznacz elementy do usunięcia.")
            return

        # TRYB EDYCJI (po naciśnięciu przycisku „Edytuj”)
        if self.action_mode == "edit":
            self._form_mode = "edit"
            self.form_title.setText("Edytuj przedmiot")
            self.selected_item = item

            self.name_edit.setText(item.get("name", "") or "")

            cat = item.get("category", "") or ""
            idx = self.category_cb.findText(cat)
            if idx >= 0:
                self.category_cb.setCurrentIndex(idx)

            date_str = item.get("purchase_date", "") or ""
            d = QDate.fromString(date_str, "yyyy-MM-dd")
            if not d.isValid():
                d = QDate.currentDate()
            self.date_edit.setDate(d)

            self.sn_edit.setText(item.get("serial_number", "") or "")
            self.desc_edit.setText(item.get("description", "") or "")

            self.stack.setCurrentWidget(self.form_page)
            self.action_mode = "normal"
            self.status_label.setText("")
            return

        # TRYB NORMALNY – tylko zaznaczenie elementu
        if self.selected_card is not None:
            self.selected_card.setProperty("selected", "false")
            self.selected_card.style().unpolish(self.selected_card)
            self.selected_card.style().polish(self.selected_card)

        self.selected_item = item
        self.selected_card = card
        card.setProperty("selected", "true")
        card.style().unpolish(card)
        card.style().polish(card)

    def on_item_double_clicked(self, item: dict, card: ItemCard):
        """Podwójne kliknięcie: otwarcie strony podglądu."""
        # w trybie usuwania ignorujemy double-click, bo tam jest logika checkboxów
        if getattr(self, "delete_mode", False):
            return

        # zapamiętaj element
        self.preview_item = item

        # ustaw pola na stronie podglądu
        self.prev_name_label.setText(item.get("name", "") or "")
        self.prev_category_label.setText(item.get("category", "") or "")
        self.prev_date_label.setText(item.get("purchase_date", "") or "")
        self.prev_sn_label.setText(item.get("serial_number", "") or "")
        desc = item.get("description", "") or "(brak opisu)"
        self.prev_desc_label.setText(desc)

        # przełącz na stronę podglądu
        self.stack.setCurrentWidget(self.preview_page)

    def on_add_clicked(self):
        if self.delete_mode:
            # w trybie usuwania: wykonaj kasowanie zaznaczonych
            if not self.selected_ids:
                # nic nie wybrano
                return
            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć {len(self.selected_ids)} element(y)?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                try:
                    for id_ in list(self.selected_ids):
                        self.db.delete_item(id_)
                except Exception as e:
                    QMessageBox.critical(self, "Błąd usuwania", str(e))
            # niezależnie od potwierdzenia wyjdź z trybu usuwania
            self.delete_mode = False
            self.selected_ids.clear()
            self.status_label.setText("")
            self.btn_delete.setText("Usuń")
            self.btn_add.setText("Dodaj")
            self.btn_edit.setEnabled(True)
            self.load_items()
            return

        # normalny tryb: otwórz formularz dodawania
        self.action_mode = "normal"
        self._form_mode = "add"
        self.form_title.setText("Dodaj przedmiot")
        self.name_edit.clear()
        self.category_cb.setCurrentIndex(0)
        self.date_edit.setDate(QDate.currentDate())
        self.sn_edit.clear()
        self.desc_edit.clear()
        self.stack.setCurrentWidget(self.form_page)

    def on_edit_clicked(self):
        # unikamy mieszania z trybem usuwania
        if self.delete_mode:
            return

        self.action_mode = "edit"
        self.status_label.setText("Tryb edycji: kliknij element na liście, który chcesz edytować.")

    def on_delete_clicked(self):
        # przełącznik trybu usuwania
        if not self.delete_mode:
            # włącz tryb usuwania
            self.delete_mode = True
            self.selected_ids.clear()
            self.status_label.setText("Tryb usuwania: zaznacz elementy do usunięcia.")
            self.btn_delete.setText("Anuluj")
            self.btn_add.setText("Usuń zaznaczone")
            self.btn_edit.setEnabled(False)
            self.refresh_list()
        else:
            # wyłącz tryb usuwania (anuluj)
            self.delete_mode = False
            self.selected_ids.clear()
            self.status_label.setText("")
            self.btn_delete.setText("Usuń")
            self.btn_add.setText("Dodaj")
            self.btn_edit.setEnabled(True)
            self.refresh_list()

    # ---------- obsługa UI: formularz ----------

    def on_form_cancel(self):
        self.action_mode = "normal"
        self.status_label.setText("")
        self.stack.setCurrentWidget(self.list_page)

    def on_form_save(self):
        self.action_mode = "normal"
        self.status_label.setText("")
        
        data = {
            "name": self.name_edit.text().strip(),
            "category": self.category_cb.currentText().strip(),
            "purchase_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "serial_number": self.sn_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
        }

        if not data["name"]:
            QMessageBox.warning(self, "Błąd", "Nazwa jest wymagana.")
            return

        try:
            if self._form_mode == "add":
                self.db.add_item(
                    data["name"],
                    data["category"],
                    data["purchase_date"],
                    data["serial_number"],
                    data["description"],
                )
            else:
                self.db.update_item(
                    self.selected_item["id"],
                    data["name"],
                    data["category"],
                    data["purchase_date"],
                    data["serial_number"],
                    data["description"],
                )
            self.load_items()
            self.stack.setCurrentWidget(self.list_page)
        except Exception as e:
            QMessageBox.critical(self, "Błąd zapisu", str(e))

    # ---------- obsługa UI: strona sortowania ----------

    def on_sort_cancel(self):
        self.stack.setCurrentWidget(self.list_page)

    def on_sort_apply(self):
        # ustal tryb sortowania
        if self.rb_sort_date_asc.isChecked():
            self.sort_mode = "date_asc"
        elif self.rb_sort_date_desc.isChecked():
            self.sort_mode = "date_desc"
        else:
            self.sort_mode = "id"

        # zaktualizuj listę wybranych kategorii
        self.filter_categories = [cb.text() for cb in self.cat_checkboxes if cb.isChecked()]

        self.refresh_list()
        self.stack.setCurrentWidget(self.list_page)

    # ---------- obsługa UI: strona podglądu ----------
    def on_preview_edit_clicked(self):
        """Edytuj aktualnie podglądany element."""
        if not self.preview_item:
            return

        it = self.preview_item
        self._form_mode = "edit"
        self.form_title.setText("Edytuj przedmiot")
        self.selected_item = it

        self.name_edit.setText(it.get("name", "") or "")

        cat = it.get("category", "") or ""
        idx = self.category_cb.findText(cat)
        if idx >= 0:
            self.category_cb.setCurrentIndex(idx)

        date_str = it.get("purchase_date", "") or ""
        d = QDate.fromString(date_str, "yyyy-MM-dd")
        if not d.isValid():
            d = QDate.currentDate()
        self.date_edit.setDate(d)

        self.sn_edit.setText(it.get("serial_number", "") or "")
        self.desc_edit.setText(it.get("description", "") or "")

        self.stack.setCurrentWidget(self.form_page)

    def on_preview_delete_clicked(self):
        """Usuń aktualnie podglądany element."""
        if not self.preview_item:
            return

        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć „{self.preview_item.get('name', '')}”?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_item(self.preview_item["id"])
                self.load_items()
                self.stack.setCurrentWidget(self.list_page)
                self.preview_item = None
            except Exception as e:
                QMessageBox.critical(self, "Błąd usuwania", str(e))

    # ---------- eksport do CSV ----------
    def on_export_clicked(self):
        """Eksport widocznych danych do CSV, z domyślnym katalogiem na pendrivie."""

        # Spróbuj wykryć podłączony pendrive
        usb_dir = detect_usb_mount()
        if usb_dir:
            start_dir = usb_dir
        else:
            # jeśli nie ma pendrive'a, zaczynamy z katalogu domowego
            start_dir = Path.home()

        default_path = start_dir / "export.csv"

        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz eksport CSV",
            str(default_path),
            "Pliki CSV (*.csv);;Wszystkie pliki (*.*)",
        )
        if not path_str:
            return

        try:
            # UWAGA: tu możesz wybrać, czy eksportujesz CAŁĄ bazę,
            # czy tylko przefiltrowaną listę:
            # 1) cała baza:
            # rows = self.db.list_items()
            #
            # 2) tylko to, co jest po filtrach/szukaniu/sortowaniu:
            rows = self._current_view_items()

            export_inventory_to_csv(rows, Path(path_str))
            QMessageBox.information(
                self,
                "Eksport zakończony",
                f"Zapisano dane do pliku:\n{path_str}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Błąd eksportu", str(e))