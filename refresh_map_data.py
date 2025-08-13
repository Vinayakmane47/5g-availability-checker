#!/usr/bin/env python3
"""
Refresh Map Data Script

This script refreshes the results index to ensure the map displays the latest
5G availability data from results.csv.
"""

import sys
import os
from indexes import ResultsIndex
from config import DEFAULT_RESULTS_CSV

def refresh_map_data():
    """Refresh the results index to load latest data."""
    print("Refreshing map data...")
    
    # Check if results.csv exists
    if not os.path.exists(DEFAULT_RESULTS_CSV):
        print(f"Error: {DEFAULT_RESULTS_CSV} not found!")
        return False
    
    try:
        # Create a new results index and load the data
        results_index = ResultsIndex()
        results_index.load(DEFAULT_RESULTS_CSV)
        
        if results_index.ready:
            print(f"SUCCESS: Successfully loaded {len(results_index.addr)} addresses from {DEFAULT_RESULTS_CSV}")
            
            # Count available addresses
            available_count = sum(results_index.elig)
            total_count = len(results_index.elig)
            
            print(f"STATISTICS:")
            print(f"   Total addresses: {total_count}")
            print(f"   5G Available: {available_count}")
            print(f"   5G Unavailable: {total_count - available_count}")
            print(f"   Coverage: {round((available_count / total_count) * 100, 1)}%")
            
            return True
        else:
            print("ERROR: Failed to load results index")
            return False
            
    except Exception as e:
        print(f"ERROR: Error refreshing map data: {e}")
        return False

if __name__ == "__main__":
    success = refresh_map_data()
    if success:
        print("\nSUCCESS: Map data refreshed successfully!")
        print("You can now view the updated data on your map at http://localhost:8000/map")
    else:
        print("\nFAILED: Failed to refresh map data. Check the error messages above.")
        sys.exit(1) 