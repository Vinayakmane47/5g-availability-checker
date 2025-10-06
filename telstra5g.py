from __future__ import annotations
import time
from typing import Tuple, Dict
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    # Create dummy classes for type hints
    class webdriver:
        class Chrome:
            pass
    class Options:
        pass
    class Service:
        def __init__(self, *args, **kwargs):
            pass
    class WebDriverWait:
        def __init__(self, *args, **kwargs):
            pass
    class By:
        ID = "id"
        CSS_SELECTOR = "css selector"
    class EC:
        @staticmethod
        def presence_of_element_located(*args):
            pass
        @staticmethod
        def presence_of_all_elements_located(*args):
            pass

from config import CHROME_OPTIONS, IS_CLOUD


class Telstra5GChecker:
    TELSTRA_URL = "https://www.telstra.com.au/internet/5g-home-internet"

    def __init__(self, driver_path: str, cache_ttl_seconds: int, wait_seconds: int, headless: bool) -> None:
        self.driver_path = driver_path
        self.cache_ttl = cache_ttl_seconds
        self.wait_seconds = wait_seconds
        self.headless = headless
        # addr_lower -> (available: bool, status: str, ts: float)
        self._cache: Dict[str, tuple] = {}

    # Cache helpers
    def _cache_get(self, addr: str):
        key = addr.lower().strip()
        hit = self._cache.get(key)
        if not hit:
            return None
        available, status, ts = hit
        if time.time() - ts > self.cache_ttl:
            self._cache.pop(key, None)
            return None
        return available, status

    def _cache_put(self, addr: str, available: bool, status: str):
        key = addr.lower().strip()
        self._cache[key] = (available, status, time.time())

    def clear_cache(self):
        self._cache.clear()

    # Selenium
    def _make_chrome_options(self) -> Options:
        o = Options()
        
        # Use cloud-optimized options if in cloud environment
        if IS_CLOUD:
            for option in CHROME_OPTIONS:
                o.add_argument(option)
        else:
            # Local development options
            if self.headless:
                o.add_argument("--headless=new")
            o.add_argument("--no-sandbox")
            o.add_argument("--disable-dev-shm-usage")
            o.add_argument("--disable-gpu")
            o.add_argument("--disable-setuid-sandbox")
            o.add_argument("--disable-blink-features=AutomationControlled")
            o.add_argument("--blink-settings=imagesEnabled=false")
        
        return o

    def open_driver(self) -> tuple[webdriver.Chrome, WebDriverWait]:
        service = Service(self.driver_path)
        driver = webdriver.Chrome(service=service, options=self._make_chrome_options())
        wait = WebDriverWait(driver, self.wait_seconds)
        return driver, wait

    # Core DOM flow
    def _eligible_on_loaded_page(self, driver: webdriver.Chrome, wait: WebDriverWait, addr: str) -> tuple[bool, str]:
        input_box = wait.until(EC.presence_of_element_located((By.ID, "tcom-sq-main-input")))
        input_box.clear()
        input_box.send_keys(addr)
        time.sleep(1)
        input_box.send_keys("\b\b")
        time.sleep(1)
        input_box.send_keys(addr[-2:])
        time.sleep(2)

        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#adddress-autocomplete-results li.address-option")))
            suggestions = driver.find_elements(By.CSS_SELECTOR, "#adddress-autocomplete-results li.address-option")
            if suggestions:
                driver.execute_script("arguments[0].click();", suggestions[0])
                time.sleep(3)
            else:
                return False, "no_suggestions"
        except Exception:
            return False, "suggestion_click_failed"

        try:
            result_header = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.tcom-sq__result__header__title")))
            header_text = (result_header.text or "").strip()
            is_available = "eligible for 5G Home Internet" in header_text
        except Exception:
            return False, "header_not_found"

        try:
            try:
                reset_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-sq-result-header] button[data-tcom-sq-reset]")))
            except Exception:
                reset_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.tcom-sq__error__button button[data-tcom-sq-reset]")))
            driver.execute_script("arguments[0].scrollIntoView(true);", reset_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", reset_button)
            wait.until(EC.visibility_of_element_located((By.ID, "tcom-sq-main-input")))
            time.sleep(1)
        except Exception:
            pass

        return is_available, header_text

    # Public APIs
    def check(self, addr: str) -> tuple[str, bool, str]:
        # Fallback for serverless environments
        if not SELENIUM_AVAILABLE:
            return self._check_fallback(addr)
            
        hit = self._cache_get(addr)
        if hit is not None:
            available, status = hit
            return addr, available, f"cache:{status}"
        driver, wait = self.open_driver()
        try:
            driver.get(self.TELSTRA_URL)
            wait.until(EC.presence_of_element_located((By.ID, "tcom-sq-main-input")))
            available, status = self._eligible_on_loaded_page(driver, wait, addr)
            self._cache_put(addr, available, status)
            return addr, available, status
        except Exception as e:
            return addr, False, f"error:{type(e).__name__}"
        finally:
            driver.quit()
    
    def _check_fallback(self, addr: str) -> tuple[str, bool, str]:
        """Fallback method for serverless environments without Selenium."""
        # Return mock data - in a real implementation, you might want to:
        # 1. Use a different API if available
        # 2. Return cached data from a database
        # 3. Return a "service unavailable" status
        return addr, False, "serverless_mode"

    def check_with_existing_session(self, driver: webdriver.Chrome, wait: WebDriverWait, addr: str) -> tuple[str, bool, str]:
        # Fallback for serverless environments
        if not SELENIUM_AVAILABLE:
            return self._check_fallback(addr)
            
        try:
            if "telstra.com.au" not in (driver.current_url or ""):
                driver.get(self.TELSTRA_URL)
            wait.until(EC.presence_of_element_located((By.ID, "tcom-sq-main-input")))
        except Exception:
            driver.get(self.TELSTRA_URL)
            wait.until(EC.presence_of_element_located((By.ID, "tcom-sq-main-input")))

        hit = self._cache_get(addr)
        if hit is not None:
            available, status = hit
            return addr, available, f"cache:{status}"
        try:
            available, status = self._eligible_on_loaded_page(driver, wait, addr)
            self._cache_put(addr, available, status)
            return addr, available, status
        except Exception as e:
            return addr, False, f"error:{type(e).__name__}"