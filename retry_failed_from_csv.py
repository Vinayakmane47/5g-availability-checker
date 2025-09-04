#!/usr/bin/env python3
"""
Retry Failed Addresses from results.csv

This script reads the existing results.csv file and retries addresses that failed
with ElementNotInteractableException, TimeoutException, and other errors from
previous runs. It uses the improved code to get better results.
"""

import csv
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium.common.exceptions import ElementNotInteractableException, TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from config import RESULT_CACHE_TTL, TELSTRA_WAIT_SECONDS, HEADLESS, DEFAULT_RESULTS_CSV
from telstra5g import Telstra5GChecker

class RetryFailedAddresses:
    """Retry addresses that failed in previous runs."""
    
    def __init__(self, max_workers: int = 2, batch_size: int = 20):
        """
        Initialize the retry checker.
        
        Args:
            max_workers: Number of concurrent threads
            batch_size: Number of addresses to process in each batch
        """
        self.max_workers = max_workers
        self.batch_size = batch_size
        
        # Initialize Telstra checker
        driver_path = ChromeDriverManager().install()
        self.checker = Telstra5GChecker(
            driver_path=driver_path,
            cache_ttl_seconds=RESULT_CACHE_TTL,
            wait_seconds=TELSTRA_WAIT_SECONDS,
            headless=HEADLESS,
        )
        
        # Load existing results
        self.existing_results = self._load_existing_results()
        print(f"Loaded {len(self.existing_results)} existing results from results.csv")
    
    def _load_existing_results(self) -> List[Dict[str, Any]]:
        """Load existing results from results.csv."""
        results = []
        try:
            with open(DEFAULT_RESULTS_CSV, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append(row)
        except FileNotFoundError:
            print("No existing results.csv found")
        except Exception as e:
            print(f"Error loading existing results: {e}")
        
        return results
    
    def _identify_failed_addresses(self) -> Dict[str, List[Dict[str, Any]]]:
        """Identify addresses that failed in previous runs."""
        failed_by_error = defaultdict(list)
        
        for row in self.existing_results:
            status = row.get('status_text', '')
            eligible = row.get('eligible', '').lower() == 'true'
            
            # Only retry addresses that failed (not eligible)
            if not eligible:
                if 'ElementNotInteractableException' in status:
                    failed_by_error['ElementNotInteractableException'].append(row)
                elif 'TimeoutException' in status:
                    failed_by_error['TimeoutException'].append(row)
                elif 'NoSuchWindowException' in status:
                    failed_by_error['NoSuchWindowException'].append(row)
                elif 'header_not_found' in status:
                    failed_by_error['header_not_found'].append(row)
                elif 'timeout' in status:
                    failed_by_error['timeout'].append(row)
                else:
                    failed_by_error['other'].append(row)
        
        return dict(failed_by_error)
    
    def _check_single_address_with_retry(self, address_data: Dict[str, Any], max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Check 5G availability for a single address with retry mechanism."""
        address = address_data['address']
        lat = float(address_data.get('lat', 0))
        lon = float(address_data.get('lon', 0))
        
        print(f"Retrying: {address}")
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                # Add delay between retries (exponential backoff)
                if attempt > 0:
                    delay = 2 ** attempt  # 2, 4, 8 seconds
                    print(f"  Retry {attempt + 1}/{max_retries} for {address} after {delay}s delay")
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
                    'method': 'retry_bulk'
                }
                
                print(f"  + {address}: {'Available' if available else 'Not available'} ({latency}s)")
                return result
                
            except (ElementNotInteractableException, TimeoutException, WebDriverException) as e:
                error_msg = f"Loading error on attempt {attempt + 1}/{max_retries} for {address}: {type(e).__name__}"
                if attempt < max_retries - 1:
                    print(f"  Warning: {error_msg}")
                else:
                    print(f"  Final failure for {address}: {e}")
                    return None
            except Exception as e:
                print(f"  Unexpected error checking {address}: {e}")
                return None
        
        return None
    
    def _update_results_csv(self, new_results: List[Dict[str, Any]]):
        """Update results.csv with new results, replacing old failed entries."""
        # Create a map of address to new result
        new_results_map = {result['address'].lower(): result for result in new_results}
        
        # Update existing results
        updated_results = []
        for row in self.existing_results:
            addr_lower = row['address'].lower()
            if addr_lower in new_results_map:
                # Replace with new result
                updated_results.append(new_results_map[addr_lower])
                print(f"Updated: {row['address']}")
            else:
                # Keep existing result
                updated_results.append(row)
        
        # Save updated results
        try:
            with open(DEFAULT_RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
                if updated_results:
                    writer = csv.DictWriter(f, fieldnames=updated_results[0].keys())
                    writer.writeheader()
                    writer.writerows(updated_results)
            
            print(f"Updated results.csv with {len(new_results)} new results")
        except Exception as e:
            print(f"Error updating results.csv: {e}")
    
    def _remove_duplicates(self):
        """Remove duplicate addresses from results.csv, keeping the best result for each."""
        print("=== REMOVING DUPLICATE ADDRESSES ===")
        print()
        
        # Group addresses by normalized address (lowercase)
        address_groups = defaultdict(list)
        for row in self.existing_results:
            addr_lower = row['address'].lower().strip()
            address_groups[addr_lower].append(row)
        
        # Find duplicates
        duplicates = {addr: rows for addr, rows in address_groups.items() if len(rows) > 1}
        
        if not duplicates:
            print("No duplicate addresses found!")
            return
        
        print(f"Found {len(duplicates)} addresses with duplicates:")
        total_duplicates = sum(len(rows) - 1 for rows in duplicates.values())
        print(f"Total duplicate entries to remove: {total_duplicates}")
        print()
        
        # Show some examples
        print("Examples of duplicate addresses:")
        for i, (addr, rows) in enumerate(list(duplicates.items())[:5]):
            print(f"  {addr}: {len(rows)} entries")
            for j, row in enumerate(rows[:3]):  # Show first 3 entries
                eligible = row.get('eligible', '').lower() == 'true'
                status = row.get('status_text', '')[:50]  # Truncate long status
                print(f"    {j+1}. Eligible: {eligible}, Status: {status}")
            if len(rows) > 3:
                print(f"    ... and {len(rows) - 3} more entries")
            print()
        
        # Confirm before removing duplicates
        response = input(f"Remove {total_duplicates} duplicate entries? (y/N): ")
        if response.lower() != 'y':
            print("Duplicate removal cancelled.")
            return
        
        # Keep the best result for each address
        cleaned_results = []
        removed_count = 0
        
        for addr_lower, rows in address_groups.items():
            if len(rows) == 1:
                # No duplicates, keep as is
                cleaned_results.append(rows[0])
            else:
                # Has duplicates, choose the best one
                best_row = self._select_best_result(rows)
                cleaned_results.append(best_row)
                removed_count += len(rows) - 1
                print(f"Kept best result for '{rows[0]['address']}' (removed {len(rows) - 1} duplicates)")
        
        # Save cleaned results
        try:
            with open(DEFAULT_RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
                if cleaned_results:
                    writer = csv.DictWriter(f, fieldnames=cleaned_results[0].keys())
                    writer.writeheader()
                    writer.writerows(cleaned_results)
            
            print(f"\nSuccessfully removed {removed_count} duplicate entries!")
            print(f"Database now contains {len(cleaned_results)} unique addresses")
            
            # Update the loaded results
            self.existing_results = cleaned_results
            
        except Exception as e:
            print(f"Error saving cleaned results: {e}")
    
    def _select_best_result(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best result from multiple entries for the same address."""
        # Priority order for selecting the best result:
        # 1. Successful checks (eligible = true)
        # 2. Most recent check
        # 3. Shortest latency (faster response)
        # 4. Most complete status information
        
        # First, prioritize successful checks
        successful = [row for row in rows if row.get('eligible', '').lower() == 'true']
        if successful:
            rows = successful
        
        # If still multiple, choose the most recent
        if len(rows) > 1:
            # Sort by checked_at timestamp (newest first)
            try:
                rows.sort(key=lambda x: x.get('checked_at', ''), reverse=True)
            except:
                pass  # If timestamp parsing fails, keep original order
        
        # If still multiple, choose the one with shortest latency
        if len(rows) > 1:
            try:
                rows.sort(key=lambda x: float(x.get('latency_sec', 999999)))
            except:
                pass  # If latency parsing fails, keep current order
        
        # Return the first (best) result
        return rows[0]
    
    def retry_failed_addresses(self, error_types: List[str] = None, limit: int = None):
        """Retry addresses that failed with specified error types."""
        print("=== RETRYING FAILED ADDRESSES ===")
        print()
        
        # Identify failed addresses
        failed_by_error = self._identify_failed_addresses()
        
        print("FAILED ADDRESSES BY ERROR TYPE:")
        for error_type, addresses in failed_by_error.items():
            print(f"  {error_type}: {len(addresses)} addresses")
        print()
        
        # Filter by error types if specified
        if error_types:
            failed_by_error = {k: v for k, v in failed_by_error.items() if k in error_types}
            print(f"Filtering to retry only: {', '.join(error_types)}")
        
        # Collect all addresses to retry
        all_failed_addresses = []
        for error_type, addresses in failed_by_error.items():
            all_failed_addresses.extend(addresses)
        
        if limit:
            all_failed_addresses = all_failed_addresses[:limit]
            print(f"Limited to {limit} addresses")
        
        if not all_failed_addresses:
            print("No addresses to retry!")
            return
        
        print(f"Total addresses to retry: {len(all_failed_addresses)}")
        print()
        
        # Confirm before starting
        response = input(f"Start retrying {len(all_failed_addresses)} addresses? (y/N): ")
        if response.lower() != 'y':
            print("Retry cancelled.")
            return
        
        print("Starting retry process...")
        start_time = time.time()
        
        # Process addresses in batches
        total_checked = 0
        total_successful = 0
        total_failed = 0
        new_results = []
        
        for i in range(0, len(all_failed_addresses), self.batch_size):
            batch = all_failed_addresses[i:i + self.batch_size]
            print(f"\nProcessing batch {i//self.batch_size + 1}/{(len(all_failed_addresses) + self.batch_size - 1)//self.batch_size}")
            
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
                            new_results.append(result)
                        else:
                            batch_failed += 1
                            total_failed += 1
                    except Exception as e:
                        print(f"Error processing {addr_data['address']}: {e}")
                        batch_failed += 1
                        total_failed += 1
            
            total_checked += len(batch)
            print(f"Batch completed: {batch_successful} successful, {batch_failed} failed")
            
            # Add delay between batches
            if i + self.batch_size < len(all_failed_addresses):
                print("Waiting 15 seconds before next batch...")
                time.sleep(15)
        
        # Update results.csv
        if new_results:
            self._update_results_csv(new_results)
        
        elapsed_time = time.time() - start_time
        print(f"\n=== RETRY COMPLETED ===")
        print(f"Total checked: {total_checked}")
        print(f"Successful: {total_successful}")
        print(f"Failed: {total_failed}")
        print(f"Time taken: {elapsed_time/3600:.1f} hours")
        
        # Show 5G availability results
        if new_results:
            available = sum(1 for r in new_results if r['eligible'])
            print(f"5G Available: {available}")
            print(f"5G Unavailable: {len(new_results) - available}")
            print(f"Success rate: {available/len(new_results)*100:.1f}%")

def main():
    """Main function."""
    print("=== RETRY FAILED ADDRESSES FROM RESULTS.CSV ===")
    print("This script will retry addresses that failed in previous runs.")
    print()
    
    # Create retry checker
    retry_checker = RetryFailedAddresses(
        max_workers=2,      # Conservative settings
        batch_size=20       # Small batches
    )
    
    # Ask if user wants to remove duplicates first
    print("OPTIONS:")
    print("1. Remove duplicate addresses first (recommended)")
    print("2. Skip duplicate removal and go directly to retry")
    print()
    
    duplicate_choice = input("Choose option (1 or 2): ").strip()
    
    if duplicate_choice == "1":
        print("\n" + "="*50)
        retry_checker._remove_duplicates()
        print("="*50 + "\n")
    
    print("Available error types to retry:")
    print("1. ElementNotInteractableException (most likely to succeed)")
    print("2. TimeoutException (network issues)")
    print("3. NoSuchWindowException (browser issues)")
    print("4. header_not_found (page loading issues)")
    print("5. timeout (general timeouts)")
    print("6. other (various errors)")
    print()
    
    # Get user preferences
    error_types_input = input("Enter error types to retry (comma-separated, or 'all'): ").strip()
    if error_types_input.lower() == 'all':
        error_types = None
    else:
        error_types = [t.strip() for t in error_types_input.split(',') if t.strip()]
    
    limit_input = input("Enter limit on number of addresses to retry (or press Enter for no limit): ").strip()
    limit = int(limit_input) if limit_input else None
    
    print()
    print("Retry Settings:")
    print(f"  Workers: 2")
    print(f"  Batch size: 20")
    print(f"  Error types: {error_types if error_types else 'all'}")
    print(f"  Limit: {limit if limit else 'no limit'}")
    print()
    
    # Run retry
    retry_checker.retry_failed_addresses(error_types=error_types, limit=limit)

if __name__ == "__main__":
    main() 