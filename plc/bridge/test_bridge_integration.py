import requests
import json
import time

def listen_for_events(bridge_url, timeout=10):
    """Listens for SSE events from the bridge."""
    try:
        print(f"Connecting to SSE stream at {bridge_url}/events")
        response = requests.get(f"{bridge_url}/events", stream=True, timeout=timeout)
        response.raise_for_status()
        print("Connection successful. Waiting for events...")

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data:'):
                    try:
                        data = json.loads(decoded_line[5:])
                        print(f"Received event: {data}")
                        if data.get('type') == 'signal_update':
                            print("SUCCESS: Received signal_update event.")
                            return True
                    except json.JSONDecodeError:
                        print(f"Could not decode JSON: {decoded_line}")

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to bridge: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
    
    print("Timeout reached without receiving a signal_update event.")
    return False

if __name__ == "__main__":
    # The bridge is running in a container, but is on the host network.
    # We can access it via localhost. The default port is 7654.
    BRIDGE_URL = "http://localhost:7654"
    
    print("Starting integration test for PLC Bridge.")

    # Trigger a signal change
    try:
        print("Attempting to trigger signal change for SIG1...")
        write_response = requests.post(f"{BRIDGE_URL}/write_signal", json={'signal_id': 'SIG1', 'value': True})
        write_response.raise_for_status()
        print("Signal write request sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send write request: {e}")
        print("Integration test FAILED.")
        exit(1)

    if listen_for_events(BRIDGE_URL):
        print("Integration test PASSED.")
    else:
        print("Integration test FAILED.")