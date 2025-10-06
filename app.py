from __future__ import annotations
import asyncio
import concurrent.futures
import json
import time
import signal
import sys
import atexit
from typing import List, Dict

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
try:
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not available - running in serverless mode")

# Import with fallbacks for serverless environment
try:
    from config import CBD_BBOX, DEFAULT_INPUT_CSV, DEFAULT_RESULTS_CSV, RESULT_CACHE_TTL, TELSTRA_WAIT_SECONDS, HEADLESS, IS_CLOUD
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Config not available: {e}")
    CONFIG_AVAILABLE = False
    # Default values
    CBD_BBOX = (-37.8265, 144.9475, -37.8060, 144.9835)
    DEFAULT_INPUT_CSV = "input.csv"
    DEFAULT_RESULTS_CSV = "results.csv"
    RESULT_CACHE_TTL = 7 * 24 * 3600
    TELSTRA_WAIT_SECONDS = 25
    HEADLESS = True
    IS_CLOUD = True

try:
    from geo import geocode_address, fetch_nearby_addresses, fetch_addresses_in_bbox
    GEO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Geo module not available: {e}")
    GEO_AVAILABLE = False
    # Fallback functions
    def geocode_address(addr: str):
        return None, None, "serverless_mode"
    def fetch_nearby_addresses(lat, lon, radius=100):
        return []
    def fetch_addresses_in_bbox(bbox):
        return []

try:
    from indexes import ResultsIndex, InputIndex
    INDEXES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Indexes module not available: {e}")
    INDEXES_AVAILABLE = False
    # Fallback classes with proper structure
    class ResultsIndex:
        def __init__(self):
            self.ready = False
            self.addr = []
            self.lat = []
            self.lon = []
            self.x = []
            self.y = []
            self.elig = []
            self.status = []
            self.latency = []
            self.checked_at = []
        
        def load(self, filename):
            """Load data from CSV file if it exists."""
            try:
                import csv
                import os
                print(f"Attempting to load {filename}")
                print(f"Current working directory: {os.getcwd()}")
                print(f"File exists: {os.path.exists(filename)}")
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get('address'):
                                self.addr.append(row['address'])
                                self.lat.append(float(row.get('lat', 0)))
                                self.lon.append(float(row.get('lon', 0)))
                                # Handle different column names in your CSV
                                eligible_val = row.get('eligible', 'false')
                                if isinstance(eligible_val, str):
                                    self.elig.append(eligible_val.lower() == 'true')
                                else:
                                    self.elig.append(bool(eligible_val))
                                
                                # Use status_text if available, otherwise status
                                status_val = row.get('status_text') or row.get('status', 'unknown')
                                self.status.append(status_val)
                                
                                # Use checked_at column
                                self.checked_at.append(row.get('checked_at', ''))
                    self.ready = True
                    print(f"Loaded {len(self.addr)} addresses from {filename}")
                else:
                    print(f"File {filename} not found - using sample dataset for demo")
                    # Add some sample data for demonstration
                    self.addr = [
                        "123 Collins Street, Melbourne VIC 3000",
                        "456 Bourke Street, Melbourne VIC 3000", 
                        "789 Swanston Street, Melbourne VIC 3000"
                    ]
                    self.lat = [-37.8136, -37.8146, -37.8156]
                    self.lon = [144.9631, 144.9641, 144.9651]
                    self.elig = [True, False, True]
                    self.status = ["eligible", "not_eligible", "eligible"]
                    self.checked_at = ["2024-01-15", "2024-01-15", "2024-01-15"]
                    self.ready = True
                    print(f"Using {len(self.addr)} sample addresses for demo")
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                self.ready = False
        
        def save(self, filename):
            """Save data to CSV file."""
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['address', 'lat', 'lon', 'eligible', 'status', 'checked_at'])
                    for i in range(len(self.addr)):
                        writer.writerow([
                            self.addr[i],
                            self.lat[i],
                            self.lon[i],
                            self.elig[i],
                            self.status[i],
                            self.checked_at[i]
                        ])
                print(f"Saved {len(self.addr)} addresses to {filename}")
            except Exception as e:
                print(f"Error saving {filename}: {e}")
        
        def nearest_eligible(self, lat, lon, n=10):
            """Find nearest eligible addresses."""
            if not self.ready or len(self.addr) == 0:
                return []
            
            # Simple distance calculation (not optimized)
            distances = []
            for i in range(len(self.addr)):
                if self.elig[i]:  # Only eligible addresses
                    # Simple distance calculation
                    lat_diff = lat - self.lat[i]
                    lon_diff = lon - self.lon[i]
                    distance = (lat_diff**2 + lon_diff**2)**0.5
                    distances.append((distance, i))
            
            # Sort by distance and return top n
            distances.sort()
            return [self.addr[i] for _, i in distances[:n]]
    
    class InputIndex:
        def __init__(self):
            self.ready = False
            self.addr = []
            self.lat = []
            self.lon = []
        
        def load(self, filename):
            """Load input addresses from CSV file if it exists."""
            try:
                import csv
                import os
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get('address'):
                                self.addr.append(row['address'])
                                self.lat.append(float(row.get('lat', 0)))
                                self.lon.append(float(row.get('lon', 0)))
                    self.ready = True
                    print(f"Loaded {len(self.addr)} input addresses from {filename}")
                else:
                    print(f"File {filename} not found - using empty dataset")
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                self.ready = False
        
        def save(self, filename):
            """Save input addresses to CSV file."""
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['address', 'lat', 'lon'])
                    for i in range(len(self.addr)):
                        writer.writerow([self.addr[i], self.lat[i], self.lon[i]])
                print(f"Saved {len(self.addr)} input addresses to {filename}")
            except Exception as e:
                print(f"Error saving {filename}: {e}")

