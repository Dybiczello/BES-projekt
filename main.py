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

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websockets.append(websocket)

    # Fetch historical data
    history = fetch_historical_data()
    print(f"Fetched {len(history)} history items")

    # Wyślij jako JEDEN obiekt
    await websocket.send_text(json.dumps({
        "type": "history",
        "data": history
    }))

    try:
        while True:
            await asyncio.sleep(1)
    except:
        websockets.remove(websocket)


def on_connect(client, userdata, flags, rc):
    topic = f"v3/{APP_ID}@ttn/devices/{DEVICE_ID}/up"
    client.subscribe(topic)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    try:
        temp = payload["uplink_message"]["decoded_payload"]["temperature"]
        timestamp = payload["received_at"]
        asyncio.run(send_to_clients(temp, timestamp))
    except:
        pass

async def send_to_clients(temp, timestamp):
    message = json.dumps({"temperature": temp, "timestamp": timestamp})
    for ws in websockets:
        await ws.send_text(message)

def start_mqtt():
    client = mqtt.Client()
    client.username_pw_set(f"{APP_ID}@ttn", API_KEY)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("eu1.cloud.thethings.network", 1883, 60)
    client.loop_start()

start_mqtt()

def fetch_historical_data():
    url = f"https://eu1.cloud.thethings.network/api/v3/as/applications/{APP_ID}/packages/storage/uplink_message"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }
    params = {
        "last": "12h",
    }

    response = requests.get(url, headers=headers, params=params)
    messages = []

    try:
        # Rozbij tekst na linie (każda linia to osobny JSON)
        lines = response.text.strip().split('\n')
        for line in lines:
            data = json.loads(line)
            result = data.get("result")
            if result:
                temp = result["uplink_message"]["decoded_payload"]["temperature"]
                timestamp = result["received_at"]
                messages.append({"temperature": temp, "timestamp": timestamp})

    except Exception as e:
        print("Failed to parse historical data:", e)

    return messages
