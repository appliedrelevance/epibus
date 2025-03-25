#!/usr/bin/env python
# init_plc_bridge.py - Manual signal publisher for PLC Bridge

import redis
import json
import time
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("init_plc_bridge")

# Path to the JSON file
JSON_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                         "openplc", "US15-B10-B1-PLC.json")

def publish_config_to_redis():
    """Publish the US15-B10-B1-PLC configuration to Redis for the PLC bridge to load"""
    try:
        # Connect to Redis
        r = redis.Redis(host='127.0.0.1', port=11000)
        if not r.ping():
            logger.error("Failed to connect to Redis")
            return False
        
        logger.info("Connected to Redis successfully")
        
        # Load the PLC configuration from JSON file
        if not os.path.exists(JSON_FILE):
            logger.error(f"PLC configuration file not found: {JSON_FILE}")
            return False
            
        with open(JSON_FILE, 'r') as f:
            plc_config = json.load(f)
            
        logger.info(f"Loaded PLC configuration from {JSON_FILE}")
        
        # Format as connections for the bridge
        connection = {
            "name": "US15-B10-B1-PLC",
            "hostname": "192.168.0.11",  # Using real PLC IP
            "port": 502,
            "connection_status": "Connected",
            "enabled": 1,
            "signals": []
        }
        
        # Convert the signals from the JSON file
        if "signals" in plc_config:
            for signal in plc_config["signals"]:
                modbus_signal = {
                    "name": signal.get("name"),
                    "signal_name": signal.get("signal_name", ""),
                    "modbus_address": signal.get("modbus_address", 0),
                    "signal_type": signal.get("signal_type", "Digital Input Contact")
                }
                connection["signals"].append(modbus_signal)
        
        connections = [connection]
        
        # Clear existing keys
        r.delete("plc:connections")
        r.delete("plc:signals")
        
        # Publish connections
        logger.info(f"Publishing connection with {len(connection['signals'])} signals to Redis")
        r.rpush("plc:connections", json.dumps(connections))
        
        # Also publish in legacy format (flat signals list)
        all_signals = []
        for conn in connections:
            if "signals" in conn:
                all_signals.extend(conn["signals"])
        
        logger.info(f"Publishing {len(all_signals)} signals in legacy format")
        r.rpush("plc:signals", json.dumps(all_signals))
        
        # Trigger bridge to reload signals
        logger.info("Triggering bridge to reload signals")
        r.publish("plc:command", json.dumps({
            "command": "reload_signals"
        }))
        
        logger.info("Successfully published PLC configuration to Redis")
        return True
        
    except Exception as e:
        logger.error(f"Error publishing config to Redis: {str(e)}")
        return False

if __name__ == "__main__":
    result = publish_config_to_redis()
    sys.exit(0 if result else 1)