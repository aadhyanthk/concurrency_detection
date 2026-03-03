import threading
import requests
import time

# Configuration
API_URL = "http://127.0.0.1:8000"
SEAT_ID = 1
TOTAL_USERS = 50

def attempt_booking(endpoint, user_id, results):
    try:
        response = requests.post(f"{API_URL}/{endpoint}/{SEAT_ID}?user_id=User_{user_id}")
        data = response.json()
        if data.get("status") == "success":
            results.append(f"User_{user_id}: SUCCESS")
        else:
            results.append(f"User_{user_id}: FAILED ({data.get('message')})")
    except Exception as e:
        results.append(f"User_{user_id}: ERROR")

def run_stress_test(endpoint_name):
    print(f"\n--- STARTING TEST: {endpoint_name} ---")
    threads = []
    results = []
    
    start_time = time.time()
    
    for i in range(TOTAL_USERS):
        t = threading.Thread(target=attempt_booking, args=(endpoint_name, i, results))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    duration = time.time() - start_time
    
    # Analysis
    success_count = sum(1 for r in results if "SUCCESS" in r)
    fail_count = len(results) - success_count
    
    print(f"Time Taken: {duration:.2f}s")
    print(f"Successful Bookings: {success_count} (Should be 1 for SAFE, >1 for UNSAFE)")
    print(f"Failed Bookings: {fail_count}")

# Menu
print("1. Test UNSAFE (Expect Double Bookings)")
print("2. Test SAFE (Expect 1 Success)")
choice = input("Select Test: ")

if choice == "1":
    run_stress_test("book_seat_unsafe")
elif choice == "2":
    run_stress_test("book_seat_safe")