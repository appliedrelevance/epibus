#!/usr/bin/env python3
"""
Redis PLC Signal Monitor

This script directly connects to Redis and monitors the plc:signal_update and plc:command channels,
printing all messages to the console. It doesn't rely on Frappe's Socket.IO integration.

Usage:
    python redis_monitor.py [--host HOSTNAME] [--port PORT]

Options:
    --host HOSTNAME    Redis hostname [default: 127.0.0.1]
    --port PORT        Redis port [default: 11000]
"""

import redis
import json
import argparse
import time
import sys
from datetime import datetime

def format_message(channel, message):
    """Format a message for display"""
    try:
        # Try to parse as JSON
        data = json.loads(message)
        formatted = json.dumps(data, indent=2)
    except:
        # If not JSON, just use the raw message
        formatted = message
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    return f"[{timestamp}] {channel}:\n{formatted}\n"

def monitor_redis(host='127.0.0.1', port=11000):
    """Monitor Redis channels for PLC messages"""
    try:
        # Connect to Redis
        r = redis.Redis(host=host, port=port, db=0)
        pubsub = r.pubsub()
        
        # Subscribe to channels
        channels = ['plc:signal_update', 'plc:command', 'plc:status']
        pubsub.subscribe(channels)
        
        print(f"Connected to Redis at {host}:{port}")
        print(f"Monitoring channels: {', '.join(channels)}")
        print("Waiting for messages... (press Ctrl-C to quit)\n")
        
        # Process messages
        for message in pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel']
                data = message['data']
                
                # Convert bytes to string if needed
                if isinstance(channel, bytes):
                    channel = channel.decode('utf-8')
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                
                # Print formatted message
                print(format_message(channel, data))
                sys.stdout.flush()  # Ensure output is displayed immediately
                
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        try:
            pubsub.unsubscribe()
            pubsub.close()
        except:
            pass

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Monitor Redis channels for PLC messages")
    parser.add_argument("--host", default="127.0.0.1", help="Redis hostname")
    parser.add_argument("--port", type=int, default=11000, help="Redis port")
    args = parser.parse_args()
    
    # Start monitoring
    monitor_redis(host=args.host, port=args.port)