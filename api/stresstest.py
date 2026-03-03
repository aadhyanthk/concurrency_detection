import requests
import concurrent.futures
import time

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TARGET_SEAT_ID = 1  
NUM_REQUESTS = 10   

def make_request(mode):
    """Sends a single booking request based on the mode."""
    # Mapping the test modes to our specific API endpoints
    if mode == "pessimistic":
        url = f"{BASE_URL}/seats/{TARGET_SEAT_ID}/hold"
    else:
        url = f"{BASE_URL}/simulate/{mode}/{TARGET_SEAT_ID}"
        
    try:
        response = requests.post(url)
        # Handle cases where the response might not be JSON or contains an error
        if response.status_code == 409:
            return {"success": False, "message": "Pessimistic Conflict: Row was locked/taken."}
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def run_test(mode):
    """Executes a multi-threaded burst of requests."""
    print(f"\n--- STARTING {mode.upper()} TEST ---")
    
    # Reset the seat to AVAILABLE first
    requests.post(f"{BASE_URL}/seed")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_REQUESTS) as executor:
        futures = [executor.submit(make_request, mode) for _ in range(NUM_REQUESTS)]
        results = [f.result() for f in futures]

    # Analyze Results
    # Note: Our pessimistic endpoint returns a 'message' but not always a 'success' boolean
    # so we check for successful strings or 200 status logic.
    success_count = sum(1 for r in results if "held" in str(r).lower() or r.get("success") is True)
    
    print(f"Total Requests: {NUM_REQUESTS}")
    print(f"Success Count: {success_count}")
    
    for i, res in enumerate(results):
        msg = res.get('message') or res.get('detail') or "No message"
        print(f" User {i+1}: {msg}")

if __name__ == "__main__":
    try:
        # 1. Test Unsafe (Expect 10 successes / Double Bookings)
        run_test("unsafe")
        
        time.sleep(1) 
        
        # 2. Test Pessimistic (Expect 1 success / Others blocked by Row Lock)
        run_test("pessimistic")
        
        time.sleep(1)

        # 3. Test Optimistic (Expect 1 success / Others fail Version Check)
        run_test("optimistic")
        
    except Exception as e:
        print(f"Connection failed: {e}. Is your FastAPI server running?")