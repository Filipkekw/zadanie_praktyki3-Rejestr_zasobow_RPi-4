import os
from pathlib import Path

from dotenv import load_dotenv

# katalog główny projektu (jeden poziom nad logic/)
BASE_DIR = Path(__file__).resolve().parent.parent

# wczytaj plik .env jeśli istnieje
load_dotenv(BASE_DIR / ".env")

# odczyt wartości z ENV z sensownymi domyślnymi fallbackami
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))