try:
    from telstra5g import Telstra5GChecker
    TELSTRA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Telstra5G module not available: {e}")
    TELSTRA_AVAILABLE = False
    # Fallback class
    class Telstra5GChecker:
        def __init__(self, *args, **kwargs):
            pass
        def check(self, addr: str):
            return addr, False, "serverless_mode"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global cleanup variables
_active_websockets = set()
_active_executors = set()
_driver_path = None
checker = None

def cleanup_resources():
    """Clean up all resources on shutdown."""
    print("Cleaning up resources...")
    
    # Close all active WebSocket connections
    for ws in _active_websockets.copy():
        try:
            if not ws.client_state.disconnected:
                asyncio.create_task(ws.close())
        except Exception as e:
            print(f"Error closing WebSocket: {e}")
    
    # Shutdown all thread pools
    for executor in _active_executors.copy():
        try:
            executor.shutdown(wait=False)
        except Exception as e:
            print(f"Error shutting down executor: {e}")
    
    # Clear Selenium checker
    global checker
    if checker:
        try:
            checker.clear_cache()
            checker = None
        except Exception as e:
            print(f"Error clearing Selenium checker: {e}")
    
    print("Cleanup completed")

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    print(f"\nReceived signal {signum}. Shutting down gracefully...")
    cleanup_resources()
    sys.exit(0)

# Register cleanup handlers
atexit.register(cleanup_resources)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Driver & checker
def get_checker():
    """Lazy load the checker to avoid startup issues."""
    global checker, _driver_path
    
    # Disable Selenium in cloud/serverless environments
    if IS_CLOUD or not SELENIUM_AVAILABLE or not TELSTRA_AVAILABLE:
        print("Selenium/Telstra checker disabled in serverless environment")
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
    import os
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "environment": "serverless" if IS_CLOUD else "local",
        "selenium_available": SELENIUM_AVAILABLE,
        "modules_available": {
            "config": CONFIG_AVAILABLE,
            "geo": GEO_AVAILABLE,
            "indexes": INDEXES_AVAILABLE,
            "telstra": TELSTRA_AVAILABLE
        },
        "files_available": {
            "results_csv": os.path.exists("results.csv"),
            "result10_csv": os.path.exists("result10.csv"),
            "working_directory": os.getcwd(),
            "files_in_dir": [f for f in os.listdir('.') if f.endswith('.csv')]
        },
        "database_status": {
            "results_ready": results_index.ready,
            "results_count": len(results_index.addr) if results_index.ready else 0
        }
    }


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
        },
        "active_connections": {
            "websockets": len(_active_websockets),
            "executors": len(_active_executors)
        }
    }


