from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pathlib import Path
from logic.db import Database
from logic.export import export_inventory_to_csv
import asyncio
import json

# --- konfiguracja aplikacji ---
app = FastAPI(title="Inventory WiFi Server")

# --- zarządzanie połączeniami WebSocket ---
clients: list[WebSocket] = []

async def broadcast(message: str):
    """Wysyła tekst JSON do wszystkich aktywnych klientów."""
    stale_clients = []
    for ws in clients.copy():
        try:
            await ws.send_text(message)
        except Exception:
            stale_clients.append(ws)
    for ws in stale_clients:
        if ws in clients:
            clients.remove(ws)

# --- inicjalizacja bazy ---
data_dir = Path(__file__).resolve().parent / "data"
data_dir.mkdir(exist_ok=True)
db_path = data_dir / "inventory.db"
db = Database(db_path)

# --- model danych ---
class Item(BaseModel):
    id: int | None = None
    name: str
    category: str
    purchase_date: str
    serial_number: str
    description: str

# --- główne endpointy REST API ---
@app.get("/items")
def list_items():
    return db.list_items()

@app.post("/items")
async def add_item(item: Item):
    db.add_item(
        item.name,
        item.category,
        item.purchase_date,
        item.serial_number,
        item.description,
    )
    # powiadom klientów o zmianie
    await broadcast(json.dumps({"event": "reload"}))
    return {"status": "ok"}

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    db.update_item(
        item_id,
        item.name,
        item.category,
        item.purchase_date,
        item.serial_number,
        item.description,
    )
    await broadcast(json.dumps({"event": "reload"}))
    return {"status": "ok"}

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    db.delete_item(item_id)
    await broadcast(json.dumps({"event": "reload"}))
    return {"status": "ok"}

# --- specjalne endpointy ---
@app.post("/notify_reload")
async def notify_reload():
    """Wywoływane przez aplikację Tkinter (local HTTP),
    żeby rozgłosić zmianę po stronie RPi."""
    await broadcast(json.dumps({"event": "reload"}))
    return {"status": "ok"}

@app.get("/export")
def export_csv():
    path = data_dir / "export.csv"
    export_inventory_to_csv(db.list_items(), path)
    return {"status": "ok", "path": str(path)}

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "pong"}

# --- WebSocket /ws ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    print(f"📡  Połączono klienta WebSocket ({len(clients)} aktywnych)")

    try:
        while True:
            # klient może wysyłać drobne ping-i, które ignorujemy
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in clients:
            clients.remove(websocket)
        print(f"❌  Klient rozłączony ({len(clients)} pozostało)")

# --- uruchamianie serwera ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("wifi_server:app", host="0.0.0.0", port=8000, reload=False)