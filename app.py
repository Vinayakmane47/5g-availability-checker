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

from config import CBD_BBOX, DEFAULT_INPUT_CSV, DEFAULT_RESULTS_CSV, RESULT_CACHE_TTL, TELSTRA_WAIT_SECONDS, HEADLESS
from geo import geocode_address, fetch_nearby_addresses, fetch_addresses_in_bbox
from indexes import ResultsIndex, InputIndex
from telstra5g import Telstra5GChecker

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Driver & checker
_driver_path = None
checker = None

def get_checker():
    """Lazy load the checker to avoid startup issues."""
    global checker, _driver_path
    
    # Completely disable Selenium in Railway environment
    if IS_CLOUD:
        print("Selenium disabled in Railway environment")
        return None
    
    if checker is None:
        try:
            _driver_path = ChromeDriverManager().install()
            checker = Telstra5GChecker(
                driver_path=_driver_path,
                cache_ttl_seconds=RESULT_CACHE_TTL,
                wait_seconds=TELSTRA_WAIT_SECONDS,
                headless=HEADLESS,
            )
        except Exception as e:
            print(f"Warning: Could not initialize Selenium checker: {e}")
            checker = None
    return checker

# Indexes
results_index = ResultsIndex()
results_index.load(DEFAULT_RESULTS_CSV)

input_index = InputIndex()
input_index.load(DEFAULT_INPUT_CSV)


@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.get("/health")
async def health_check():
    """Simple health check endpoint for Railway."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/status")
async def app_status():
    """Show app status and available features."""
    return {
        "status": "running",
        "environment": "railway" if IS_CLOUD else "local",
        "features": {
            "web_interface": True,
            "database_access": True,
            "map_visualization": True,
            "real_time_checking": not IS_CLOUD,  # Disabled in Railway
            "bulk_checking": not IS_CLOUD,  # Disabled in Railway
        },
        "data": {
            "total_addresses": len(results_index.addr) if results_index.ready else 0,
            "available_addresses": sum(results_index.elig) if results_index.ready else 0,
        }
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})


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
            checker_instance = get_checker()
            if checker_instance:
                futures.append(loop.run_in_executor(executor, checker_instance.check, addr))
            else:
                await websocket.send_text(json.dumps({
                    "addr": addr,
                    "available": False,
                    "status": "error: Real-time checking not available in Railway. Use 'Check from Database' instead.",
                    "time": 0,
                }))

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


@app.websocket("/ws_map")
async def websocket_map(websocket: WebSocket):
    """WebSocket endpoint for live map checking within a bounding box."""
    await websocket.accept()
    data = await websocket.receive_json()
    bbox = data["bbox"]  # [south, west, north, east]
    workers = int(data["workers"])
    max_points = int(data["max_points"])

    try:
        # Fetch addresses in the bounding box
        addresses = fetch_addresses_in_bbox(bbox, limit=max_points)
        
        if not addresses:
            await websocket.send_text(json.dumps({"error": "No addresses found in the specified area"}))
            await websocket.close()
            return

        # Check 5G availability for each address
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for addr_data in addresses:
                checker_instance = get_checker()
                if checker_instance:
                    futures.append(loop.run_in_executor(executor, checker_instance.check, addr_data["addr"]))
                else:
                    await websocket.send_text(json.dumps({
                        "addr": addr_data["addr"],
                        "available": False,
                        "status": "error: Real-time checking not available in Railway. Use 'Check from Database' instead.",
                        "lat": addr_data["lat"],
                        "lon": addr_data["lon"],
                    }))

            for fut in asyncio.as_completed(futures):
                addr, available, status = await fut
                # Find the original address data
                addr_data = next((a for a in addresses if a["addr"] == addr), None)
                if addr_data:
                    await websocket.send_text(json.dumps({
                        "addr": addr,
                        "available": available,
                        "status": status,
                        "lat": addr_data["lat"],
                        "lon": addr_data["lon"],
                    }))

    except Exception as e:
        await websocket.send_text(json.dumps({"error": f"Map check failed: {e}"}))
    
    await websocket.close()


@app.get("/api/map-data")
async def get_map_data(max_points: int = 1000):
    """REST API endpoint for getting map data."""
    try:
        # Reload the results index to get latest data
        if not results_index.ready:
            results_index.load(DEFAULT_RESULTS_CSV)
        
        # Get all addresses from results.csv
        if not results_index.ready or len(results_index.addr) == 0:
            return {"error": "No data available in results.csv"}
        
        # Get all addresses with their data
        addresses = []
        for i in range(min(len(results_index.addr), max_points)):
            addresses.append({
                "addr": results_index.addr[i],
                "lat": float(results_index.lat[i]),
                "lon": float(results_index.lon[i]),
                "available": bool(results_index.elig[i]),
                "status": results_index.status[i],
                "checked_at": results_index.checked_at[i]
            })
        
        return {
            "success": True,
            "count": len(addresses),
            "data": addresses
        }

    except Exception as e:
        return {"error": f"Map data load failed: {e}"}


@app.websocket("/ws_map_data")
async def websocket_map_data(websocket: WebSocket):
    """WebSocket endpoint for displaying existing data on the map."""
    await websocket.accept()
    data = await websocket.receive_json()
    file_type = data.get("file", "results.csv")
    max_points = int(data.get("max_points", 1000))

    try:
        # Reload the results index to get latest data
        if not results_index.ready:
            results_index.load(DEFAULT_RESULTS_CSV)
        
        # Get all addresses from results.csv (simplified without lock)
        if not results_index.ready or len(results_index.addr) == 0:
            await websocket.send_text(json.dumps({"error": "No data available in results.csv"}))
            await websocket.close()
            return
        
        # Get all addresses with their data (simplified)
        addresses = []
        for i in range(min(len(results_index.addr), max_points)):
            addresses.append({
                "addr": results_index.addr[i],
                "lat": float(results_index.lat[i]),
                "lon": float(results_index.lon[i]),
                "available": bool(results_index.elig[i]),  # Convert numpy.bool_ to Python bool
                "status": results_index.status[i],
                "checked_at": results_index.checked_at[i]
            })
        
        # Send each address to the map
        for addr_data in addresses:
            await websocket.send_text(json.dumps({
                "addr": addr_data["addr"],
                "available": addr_data["available"],
                "status": addr_data["status"],
                "lat": addr_data["lat"],
                "lon": addr_data["lon"],
                "checked_at": addr_data["checked_at"],
            }))

    except Exception as e:
        await websocket.send_text(json.dumps({"error": f"Map data load failed: {e}"}))
    
    await websocket.close()