@app.get("/test-database")
async def test_database():
    """Test endpoint to verify database loading."""
    import os
    try:
        # Try to reload the database
        results_index.load(DEFAULT_RESULTS_CSV)
        
        return {
            "success": True,
            "message": "Database loaded successfully",
            "file_exists": os.path.exists(DEFAULT_RESULTS_CSV),
            "file_size": os.path.getsize(DEFAULT_RESULTS_CSV) if os.path.exists(DEFAULT_RESULTS_CSV) else 0,
            "database_ready": results_index.ready,
            "address_count": len(results_index.addr),
            "eligible_count": sum(results_index.elig) if results_index.ready else 0,
            "sample_addresses": results_index.addr[:5] if results_index.ready and len(results_index.addr) > 0 else []
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "file_exists": os.path.exists(DEFAULT_RESULTS_CSV),
            "working_directory": os.getcwd(),
            "files_in_dir": os.listdir('.') if os.path.exists('.') else []
        }


@app.post("/cleanup")
async def manual_cleanup():
    """Manually trigger cleanup of resources."""
    cleanup_resources()
    return {"status": "cleanup_completed", "message": "All resources cleaned up"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})


@app.websocket("/ws")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    _active_websockets.add(websocket)
    
    try:
        data = await websocket.receive_json()
        address = data["address"]
        n = int(data["n"])  # cap on nearby addresses to check
        workers = int(data["workers"])  # thread pool size
        radius = int(data.get("radius", 1000))

        try:
            lat, lon = geocode_address(address)
        except Exception as e:
            await websocket.send_text(json.dumps({"error": f"Geocode failed: {e}"}))
            return

        addresses = fetch_nearby_addresses(lat, lon, radius=radius)
        addresses.insert(0, address)
        addresses = addresses[:n]

        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        _active_executors.add(executor)
        
        try:
            with executor:
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
        finally:
            _active_executors.discard(executor)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        _active_websockets.discard(websocket)
        await websocket.close()


@app.websocket("/ws_fromdata")
async def websocket_fromdata(websocket: WebSocket):
    await websocket.accept()
    _active_websockets.add(websocket)
    
    try:
        payload = await websocket.receive_json()
        address = payload.get("address", "")
        n = int(payload.get("n", 10))

        try:
            tgt_lat, tgt_lon = geocode_address(address)
        except Exception as e:
            await websocket.send_text(json.dumps({"error": f"Geocode failed: {e}"}))
            return

        if not results_index.ready:
            results_index.load(DEFAULT_RESULTS_CSV)

        nearest = results_index.nearest_eligible(tgt_lat, tgt_lon, n)
        if not nearest:
            await websocket.send_text(json.dumps({"error": "No eligible addresses found nearby in results.csv"}))
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
    except Exception as e:
        print(f"WebSocket fromdata error: {e}")
    finally:
        _active_websockets.discard(websocket)
        await websocket.close()


@app.websocket("/ws_map")
async def websocket_map(websocket: WebSocket):
    """WebSocket endpoint for live map checking within a bounding box."""
    await websocket.accept()
    _active_websockets.add(websocket)
    
    try:
        data = await websocket.receive_json()
        bbox = data["bbox"]  # [south, west, north, east]
        workers = int(data["workers"])
        max_points = int(data["max_points"])

        try:
            # Fetch addresses in the bounding box
            addresses = fetch_addresses_in_bbox(bbox, limit=max_points)
            
            if not addresses:
                await websocket.send_text(json.dumps({"error": "No addresses found in the specified area"}))
                return

            # Check 5G availability for each address
            loop = asyncio.get_event_loop()
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
            _active_executors.add(executor)
            
            try:
                with executor:
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
            finally:
                _active_executors.discard(executor)

        except Exception as e:
            await websocket.send_text(json.dumps({"error": f"Map check failed: {e}"}))
    except Exception as e:
        print(f"WebSocket map error: {e}")
    finally:
        _active_websockets.discard(websocket)
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
    _active_websockets.add(websocket)
    
    try:
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
    except Exception as e:
        print(f"WebSocket map_data error: {e}")
    finally:
        _active_websockets.discard(websocket)
        await websocket.close()
