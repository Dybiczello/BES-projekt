import asyncio
import json
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import paho.mqtt.client as mqtt

APP_ID = "bes-test"
DEVICE_ID = "my-new-device"
API_KEY = "NNSXS.73VZYON46SRCG6QTCQE3SFXPGR5R67XWPC422I.Z5VQ2FLCP3MVJMKKTTNPBR46BXJA7FMTL3HNJJ5SUHVU36OISLPQ"

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Lista aktywnych WebSocketów
active_websockets = set()

# Asynchroniczna kolejka do komunikacji między wątkiem MQTT a pętlą async
send_queue: asyncio.Queue = asyncio.Queue()

# Główna pętla zdarzeń (asyncio)
main_loop = asyncio.get_event_loop()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    print("🟢 Nowy WebSocket połączenie")
    try:
        while True:
            # Możemy czekać na wiadomości z klienta, ale nie są potrzebne
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
        print("🔴 WebSocket rozłączony")

# MQTT callbacki
def on_connect(client, userdata, flags, rc):
    topic = f"v3/{APP_ID}@ttn/devices/{DEVICE_ID}/up"
    client.subscribe(topic)
    print(f"🔌 Połączono z MQTT, subskrypcja na temat: {topic}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        temp = payload["uplink_message"]["decoded_payload"]["temperature"]
        timestamp = payload["received_at"]
        print(f"📥 Otrzymano dane MQTT: temp={temp}, time={timestamp}")
        # Umieść dane w kolejce w sposób bezpieczny dla wątku
        main_loop.call_soon_threadsafe(send_queue.put_nowait, (temp, timestamp))
    except Exception as e:
        print("❌ Błąd w on_message:", e)

def start_mqtt():
    client = mqtt.Client()
    client.username_pw_set(f"{APP_ID}@ttn", API_KEY)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("eu1.cloud.thethings.network", 1883, 60)
    client.loop_start()

async def websocket_broadcaster():
    print("⚙️ Uruchamiam websocket_broadcaster task")
    while True:
        temp, timestamp = await send_queue.get()
        message = json.dumps({"temperature": temp, "timestamp": timestamp})
        # Wyślij wiadomość do wszystkich aktywnych WebSocketów
        websockets_to_remove = set()
        for ws in active_websockets:
            try:
                await ws.send_text(message)
            except Exception as e:
                print(f"❌ Błąd podczas wysyłania do websocket: {e}")
                websockets_to_remove.add(ws)
        # Usuń uszkodzone połączenia
        for ws in websockets_to_remove:
            active_websockets.remove(ws)

# Start MQTT w osobnym wątku, żeby nie blokował pętli asyncio
threading.Thread(target=start_mqtt, daemon=True).start()

# Uruchom task websocket_broadcaster po starcie aplikacji
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(websocket_broadcaster())
