#!/usr/bin/env python3
"""
Test Bulk Checker - Small Scale Test

This script runs the bulk checker with just 10 addresses to test
the functionality before running on the main database.
"""

import sys
import os
import csv
import time
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium.common.exceptions import ElementNotInteractableException, TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from config import CBD_BBOX, DEFAULT_RESULTS_CSV, RESULT_CACHE_TTL, TELSTRA_WAIT_SECONDS, HEADLESS
from geo import fetch_addresses_in_bbox, geocode_address
from telstra5g import Telstra5GChecker
from models import EligibilityRow

class TestBulkChecker:
    """Test version of BulkChecker that saves to a custom file."""
    
    def __init__(self, max_workers: int = 1, address_limit: int = 10, batch_size: int = 5, output_file: str = 'result10.csv'):
        """
        Initialize the test bulk checker.
        
        Args:
            max_workers: Number of concurrent threads for checking addresses
            address_limit: Maximum number of addresses to check
            batch_size: Number of addresses to process in each batch
            output_file: Custom output file for results
        """
        self.max_workers = max_workers
        self.address_limit = address_limit
        self.batch_size = batch_size
        self.output_file = output_file
        
        # Initialize Telstra checker
        driver_path = ChromeDriverManager().install()
        self.checker = Telstra5GChecker(
            driver_path=driver_path,
            cache_ttl_seconds=RESULT_CACHE_TTL,
            wait_seconds=TELSTRA_WAIT_SECONDS,
            headless=HEADLESS,
        )
        
        # Load existing results to avoid duplicates
        self.existing_addresses = self._load_existing_addresses()
        print(f"Loaded {len(self.existing_addresses)} existing addresses from {self.output_file}")
        
        # Load failed addresses for retry
        self.failed_addresses = self._load_failed_addresses()
        print(f"Loaded {len(self.failed_addresses)} failed addresses for retry")
    
    def _load_existing_addresses(self) -> set:
        """Load existing addresses from output file to avoid duplicates."""
        existing = set()
        try:
            with open(self.output_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    addr = (row.get('address') or '').strip()
                    if addr:
                        existing.add(addr.lower())
        except FileNotFoundError:
            print(f"No existing {self.output_file} found, starting fresh")
        except Exception as e:
            print(f"Warning: Error loading existing results: {e}")
        
        return existing
    
    def _load_failed_addresses(self) -> List[Dict[str, Any]]:
        """Load failed addresses from failed_addresses.json for retry."""
        failed_file = 'failed_addresses_test.json'
        try:
            if os.path.exists(failed_file):
                with open(failed_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading failed addresses: {e}")
        return []
    
    def _save_failed_addresses(self, failed_addresses: List[Dict[str, Any]]) -> None:
        """Save failed addresses to failed_addresses_test.json."""
        try:
            with open('failed_addresses_test.json', 'w', encoding='utf-8') as f:
                json.dump(failed_addresses, f, indent=2)
        except Exception as e:
            print(f"Error saving failed addresses: {e}")
    
    def _save_result(self, result: Dict[str, Any]) -> None:
        """Save a single result to the custom output file."""
        try:
            # Check if file exists to determine if we need to write headers
            file_exists = True
            try:
                with open(self.output_file, 'r', newline='', encoding='utf-8') as f:
                    pass
            except FileNotFoundError:
                file_exists = False
            
            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'address', 'eligible', 'status_text', 'latency_sec', 
                    'checked_at', 'lat', 'lon', 'method'
                ])
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(result)
                
        except Exception as e:
            print(f"Error saving result for {result.get('address', 'unknown')}: {e}")
    
    def _check_single_address_with_retry(self, address_data: Dict[str, Any], max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Check 5G availability for a single address with retry mechanism."""
        address = address_data['addr']
        lat = address_data['lat']
        lon = address_data['lon']
        
        # Skip if already checked
        if address.lower() in self.existing_addresses:
            print(f"Skipping {address} - already checked")
            return None
        
        print(f"Checking: {address}")
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                # Add delay between retries (exponential backoff)
                if attempt > 0:
                    delay = 2 ** attempt  # 2, 4, 8 seconds
                    print(f"Retry {attempt + 1}/{max_retries} for {address} after {delay}s delay")
                    time.sleep(delay)
                
                # Check 5G availability
                checked_addr, available, status = self.checker.check(address)
                
                # Calculate latency
                latency = round(time.time() - start_time, 3)
                
                # Create result
                result = {
                    'address': address,
                    'eligible': available,
                    'status_text': status if available else '',
                    'latency_sec': latency,
                    'checked_at': datetime.utcnow().isoformat() + '+00:00',
                    'lat': lat,
                    'lon': lon,
                    'method': 'test_bulk'
                }
                
                # Save immediately
                self._save_result(result)
                
                # Add to existing set to avoid duplicates
                self.existing_addresses.add(address.lower())
                
                print(f"+ {address}: {'Available' if available else 'Not available'} ({latency}s)")
                return result
                
            except (ElementNotInteractableException, TimeoutException, WebDriverException) as e:
                error_msg = f"Loading error on attempt {attempt + 1}/{max_retries} for {address}: {type(e).__name__}"
                if attempt < max_retries - 1:
                    print(f"Warning: {error_msg}")
                else:
                    print(f"Final failure for {address}: {e}")
                    return None
            except Exception as e:
                print(f"Unexpected error checking {address}: {e}")
                return None
        
        return None
    
    def run(self):
        """Run the bulk checking process."""
        print(f"Starting bulk check with {self.address_limit} addresses...")
        
        # Fetch addresses in Melbourne CBD
        addresses = fetch_addresses_in_bbox(CBD_BBOX, limit=self.address_limit)
        
        if not addresses:
            print("No addresses found in the specified area")
            return
        
        print(f"Found {len(addresses)} addresses to check")
        
        # Process addresses in batches
        total_checked = 0
        total_successful = 0
        total_failed = 0
        failed_addresses = []
        
        for i in range(0, len(addresses), self.batch_size):
            batch = addresses[i:i + self.batch_size]
            print(f"\nProcessing batch {i//self.batch_size + 1}/{(len(addresses) + self.batch_size - 1)//self.batch_size}")
            
            batch_successful = 0
            batch_failed = 0
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks in the batch
                future_to_address = {
                    executor.submit(self._check_single_address_with_retry, addr_data): addr_data
                    for addr_data in batch
                }
                
                # Process completed tasks
                for future in as_completed(future_to_address):
                    addr_data = future_to_address[future]
                    try:
                        result = future.result()
                        if result:
                            batch_successful += 1
                            total_successful += 1
                        else:
                            batch_failed += 1
                            total_failed += 1
                            failed_addresses.append(addr_data)
                    except Exception as e:
                        print(f"Error processing {addr_data['addr']}: {e}")
                        batch_failed += 1
                        total_failed += 1
                        failed_addresses.append(addr_data)
            
            total_checked += len(batch)
            print(f"Batch completed: {batch_successful} successful, {batch_failed} failed")
            
            # Add delay between batches
            if i + self.batch_size < len(addresses):
                print("Waiting 10 seconds before next batch...")
                time.sleep(10)
        
        # Save failed addresses
        if failed_addresses:
            self._save_failed_addresses(failed_addresses)
            print(f"\nSaved {len(failed_addresses)} failed addresses to failed_addresses_test.json")
        
        print(f"\n=== BULK CHECK COMPLETED ===")
        print(f"Total checked: {total_checked}")
        print(f"Successful: {total_successful}")
        print(f"Failed: {total_failed}")
        print(f"Results saved to: {self.output_file}")

def main():
    """Run a small test with 10 addresses."""
    print("=== TEST BULK CHECKER ===")
    print("Running with 10 addresses to test functionality...")
    print()
    
    # Create a test checker with minimal settings
    test_checker = TestBulkChecker(
        max_workers=1,      # Single worker for testing
        address_limit=10,   # Only 10 addresses
        batch_size=5,       # Small batch size
        output_file='result10.csv'  # Test output file
    )
    
    print("Test Settings:")
    print(f"  Workers: 1")
    print(f"  Address limit: 10")
    print(f"  Batch size: 5")
    print(f"  Output file: result10.csv")
    print()
    
    # Confirm before starting
    response = input("Start test with 10 addresses? (y/N): ")
    if response.lower() != 'y':
        print("Test cancelled.")
        return
    
    print("Starting test...")
    
    try:
        # Run the test
        test_checker.run()
        
        print()
        print("=== TEST COMPLETED ===")
        print("Check result10.csv for the test results.")
        
        # Show summary if file exists
        if os.path.exists('result10.csv'):
            with open('result10.csv', 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                print(f"Results saved: {len(rows)} addresses checked")
                
                if rows:
                    available = sum(1 for row in rows if row.get('eligible', '').lower() == 'true')
                    print(f"5G Available: {available}")
                    print(f"5G Unavailable: {len(rows) - available}")
        
        print()
        print("If the test was successful, you can now run:")
        print("  ./run_bulk_checker.sh")
        print("to expand your main database.")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError during test: {e}")
        print("Please check the error and fix before running on main database.")

if __name__ == "__main__":
    main() 