from __future__ import annotations
import asyncio
import concurrent.futures
import json
import time
from typing import List, Dict

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from webdriver_manager.chrome import ChromeDriverManager

from config import DEFAULT_INPUT_CSV, DEFAULT_RESULTS_CSV, RESULT_CACHE_TTL, TELSTRA_WAIT_SECONDS, HEADLESS
from geo import geocode_address, fetch_nearby_addresses
from indexes import ResultsIndex, InputIndex
from telstra5g import Telstra5GChecker

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Driver & checker
_driver_path = ChromeDriverManager().install()
checker = Telstra5GChecker(
    driver_path=_driver_path,
    cache_ttl_seconds=RESULT_CACHE_TTL,
    wait_seconds=TELSTRA_WAIT_SECONDS,
    headless=HEADLESS,
)

# Indexes
results_index = ResultsIndex()
results_index.load(DEFAULT_RESULTS_CSV)

input_index = InputIndex()
input_index.load(DEFAULT_INPUT_CSV)


@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.websocket("/ws")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive_json()
    address = data["address"]
    n = int(data["n"])  # cap on nearby addresses to check
    workers = int(data["workers"])  # thread pool size
    radius = int(data.get("radius", 1000))

    try:
        lat, lon = geocode_address(address)
    except Exception as e:
        await websocket.send_text(json.dumps({"error": f"Geocode failed: {e}"}))
        await websocket.close()
        return

    addresses = fetch_nearby_addresses(lat, lon, radius=radius)
    addresses.insert(0, address)
    addresses = addresses[:n]

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        start_times: Dict[str, float] = {}
        for addr in addresses:
            start_times[addr] = time.time()
            futures.append(loop.run_in_executor(executor, checker.check, addr))

        for fut in asyncio.as_completed(futures):
            a, available, status = await fut
            elapsed = round(time.time() - start_times.get(a, time.time()), 2)
            await websocket.send_text(json.dumps({
                "addr": a,
                "available": available,
                "status": status,
                "time": elapsed,
            }))
    await websocket.close()


@app.websocket("/ws_fromdata")
async def websocket_fromdata(websocket: WebSocket):
    await websocket.accept()
    payload = await websocket.receive_json()
    address = payload.get("address", "")
    n = int(payload.get("n", 10))

    try:
        tgt_lat, tgt_lon = geocode_address(address)
    except Exception as e:
        await websocket.send_text(json.dumps({"error": f"Geocode failed: {e}"}))
        await websocket.close()
        return

    if not results_index.ready:
        results_index.load(DEFAULT_RESULTS_CSV)

    nearest = results_index.nearest_eligible(tgt_lat, tgt_lon, n)
    if not nearest:
        await websocket.send_text(json.dumps({"error": "No eligible addresses found nearby in results.csv"}))
        await websocket.close()
        return

    for item in nearest:
        await websocket.send_text(json.dumps({
            "addr": item["addr"],
            "available": True,
            "status": item["status_text"],
            "lat": item["lat"],
            "lon": item["lon"],
            "checked_at": item["checked_at"],
            "latency_sec": item["latency_sec"],
            "distance_km": round(float(item["distance_km"]), 3),
            "source": "results.csv",
        }))
    await websocket.close()
