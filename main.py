from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import asyncio
import json
import paho.mqtt.client as mqtt

APP_ID = "bes-test"
DEVICE_ID = "my-new-device"
API_KEY = "NNSXS.73VZYON46SRCG6QTCQE3SFXPGR5R67XWPC422I.Z5VQ2FLCP3MVJMKKTTNPBR46BXJA7FMTL3HNJJ5SUHVU36OISLPQ"

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

websockets = []
send_queue = asyncio.Queue()
main_loop = asyncio.get_event_loop()  # <-- globalny event loop

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("🟢 Nowy WebSocket połączenie")
    await websocket.accept()
    websockets.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # keep connection open
    except Exception as e:
        print(f"🔴 WebSocket rozłączony: {e}")
    finally:
        websockets.remove(websocket)

async def websocket_broadcaster():
    while True:
        temp, timestamp = await send_queue.get()
        message = json.dumps({"temperature": temp, "timestamp": timestamp})
        # Usuwamy WebSockety zamknięte
        disconnected = []
        for ws in websockets:
            try:
                await ws.send_text(message)
            except Exception as e:
                print(f"🔴 Błąd wysyłania do klienta WebSocket: {e}")
                disconnected.append(ws)
        for ws in disconnected:
            websockets.remove(ws)

def on_connect(client, userdata, flags, rc):
    topic = f"v3/{APP_ID}@ttn/devices/{DEVICE_ID}/up"
    print(f"🔌 Połączono z MQTT, subskrypcja na temat: {topic}")
    client.subscribe(topic)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    try:
        temp = payload["uplink_message"]["decoded_payload"]["temperature"]
        timestamp = payload["received_at"]
        # Przekazujemy do event loopa w bezpieczny sposób
        main_loop.call_soon_threadsafe(send_queue.put_nowait, (temp, timestamp))
        print(f"📥 Otrzymano temperaturę: {temp} o czasie: {timestamp}")
    except Exception as e:
        print("❌ Błąd MQTT:", e)

def start_mqtt():
    client = mqtt.Client()
    client.username_pw_set(f"{APP_ID}@ttn", API_KEY)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("eu1.cloud.thethings.network", 1883, 60)
    client.loop_start()

start_mqtt()

# Uruchamiamy task nadawczy WebSocketów
asyncio.create_task(websocket_broadcaster())
