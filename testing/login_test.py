import json
import time

import requests

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/"
ENDPOINT_PATH = "auth/token/"
API_URL = f"{BASE_URL}{API_PREFIX}{ENDPOINT_PATH}"

TEST_USERNAME = "shell_test_user"
NEW_PASSWORD = "MySecureNewPassword123"


def exponential_backoff(func, max_retries=5, delay=1.0):
    """
    Attempts to call a function (network request) multiple times with increasing
    delay to handle temporary connection issues.

    Args:
        func (callable): The function to execute (e.g., requests.post).
        max_retries (int): Maximum number of attempts.
        delay (float): Initial delay in seconds.
    """
    for i in range(max_retries):
        try:
            return func()
        except requests.exceptions.ConnectionError as e:
            if i == max_retries - 1:
                raise e
            wait_time = delay * (2 ** i)
            print(f"Connection failed. Retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)


def run_login_test():
    """Main function to execute the token acquisition test."""
    print("--- Django JWT Token Acquisition Test Utility ---")
    print(f"Target URL: {API_URL}")
    print(f"Attempting to log in as: {TEST_USERNAME}")

    if not all([TEST_USERNAME, NEW_PASSWORD]):
        print("\nERROR: Please ensure TEST_USERNAME and NEW_PASSWORD are set.")
        return

    payload = {
        "username": TEST_USERNAME,
        "password": NEW_PASSWORD
    }

    headers = {
        'Content-Type': 'application/json'
    }
    print("\nSending POST request to acquire tokens...")

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
        access_token = response_data.get('access')
        refresh_token = response_data.get('refresh')

        if access_token and refresh_token:
            print("\n✅ SUCCESS: JWT Tokens Acquired.")
            print("-" * 30)
            print("ACCESS TOKEN (Bearer Token for API calls):")
            print(access_token[:30] + '...[truncated for display]')
            print("-" * 30)
            print("REFRESH TOKEN (For renewing session):")
            print(refresh_token[:30] + '...[truncated for display]')
            print("-" * 30)
            print("The full authentication system is now confirmed!")
        else:
            print("\n❌ FAILED: Status 200, but tokens are missing.")
            print(json.dumps(response_data, indent=4))

    elif response.status_code == 401:
        print("\n❌ FAILED: Unauthorized (Status 401).")
        print("This usually means the username or password was incorrect.")
        print("-" * 30)
        print(json.dumps(response_data, indent=4))
        print("-" * 30)
    else:
        print("\n❓ UNEXPECTED ERROR.")
        print(f"Status: {response.status_code}")
        print("Detail:")
        print(json.dumps(response_data, indent=4))


if __name__ == "__main__":
    run_login_test()
