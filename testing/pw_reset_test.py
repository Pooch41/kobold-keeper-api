import requests
import json
import time


BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/"
ENDPOINT_PATH = "auth/password/reset/"
API_URL = f"{BASE_URL}{API_PREFIX}{ENDPOINT_PATH}"
TEST_USERNAME = "shell_test_user"
TEST_RECOVERY_KEY = "GvCTcynD2Z"
NEW_PASSWORD = "MySecureNewPassword123"


def exponential_backoff(func, max_retries=5, delay=1.0):
    """Handles transient network errors with exponential backoff."""
    for i in range(max_retries):
        try:
            return func()
        except requests.exceptions.ConnectionError as e:
            if i == max_retries - 1:
                raise e
            wait_time = delay * (2 ** i)
            print(f"Connection failed. Retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)


def run_reset_test():
    """Simulates a password reset request."""
    print("--- Django Password Reset Test Utility ---")
    print(f"Target URL: {API_URL}")
    print(f"Testing User: {TEST_USERNAME}")

    new_password = NEW_PASSWORD
    print(f"Using Recovery Key: {TEST_RECOVERY_KEY}")
    print(f"Using New Password: {new_password}")

    if not all([TEST_USERNAME, TEST_RECOVERY_KEY, new_password]):
        print("\nERROR: Please ensure all TEST data fields are properly configured at the top of the script.")
        return

    payload = {
        "username": TEST_USERNAME,
        "recovery_key": TEST_RECOVERY_KEY,
        "new_password": new_password
    }

    headers = {
        'Content-Type': 'application/json'
    }
    print("\nSending POST request...")

    def make_request():
        return requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=10)

    try:
        response = exponential_backoff(make_request)
    except Exception as e:
        print(f"\n--- FATAL ERROR ---")
        print(f"Could not connect to the API. Is your Django server running at {BASE_URL}?")
        print(f"Details: {e}")
        return

    print(f"\nResponse Status Code: {response.status_code}")

    try:
        response_data = response.json()
    except json.JSONDecodeError:
        print("Response Error: Could not decode JSON. Raw response:")
        print(response.text)
        return

    if response.status_code == 200:
        print("\n✅ SUCCESS: Password Reset Complete.")
        print(f"Detail: {response_data.get('detail', 'No detail provided.')}")
        print(f"User {TEST_USERNAME}'s password has been updated!")

    elif response.status_code == 400:
        print("\n❌ FAILED: Validation Error (Status 400).")
        print("-" * 30)
        print(json.dumps(response_data, indent=4))
        print("-" * 30)
    else:
        print("\n❓ UNEXPECTED ERROR.")
        print(f"Status: {response.status_code}")
        print("Detail:")
        print(json.dumps(response_data, indent=4))


if __name__ == "__main__":
    run_reset_test()
