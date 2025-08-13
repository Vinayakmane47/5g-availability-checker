#!/usr/bin/env python3
"""
Cloud-Optimized Bulk 5G Availability Checker

This version is optimized for Railway deployment with conservative settings
to avoid resource limits and rate limiting issues.
"""

import json
import time
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging

from telstra5g import Telstra5GChecker
from geo import fetch_addresses_in_bbox
from config import CBD_BBOX, DEFAULT_RESULTS_CSV, TELSTRA_WAIT_SECONDS, HEADLESS, IS_CLOUD
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CloudBulkChecker:
    """Cloud-optimized bulk checker for Railway deployment."""
    
    def __init__(self, max_workers: int = 1, address_limit: int = 100, batch_size: int = 20):
        """
        Initialize cloud bulk checker with conservative settings.
        
        Args:
            max_workers: Number of concurrent workers (1 for cloud)
            address_limit: Maximum addresses to check
            batch_size: Addresses per batch (smaller for cloud)
        """
        self.max_workers = max_workers
        self.address_limit = address_limit
        self.batch_size = batch_size
        
        # Initialize checker with cloud-optimized settings
        driver_path = ChromeDriverManager().install()
        self.checker = Telstra5GChecker(
            driver_path=driver_path,
            cache_ttl_seconds=24 * 3600,  # 24 hours cache
            wait_seconds=TELSTRA_WAIT_SECONDS,
            headless=HEADLESS
        )
        
        # Load existing results
        self.existing_addresses = self._load_existing_addresses()
        self.failed_addresses = self._load_failed_addresses()
        
        logger.info(f"Cloud Bulk Checker initialized:")
        logger.info(f"  Workers: {max_workers}")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Address limit: {address_limit}")
        logger.info(f"  Existing addresses: {len(self.existing_addresses)}")
        logger.info(f"  Failed addresses: {len(self.failed_addresses)}")
    
    def _load_existing_addresses(self) -> set:
        """Load addresses already checked from results.csv."""
        existing = set()
        try:
            with open(DEFAULT_RESULTS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing.add(row['address'].lower().strip())
            logger.info(f"Loaded {len(existing)} existing addresses")
        except FileNotFoundError:
            logger.info("No existing results.csv found")
        except Exception as e:
            logger.error(f"Error loading existing addresses: {e}")
        return existing
    
    def _load_failed_addresses(self) -> List[str]:
        """Load previously failed addresses."""
        try:
            with open('failed_addresses_cloud.json', 'r') as f:
                failed = json.load(f)
            logger.info(f"Loaded {len(failed)} failed addresses")
            return failed
        except FileNotFoundError:
            logger.info("No failed addresses file found")
            return []
        except Exception as e:
            logger.error(f"Error loading failed addresses: {e}")
            return []
    
    def _save_failed_addresses(self, failed: List[str]):
        """Save failed addresses for later retry."""
        try:
            with open('failed_addresses_cloud.json', 'w') as f:
                json.dump(failed, f, indent=2)
            logger.info(f"Saved {len(failed)} failed addresses")
        except Exception as e:
            logger.error(f"Error saving failed addresses: {e}")
    
    def _check_single_address_with_retry(self, address: str, max_retries: int = 2) -> tuple:
        """
        Check a single address with retry logic optimized for cloud.
        
        Args:
            address: Address to check
            max_retries: Maximum retry attempts
            
        Returns:
            Tuple of (address, available, status)
        """
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Checking {address} (attempt {attempt + 1})")
                available, status = self.checker.check(address)
                logger.info(f"SUCCESS: {address} - 5G: {'Available' if available else 'Unavailable'}")
                return address, available, status
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {address}: {e}")
                if attempt < max_retries:
                    # Exponential backoff: 30s, 60s
                    delay = 30 * (2 ** attempt)
                    logger.info(f"Retrying {address} in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"FAILED: {address} after {max_retries + 1} attempts")
                    return address, False, f"error: {str(e)}"
    
    def _process_batch(self, addresses: List[str]) -> List[tuple]:
        """Process a batch of addresses with cloud-optimized concurrency."""
        results = []
        failed_in_batch = []
        
        logger.info(f"Processing batch of {len(addresses)} addresses")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all addresses
            future_to_address = {
                executor.submit(self._check_single_address_with_retry, addr): addr 
                for addr in addresses
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_address):
                address = future_to_address[future]
                try:
                    result = future.result()
                    if result[2].startswith('error:'):
                        failed_in_batch.append(address)
                    else:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Exception for {address}: {e}")
                    failed_in_batch.append(address)
        
        # Add failed addresses to retry list
        if failed_in_batch:
            self.failed_addresses.extend(failed_in_batch)
            self._save_failed_addresses(self.failed_addresses)
        
        logger.info(f"Batch completed: {len(results)} success, {len(failed_in_batch)} failed")
        return results
    
    def _save_results(self, results: List[tuple]):
        """Save results to CSV file."""
        try:
            # Load existing results
            existing_results = []
            try:
                with open(DEFAULT_RESULTS_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_results = list(reader)
            except FileNotFoundError:
                pass
            
            # Add new results
            for addr, available, status in results:
                existing_results.append({
                    'address': addr,
                    'eligible': 'True' if available else 'False',
                    'status_text': status,
                    'latency_sec': '0',  # Cloud doesn't track latency
                    'checked_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'lat': '0',  # Would need geocoding
                    'lon': '0',
                    'method': 'cloud_bulk'
                })
            
            # Save all results
            with open(DEFAULT_RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['address', 'eligible', 'status_text', 'latency_sec', 
                             'checked_at', 'lat', 'lon', 'method']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_results)
            
            logger.info(f"Saved {len(results)} new results to {DEFAULT_RESULTS_CSV}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def run(self, retry_failed: bool = False):
        """
        Run the cloud bulk checker.
        
        Args:
            retry_failed: Whether to retry previously failed addresses
        """
        logger.info("Starting Cloud Bulk Checker...")
        start_time = time.time()
        
        # Get addresses to check
        if retry_failed and self.failed_addresses:
            addresses_to_check = self.failed_addresses[:self.address_limit]
            logger.info(f"Retrying {len(addresses_to_check)} failed addresses")
        else:
            # Get new addresses from CBD
            try:
                all_addresses = fetch_addresses_in_bbox(CBD_BBOX, limit=self.address_limit * 2)
                addresses_to_check = [addr['addr'] for addr in all_addresses]
                logger.info(f"Fetched {len(addresses_to_check)} addresses from CBD")
            except Exception as e:
                logger.error(f"Error fetching addresses: {e}")
                return
        
        # Filter out already checked addresses
        if not retry_failed:
            addresses_to_check = [
                addr for addr in addresses_to_check 
                if addr.lower().strip() not in self.existing_addresses
            ]
        
        addresses_to_check = addresses_to_check[:self.address_limit]
        logger.info(f"Will check {len(addresses_to_check)} addresses")
        
        if not addresses_to_check:
            logger.info("No addresses to check")
            return
        
        # Process in batches
        all_results = []
        total_batches = (len(addresses_to_check) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(addresses_to_check), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch = addresses_to_check[i:i + self.batch_size]
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} addresses)")
            
            # Process batch
            batch_results = self._process_batch(batch)
            all_results.extend(batch_results)
            
            # Delay between batches (longer for cloud)
            if batch_num < total_batches:
                delay = 60 if IS_CLOUD else 30  # 60s delay for cloud
                logger.info(f"Waiting {delay} seconds before next batch...")
                time.sleep(delay)
        
        # Save results
        if all_results:
            self._save_results(all_results)
        
        # Summary
        elapsed_time = time.time() - start_time
        successful = len([r for r in all_results if not r[2].startswith('error:')])
        available = len([r for r in all_results if r[1] and not r[2].startswith('error:')])
        
        logger.info("Cloud Bulk Checker completed!")
        logger.info(f"  Total time: {elapsed_time/60:.1f} minutes")
        logger.info(f"  Addresses checked: {len(addresses_to_check)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {len(addresses_to_check) - successful}")
        logger.info(f"  5G Available: {available}")
        logger.info(f"  Success rate: {(successful/len(addresses_to_check)*100):.1f}%")

def main():
    """Main function for cloud bulk checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cloud-optimized 5G availability bulk checker')
    parser.add_argument('--workers', type=int, default=1, help='Number of workers (default: 1 for cloud)')
    parser.add_argument('--limit', type=int, default=100, help='Maximum addresses to check (default: 100)')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size (default: 20 for cloud)')
    parser.add_argument('--retry-failed', action='store_true', help='Retry previously failed addresses')
    
    args = parser.parse_args()
    
    # Create and run checker
    checker = CloudBulkChecker(
        max_workers=args.workers,
        address_limit=args.limit,
        batch_size=args.batch_size
    )
    
    checker.run(retry_failed=args.retry_failed)

if __name__ == "__main__":
    main() 