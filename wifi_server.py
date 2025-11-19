from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pathlib import Path
from logic.db import Database
from logic.export import export_inventory_to_csv
import asyncio
import json

app = FastAPI(title="Inventory WiFi Server")

clients: list[WebSocket] = []

async def broadcast(message: str):
	for ws in clients:
		try:
			await ws.send_text(message)
		except Exception:
			clients.remove(ws)

# --- inicjalizacja bazy ---
data_dir = Path(__file__).resolve().parent / "data"
data_dir.mkdir(exist_ok=True)
db = Database(data_dir / "inventory.db")

# --- modele danych ---
class Item(BaseModel):
    id: int | None = None
    name: str
    category: str
    purchase_date: str
    serial_number: str
    description: str


# --- endpointy API ---
@app.get("/items")
def list_items():
    return db.list_items()

@app.post("/items")
async def add_item(item: Item):
    db.add_item(item.name, item.category, item.purchase_date, item.serial_number, item.description)
    await broadcast(json.dumps({"event": "reload"}))
    return {"status": "ok"}

@app.post("/notify_reload")
async def notify_reload():
    await broadcast(json.dumps({"event": "reload"}))
    return {"status": "ok"}

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    db.update_item(item_id, **item.dict(exclude={"id"}))
    return {"status": "ok"}

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    db.delete_item(item_id)
    return {"status": "ok"}

@app.get("/export")
def export_csv():
    path = data_dir / "export.csv"
    export_inventory_to_csv(db.list_items(), path)
    return {"status": "ok", "path": str(path)}

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "pong"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
	await websocket.accept()
	clients.append(websocket)
	print("Polaczono klienta Websocket")
	
	try:
		while True:
			_ = await websocket.receive_text()
	except WebSocketDisconnect:
		print("Klient rozlaczony")
		clients.remove(websocket)

# --- startowanie serwera ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
