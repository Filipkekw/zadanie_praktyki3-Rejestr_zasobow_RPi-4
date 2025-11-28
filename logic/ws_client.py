import asyncio
import threading
import json
import websockets
from .config import SERVER_HOST, SERVER_PORT

class WSListener:

    def __init__(self, on_reload_callback, uri: str | None = None):
        if uri is None:
            uri = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws"
        self.uri = uri
        self.on_reload_callback = on_reload_callback  # funkcja np. refresh()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._listen())
        finally:
            self.loop.close()

    async def _listen(self):
        while True:
            try:
                async with websockets.connect(self.uri) as ws:
                    print("Aplikacja RPi połączona z WS serwera.")
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if data.get("event") == "reload":
                            print("Odebrano RELOAD z serwera.")
                            self.on_reload_callback()
            except Exception as e:
                print("Błąd WS / zerwane połączenie:", e)
                await asyncio.sleep(5)  # spróbuj ponownie po 5 s

    def start(self):
        self.thread.start()

    def stop(self):
        self.running = False
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass