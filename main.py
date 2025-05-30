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
API_KEY = "NNSXS.73VZYON46SRCG6QTCQE3SFXPGR5R67KXWPC422I.Z5VQ2FLCP3MVJMKKTTNPBR46BXJA7FMTL3HNJJ5SUHVU36OISLPQ"

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

websockets = []
send_queue = asyncio.Queue()  # kolejka do przesyłania danych między MQTT a websocketami


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket accepted")
    websockets.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # utrzymuj połączenie przy życiu
    except:
        print("❌ WebSocket disconnected")
    finally:
        if websocket in websockets:
            websockets.remove(websocket)


async def websocket_broadcaster():
    while True:
        temp, timestamp = await send_queue.get()
        message = json.dumps({"temperature": temp, "timestamp": timestamp})
        to_remove = []
        for ws in websockets:
            try:
                await ws.send_text(message)
            except:
                to_remove.append(ws)
        for ws in to_remove:
            if ws in websockets:
                websockets.remove(ws)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(websocket_broadcaster())
    start_mqtt()


def on_connect(client, userdata, flags, rc):
    topic = f"v3/{APP_ID}@ttn/devices/{DEVICE_ID}/up"
    client.subscribe(topic)


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    try:
        temp = payload["uplink_message"]["decoded_payload"]["temperature"]
        timestamp = payload["received_at"]
        # zamiast asyncio.run(), używamy create_task na kolejce
        asyncio.create_task(send_queue.put((temp, timestamp)))
    except Exception as e:
        print("❌ Błąd w on_message:", e)


def start_mqtt():
    client = mqtt.Client()
    client.username_pw_set(f"{APP_ID}@ttn", API_KEY)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("eu1.cloud.thethings.network", 1883, 60)
    client.loop_start()
