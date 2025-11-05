# Rejestr zasobow RPi 4

Lekka aplikacja do rejestru zasobów na Raspberry Pi 4 (Tkinter + SQLite). Interfejs w Tkinter, baza danych w pliku data/inventory.db.

Funkcje
- automatyczne połączenie z bazą SQLite (tworzy tabelę przy pierwszym uruchomieniu)
- podgląd zasobów w tabeli (Treeview)
- dodawanie pozycji
- usuwanie zaznaczonej pozycji
- odświeżanie listy

Wymagania
- Raspberry Pi 4 z Raspberry Pi OS
- Python 3.x
- Tkinter (python3-tk) i sqlite3
  - sudo apt update
  - sudo apt install -y python3-tk sqlite3

Uruchomienie
1) Sklonuj/kopiuj repozytorium na RPi.
2) Upewnij się, że istnieją puste pliki ui/__init__.py i logic/__init__.py (dla importów).
3) Uruchom:
   - python3 main.py

Struktura projektu
```
project_root/
├── data/
│   └── inventory.db        # baza SQLite (tworzona automatycznie)
├── ui/
│   ├── __init__.py
│   └── views.py            # GUI (Tkinter: formularz + tabela)
├── logic/
│   ├── __init__.py
│   └── db.py               # obsługa SQLite
├── main.py                 # punkt startowy aplikacji
└── README.md
```

Dostosowanie
- Kategorie w Combobox: edytuj listę self.categories w ui/views.py (np. ["Narzędzia", "Meble", "RTV", "AGD", "IT", "Inne"]).
- Lokalizacja bazy: zmień ścieżkę w main.py (domyślnie data/inventory.db).