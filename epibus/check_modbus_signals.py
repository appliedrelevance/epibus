#!/usr/bin/env python
# check_modbus_signals.py - Script to check if there are any Modbus signals defined in the system

import frappe
import json
import sys


def check_modbus_signals():
    """Check if there are any Modbus signals defined in the system"""
    try:
        # Initialize Frappe
        frappe.init(site="epinomy.localhost", sites_path="sites")
        frappe.connect()

        # Get all Modbus connections
        connections = frappe.get_all(
            "Modbus Connection",
            fields=["name", "device_name", "device_type",
                    "host", "port", "enabled"],
            filters={"enabled": 1}
        )

        print(f"Found {len(connections)} Modbus connections")

        # Get signals for each connection
        total_signals = 0
        for conn in connections:
            signals = frappe.get_all(
                "Modbus Signal",
                fields=["name", "signal_name",
                        "signal_type", "modbus_address"],
                filters={"parent": conn["name"]}
            )

            print(
                f"Connection {conn['name']} ({conn['device_name']}) has {len(signals)} signals")
            total_signals += len(signals)

            # Print signal details
            for signal in signals:
                print(
                    f"  - Signal: {signal['name']} ({signal['signal_name']}), Type: {signal['signal_type']}, Address: {signal['modbus_address']}")

        print(f"Total signals: {total_signals}")

        # Check if the PLC Bridge API is working
        try:
            from epibus.api.plc import get_signals
            print("PLC Bridge API module imported successfully")
        except ImportError as e:
            print(f"Error importing PLC Bridge API: {str(e)}")

        # Check if the Redis client is working
        try:
            from epibus.utils.plc_redis_client import PLCRedisClient
            client = PLCRedisClient.get_instance()
            print("Redis client initialized successfully")

            # Try to get signals from Redis
            redis_signals = client.get_signals()
            print(f"Got {len(redis_signals)} signals from Redis")
        except Exception as e:
            print(f"Error initializing Redis client: {str(e)}")

    except Exception as e:
        print(f"Error checking Modbus signals: {str(e)}")
    finally:
        # Destroy Frappe session
        frappe.destroy()


if __name__ == "__main__":
    check_modbus_signals()
