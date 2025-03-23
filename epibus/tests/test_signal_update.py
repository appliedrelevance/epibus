import frappe
import json
from epibus.utils.plc_redis_client import PLCRedisClient


def simulate_signal_update(signal_name, value):
    """Simulate a signal update from the PLC bridge"""
    print(f"Simulating signal update: {signal_name} = {value}")

    # Get Redis client
    client = PLCRedisClient.get_instance()

    # Create message data
    import time
    message_data = json.dumps({
        "name": signal_name,
        "value": value,
        "timestamp": time.time()
    })

    # Call handle_signal_update directly
    client.handle_signal_update(message_data)

    print(f"Signal update processed for {signal_name}")


def test_with_digital_signal():
    """Test with a digital signal (boolean value)"""
    # Get a digital signal
    signals = frappe.get_all(
        "Modbus Signal",
        filters={"signal_type": ["like", "%Digital%"]},
        fields=["name"],
        limit=1
    )

    if not signals:
        print("No digital signals found. Creating a test signal...")
        # Create a test connection if needed
        if not frappe.db.exists("Modbus Connection", "TEST-CONN-01"):
            connection = frappe.get_doc({
                "doctype": "Modbus Connection",
                "device_name": "Test Connection",
                "device_type": "PLC",
                "host": "localhost",
                "port": 502,
                "enabled": 1
            })
            connection.insert()
            print(f"Created test connection: {connection.name}")
        else:
            connection = frappe.get_doc("Modbus Connection", "TEST-CONN-01")

        # Create a test signal
        signal = frappe.get_doc({
            "doctype": "Modbus Signal",
            "parent": connection.name,
            "parenttype": "Modbus Connection",
            "parentfield": "signals",
            "signal_name": "Test Digital Signal",
            "signal_type": "Digital Output Coil",
            "modbus_address": 100,
            "digital_value": False
        })
        signal.insert()
        print(f"Created test signal: {signal.name}")
        signal_name = signal.name
    else:
        signal_name = signals[0].name

    # Test with both True and False values
    simulate_signal_update(signal_name, True)
    simulate_signal_update(signal_name, False)


def test_with_analog_signal():
    """Test with an analog signal (numeric value)"""
    # Get an analog signal
    signals = frappe.get_all(
        "Modbus Signal",
        filters={"signal_type": ["like", "%Register%"]},
        fields=["name"],
        limit=1
    )

    if not signals:
        print("No analog signals found. Creating a test signal...")
        # Create a test connection if needed
        if not frappe.db.exists("Modbus Connection", "TEST-CONN-01"):
            connection = frappe.get_doc({
                "doctype": "Modbus Connection",
                "device_name": "Test Connection",
                "device_type": "PLC",
                "host": "localhost",
                "port": 502,
                "enabled": 1
            })
            connection.insert()
            print(f"Created test connection: {connection.name}")
        else:
            connection = frappe.get_doc("Modbus Connection", "TEST-CONN-01")

        # Create a test signal
        signal = frappe.get_doc({
            "doctype": "Modbus Signal",
            "parent": connection.name,
            "parenttype": "Modbus Connection",
            "parentfield": "signals",
            "signal_name": "Test Analog Signal",
            "signal_type": "Holding Register",
            "modbus_address": 200,
            "float_value": 0.0
        })
        signal.insert()
        print(f"Created test signal: {signal.name}")
        signal_name = signal.name
    else:
        signal_name = signals[0].name

    # Test with different numeric values
    simulate_signal_update(signal_name, 5)
    simulate_signal_update(signal_name, 15)
    simulate_signal_update(signal_name, 7.5)


def run_tests():
    """Run all tests"""
    print("Starting signal update tests...")
    test_with_digital_signal()
    test_with_analog_signal()
    print("All tests completed")


if __name__ == "__main__":
    run_tests()
