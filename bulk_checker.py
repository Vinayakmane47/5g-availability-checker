#!/usr/bin/env python3
"""
Bulk 5G Availability Checker for Melbourne CBD

This script generates addresses in Melbourne CBD and checks their 5G availability
using the Telstra website. Results are saved to results.csv for use by the web app.
Enhanced with retry mechanisms and batch processing to handle loading errors.
"""

import csv
import time
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys
import os

from selenium.common.exceptions import ElementNotInteractableException, TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from config import CBD_BBOX, DEFAULT_RESULTS_CSV, RESULT_CACHE_TTL, TELSTRA_WAIT_SECONDS, HEADLESS
from geo import fetch_addresses_in_bbox, geocode_address
from telstra5g import Telstra5GChecker
from models import EligibilityRow


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_checker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BulkChecker:
    def __init__(self, max_workers: int = 3, address_limit: int = 1000, batch_size: int = 50):
        """
        Initialize the bulk checker.
        
        Args:
            max_workers: Number of concurrent threads for checking addresses
            address_limit: Maximum number of addresses to check
            batch_size: Number of addresses to process in each batch
        """
        self.max_workers = max_workers
        self.address_limit = address_limit
        self.batch_size = batch_size
        
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
        logger.info(f"Loaded {len(self.existing_addresses)} existing addresses from results.csv")
        
        # Load failed addresses for retry
        self.failed_addresses = self._load_failed_addresses()
        logger.info(f"Loaded {len(self.failed_addresses)} failed addresses for retry")
    
    def _load_existing_addresses(self) -> set:
        """Load existing addresses from results.csv to avoid duplicates."""
        existing = set()
        try:
            with open(DEFAULT_RESULTS_CSV, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    addr = (row.get('address') or '').strip()
                    if addr:
                        existing.add(addr.lower())
        except FileNotFoundError:
            logger.info("No existing results.csv found, starting fresh")
        except Exception as e:
            logger.warning(f"Error loading existing results: {e}")
        
        return existing
    
    def _load_failed_addresses(self) -> List[Dict[str, Any]]:
        """Load failed addresses from failed_addresses.json for retry."""
        failed_file = 'failed_addresses.json'
        try:
            if os.path.exists(failed_file):
                with open(failed_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading failed addresses: {e}")
        return []
    
    def _save_failed_addresses(self, failed_addresses: List[Dict[str, Any]]) -> None:
        """Save failed addresses to failed_addresses.json for later retry."""
        try:
            with open('failed_addresses.json', 'w', encoding='utf-8') as f:
                json.dump(failed_addresses, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving failed addresses: {e}")
    
    def _save_result(self, result: Dict[str, Any]) -> None:
        """Save a single result to results.csv."""
        try:
            # Check if file exists to determine if we need to write headers
            file_exists = True
            try:
                with open(DEFAULT_RESULTS_CSV, 'r', newline='', encoding='utf-8') as f:
                    pass
            except FileNotFoundError:
                file_exists = False
            
            with open(DEFAULT_RESULTS_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'address', 'eligible', 'status_text', 'latency_sec', 
                    'checked_at', 'lat', 'lon', 'method'
                ])
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(result)
                
        except Exception as e:
            logger.error(f"Error saving result for {result.get('address', 'unknown')}: {e}")
    
    def _check_single_address_with_retry(self, address_data: Dict[str, Any], max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Check 5G availability for a single address with retry mechanism."""
        address = address_data['addr']
        lat = address_data['lat']
        lon = address_data['lon']
        
        # Skip if already checked
        if address.lower() in self.existing_addresses:
            logger.debug(f"Skipping {address} - already checked")
            return None
        
        logger.info(f"Checking: {address}")
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                # Add delay between retries (exponential backoff)
                if attempt > 0:
                    delay = 2 ** attempt  # 2, 4, 8 seconds
                    logger.info(f"Retry {attempt + 1}/{max_retries} for {address} after {delay}s delay")
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
                    'method': 'bulk'
                }
                
                # Save immediately
                self._save_result(result)
                
                # Add to existing set to avoid duplicates
                self.existing_addresses.add(address.lower())
                
                logger.info(f"+ {address}: {'Available' if available else 'Not available'} ({latency}s)")
                return result
                
            except (ElementNotInteractableException, TimeoutException, WebDriverException) as e:
                error_msg = f"Loading error on attempt {attempt + 1}/{max_retries} for {address}: {type(e).__name__}"
                if attempt < max_retries - 1:
                    logger.warning(error_msg)
                else:
                    logger.error(f"Final failure for {address}: {e}")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error checking {address}: {e}")
                return None
        
        return None
    
    def _process_batch(self, addresses: List[Dict[str, Any]]) -> tuple[int, int, List[Dict[str, Any]]]:
        """Process a batch of addresses and return success/failure counts and failed addresses."""
        successful = 0
        failed = 0
        failed_addresses = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks in the batch
            future_to_address = {
                executor.submit(self._check_single_address_with_retry, addr): addr 
                for addr in addresses
            }
            
            # Process completed tasks
            for future in as_completed(future_to_address):
                address_data = future_to_address[future]
                try:
                    result = future.result()
                    if result:
                        successful += 1
                    else:
                        failed += 1
                        failed_addresses.append(address_data)
                except Exception as e:
                    logger.error(f"Task failed for {address_data['addr']}: {e}")
                    failed += 1
                    failed_addresses.append(address_data)
        
        return successful, failed, failed_addresses
    
    def fetch_cbd_addresses(self) -> List[Dict[str, Any]]:
        """Fetch addresses from Melbourne CBD using OpenStreetMap data."""
        logger.info("Fetching addresses from Melbourne CBD...")
        
        try:
            addresses = fetch_addresses_in_bbox(CBD_BBOX, limit=self.address_limit)
            logger.info(f"Found {len(addresses)} addresses in Melbourne CBD")
            return addresses
        except Exception as e:
            logger.error(f"Error fetching addresses: {e}")
            return []
    
    def run(self) -> None:
        """Run the bulk checking process with batch processing."""
        logger.info("Starting bulk 5G availability check for Melbourne CBD")
        logger.info(f"Using {self.max_workers} workers, limit: {self.address_limit} addresses, batch size: {self.batch_size}")
        
        # Combine new addresses with failed addresses for retry
        new_addresses = self.fetch_cbd_addresses()
        if not new_addresses:
            logger.error("No addresses found to check")
            return
        
        # Filter out already checked addresses
        addresses_to_check = [
            addr for addr in new_addresses + self.failed_addresses
            if addr['addr'].lower() not in self.existing_addresses
        ]
        
        if not addresses_to_check:
            logger.info("All addresses have already been checked")
            return
        
        logger.info(f"Checking {len(addresses_to_check)} addresses (including {len(self.failed_addresses)} retries)")
        
        # Process addresses in batches
        total_successful = 0
        total_failed = 0
        all_failed_addresses = []
        
        for i in range(0, len(addresses_to_check), self.batch_size):
            batch = addresses_to_check[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(addresses_to_check) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} addresses)")
            
            successful, failed, failed_addresses = self._process_batch(batch)
            total_successful += successful
            total_failed += failed
            all_failed_addresses.extend(failed_addresses)
            
            logger.info(f"Batch {batch_num} completed: {successful} successful, {failed} failed")
            
            # Add delay between batches to avoid overwhelming the system
            if i + self.batch_size < len(addresses_to_check):
                logger.info("Waiting 30 seconds before next batch...")
                time.sleep(30)
        
        # Save failed addresses for later retry
        if all_failed_addresses:
            self._save_failed_addresses(all_failed_addresses)
            logger.info(f"Saved {len(all_failed_addresses)} failed addresses to failed_addresses.json for retry")
        
        logger.info(f"Bulk check completed: {total_successful} successful, {total_failed} failed")
        logger.info(f"Results saved to {DEFAULT_RESULTS_CSV}")
        
        if all_failed_addresses:
            logger.info("You can retry failed addresses by running: python bulk_checker.py --retry-failed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Bulk 5G availability checker for Melbourne CBD')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Number of concurrent workers (default: 3)')
    parser.add_argument('--limit', type=int, default=1000,
                       help='Maximum number of addresses to check (default: 1000)')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of addresses to process in each batch (default: 50)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be checked without actually checking')
    parser.add_argument('--retry-failed', action='store_true',
                       help='Only retry addresses that failed in previous runs')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No actual checking will be performed")
        checker = BulkChecker(max_workers=1, address_limit=args.limit, batch_size=args.batch_size)
        addresses = checker.fetch_cbd_addresses()
        logger.info(f"Would check {len(addresses)} addresses")
        for i, addr in enumerate(addresses[:10]):  # Show first 10
            logger.info(f"  {i+1}. {addr['addr']}")
        if len(addresses) > 10:
            logger.info(f"  ... and {len(addresses) - 10} more")
        return
    
    try:
        checker = BulkChecker(max_workers=args.workers, address_limit=args.limit, batch_size=args.batch_size)
        
        if args.retry_failed:
            logger.info("RETRY MODE - Only retrying failed addresses")
            # Clear the failed addresses list since we're retrying them
            checker.failed_addresses = []
        
        checker.run()
    except KeyboardInterrupt:
        logger.info("Bulk check interrupted by user")
    except Exception as e:
        logger.error(f"Bulk check failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 