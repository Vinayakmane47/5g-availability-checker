#!/usr/bin/env python3
"""
Test script to verify cleanup handlers work properly.
"""

import time
import signal
import subprocess
import sys

def test_cleanup_on_interrupt():
    """Test that the app cleans up properly when interrupted."""
    print("Testing cleanup on interrupt...")
    print("Starting uvicorn server...")
    
    # Start the server
    process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app:app", 
        "--host", "0.0.0.0", "--port", "8000"
    ])
    
    try:
        # Wait a moment for server to start
        time.sleep(3)
        print("Server started. Testing health endpoint...")
        
        # Test health endpoint
        import requests
        response = requests.get("http://localhost:8000/health")
        print(f"Health check: {response.status_code} - {response.json()}")
        
        # Test status endpoint
        response = requests.get("http://localhost:8000/status")
        print(f"Status check: {response.status_code} - {response.json()}")
        
        print("\nNow testing graceful shutdown...")
        print("Sending SIGINT (Ctrl+C) to the server...")
        
        # Send interrupt signal
        process.send_signal(signal.SIGINT)
        
        # Wait for graceful shutdown
        try:
            process.wait(timeout=10)
            print("SUCCESS: Server shut down gracefully!")
        except subprocess.TimeoutExpired:
            print("FAILED: Server didn't shut down gracefully, forcing...")
            process.kill()
            
    except KeyboardInterrupt:
        print("\nReceived interrupt, testing cleanup...")
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)
            print("SUCCESS: Cleanup on interrupt successful!")
        except subprocess.TimeoutExpired:
            print("FAILED: Cleanup took too long, forcing...")
            process.kill()
    except Exception as e:
        print(f"ERROR: Error during test: {e}")
        process.kill()
    finally:
        # Ensure process is terminated
        if process.poll() is None:
            process.kill()
            process.wait()

if __name__ == "__main__":
    test_cleanup_on_interrupt() 