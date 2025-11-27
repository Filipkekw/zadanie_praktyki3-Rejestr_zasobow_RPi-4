# Rejestr zasobów - serwer RPi (PyQt5 + FastAPI)

Lekka aplikacja do rejestru zasobów na Raspberry Pi 4 (PyQt5 + SQLite). 
Interfejs w PyQt5 z bazą danych w pliku ```data/inventory.db``` oraz API HTTP/WebSocket (FastAPI) dla klienta mobilnego.

## Wymagania 

- Raspberry Pi 4 z Raspberry Pi OS
- Python 3.11+
- zainstalowane pakiety:
```bash
sudo apt update
sudo apt install python3 python3-pip sqlite3 -y
pip install fastapi uvicorn websockets requests
```    
- w przypadku pojawienia się błędu o zablokowaniu instalacji z powodu błędu o treści "externally-managed-environment" trzeba dodać --break-system-packages ale:
    - UWAGA! Użycie tego łączy się z ryzykiem uszkodzenia instalacji pythona lub całego systemu operacyjnego!
    -  Można obejść ten problem, lecz to będzie wymagało użycia wirtualnego środowiska (venv) i aplikacja będzie dostępna tylko w nim.

## Struktura projektu
```
Rejestr_zasobow_RPi-4-main/
├── data/
│   └── inventory.db        # baza SQLite (tworzona automatycznie)
├── ui/
│   └── views.py            # GUI (PyQt5: formularz + tabela)
├── logic/
│   ├── export.py           # obsługa eksportu danych do pliku .csv
│   ├── ws_client.py        # synchronizacja danych pomiędzy aplikacją tkinter a flutter
│   └── db.py               # obsługa SQLite
├── main.py                 # punkt startowy aplikacji
├── wifi_server.py          # obsługa serwera http
└── README.md
```
## Uruchamianie
1. Uruchom serwer API na RPi:
```bash
python3 wifi_server.py
```
Serwer będzie dostępny pod adresem: ```http://<IP_RPi>:8000```

2. Uruchom aplikację GUI PyQt5:
```bash
python3 main.py
```
3. Klient Flutter musi być w tej samej sieci Wi-Fi i mieć ustawiony adres IP Raspberry Pi w pięciu miejscach w kodzie w plikach aplikacji klienta (szczegóły w pliku README.md aplikacji klienta).

## Funkcje
- Dodawanie, edycja i usuwanie zasobów (Tkinter + Flutter).
- Wspólna baza SQLite (data/inventory.db)
- Sortowanie, filtrowanie i wyszukiwanie zasobów
- Synchronizacja w czasie rzeczywistym (Websocket) między RPi a klientem.
- Eksport zasobów do pliku .csv.