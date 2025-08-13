import os

CBD_BBOX = (-37.8265, 144.9475, -37.8060, 144.9835)  # south, west, north, east
DEFAULT_INPUT_CSV = "input.csv"
DEFAULT_RESULTS_CSV = "results.csv"
RESULT_CACHE_TTL = 7 * 24 * 3600
TELSTRA_WAIT_SECONDS = 25
HEADLESS = True  # Always headless in cloud
USER_AGENT = "5G-Checker-App"

# Melbourne projection anchor
LAT0 = -37.8136
LON0 = 144.9631

# Cloud deployment settings
IS_CLOUD = os.getenv('RAILWAY_ENVIRONMENT', False) or os.getenv('PORT', False)
CHROME_OPTIONS = [
    '--headless',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-web-security',
    '--disable-features=VizDisplayCompositor',
    '--remote-debugging-port=9222'
]