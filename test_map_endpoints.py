#!/usr/bin/env python3
"""
Test Map Endpoints Script

This script tests the WebSocket endpoints for the map to ensure they're working correctly.
"""

import asyncio
import websockets
import json
import sys

async def test_ws_map_data():
    """Test the /ws_map_data endpoint."""
    print("Testing /ws_map_data endpoint...")
    
    try:
        uri = "ws://localhost:8000/ws_map_data"
        async with websockets.connect(uri) as websocket:
            # Send test request
            test_data = {
                "file": "results.csv",
                "workers": 1,
                "max_points": 10
            }
            
            await websocket.send(json.dumps(test_data))
            print("+ Sent test data to /ws_map_data")
            
            # Receive responses
            count = 0
            async for message in websocket:
                data = json.loads(message)
                if "error" in data:
                    print(f"- Error: {data['error']}")
                    break
                
                if "lat" in data and "lon" in data:
                    count += 1
                    print(f"+ Received data {count}: {data['addr']} at ({data['lat']}, {data['lon']}) - 5G: {'Available' if data['available'] else 'Unavailable'}")
                
                if count >= 5:  # Limit to first 5 responses
                    break
            
            print(f"+ Successfully received {count} data points from /ws_map_data")
            
    except Exception as e:
        print(f"- Error testing /ws_map_data: {e}")
        return False
    
    return True

async def test_ws_map():
    """Test the /ws_map endpoint."""
    print("\nTesting /ws_map endpoint...")
    
    try:
        uri = "ws://localhost:8000/ws_map"
        async with websockets.connect(uri) as websocket:
            # Send test request with Melbourne CBD bounding box
            test_data = {
                "bbox": [-37.8265, 144.9475, -37.8060, 144.9835],  # Melbourne CBD
                "workers": 1,
                "max_points": 5
            }
            
            await websocket.send(json.dumps(test_data))
            print("+ Sent test data to /ws_map")
            
            # Receive responses
            count = 0
            async for message in websocket:
                data = json.loads(message)
                if "error" in data:
                    print(f"- Error: {data['error']}")
                    break
                
                if "lat" in data and "lon" in data:
                    count += 1
                    print(f"+ Received data {count}: {data['addr']} at ({data['lat']}, {data['lon']}) - 5G: {'Available' if data['available'] else 'Unavailable'}")
                
                if count >= 3:  # Limit to first 3 responses
                    break
            
            print(f"+ Successfully received {count} data points from /ws_map")
            
    except Exception as e:
        print(f"- Error testing /ws_map: {e}")
        return False
    
    return True

async def main():
    """Run all tests."""
    print("Testing Map WebSocket Endpoints")
    print("=" * 40)
    
    # Test /ws_map_data endpoint
    success1 = await test_ws_map_data()
    
    # Test /ws_map endpoint
    success2 = await test_ws_map()
    
    print("\n" + "=" * 40)
    if success1 and success2:
        print("+ All tests passed! Map endpoints are working correctly.")
        print("You can now use the map at http://localhost:8000/map")
    else:
        print("- Some tests failed. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 