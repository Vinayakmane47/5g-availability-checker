#!/usr/bin/env python3
"""
Simple Map Test Script

This script tests if the map data can be loaded directly from the results index.
"""

from indexes import ResultsIndex
from config import DEFAULT_RESULTS_CSV

def test_map_data_loading():
    """Test if map data can be loaded from results.csv."""
    print("Testing map data loading...")
    
    try:
        # Load the results index
        results_index = ResultsIndex()
        results_index.load(DEFAULT_RESULTS_CSV)
        
        if not results_index.ready:
            print("ERROR: Results index not ready")
            return False
        
        print(f"SUCCESS: Loaded {len(results_index.addr)} addresses")
        
        # Count available addresses
        available_count = sum(results_index.elig)
        total_count = len(results_index.elig)
        
        print(f"STATISTICS:")
        print(f"   Total addresses: {total_count}")
        print(f"   5G Available: {available_count}")
        print(f"   5G Unavailable: {total_count - available_count}")
        print(f"   Coverage: {round((available_count / total_count) * 100, 1)}%")
        
        # Show first few addresses
        print(f"\nFIRST 5 ADDRESSES:")
        for i in range(min(5, len(results_index.addr))):
            addr = results_index.addr[i]
            lat = float(results_index.lat[i])
            lon = float(results_index.lon[i])
            available = bool(results_index.elig[i])
            print(f"   {i+1}. {addr} at ({lat}, {lon}) - 5G: {'Available' if available else 'Unavailable'}")
        
        # Show some available addresses
        available_indices = [i for i, elig in enumerate(results_index.elig) if elig]
        if available_indices:
            print(f"\nFIRST 5 AVAILABLE ADDRESSES:")
            for i, idx in enumerate(available_indices[:5]):
                addr = results_index.addr[idx]
                lat = float(results_index.lat[idx])
                lon = float(results_index.lon[idx])
                print(f"   {i+1}. {addr} at ({lat}, {lon})")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_map_data_loading()
    if success:
        print("\nSUCCESS: Map data can be loaded correctly!")
        print("The issue might be with the WebSocket implementation.")
    else:
        print("\nFAILED: Could not load map data.") 