#!/usr/bin/env python3
"""
Redis to Socket.IO Bridge

This script creates a direct bridge between Redis and Socket.IO, forwarding messages
from Redis channels to Socket.IO events. This bypasses Frappe's realtime system
to help diagnose communication issues.

Usage:
    python redis_to_socketio.py [--redis-host HOSTNAME] [--redis-port PORT] [--socketio-port PORT]

Options:
    --redis-host HOSTNAME    Redis hostname [default: 127.0.0.1]
    --redis-port PORT        Redis port [default: 11000]
    --socketio-port PORT     Socket.IO server port [default: 12345]
"""

import redis
import json
import argparse
import time
import sys
import threading
from datetime import datetime
import socketio
import eventlet
from eventlet import wsgi

# Initialize Socket.IO server
sio = socketio.Server(cors_allowed_origins='*', logger=True, engineio_logger=True)
app = socketio.WSGIApp(sio)

# Global variables
clients = set()
redis_client = None
pubsub = None
running = True

@sio.event
def connect(sid, environ):
    """Handle client connection"""
    print(f"Client connected: {sid}")
    clients.add(sid)
    # Send connection confirmation
    sio.emit('message', {'type': 'connection_status', 'data': {'status': 'connected', 'timestamp': time.time()}}, room=sid)

@sio.event
def disconnect(sid):
    """Handle client disconnection"""
    print(f"Client disconnected: {sid}")
    if sid in clients:
        clients.remove(sid)

def redis_listener(host='127.0.0.1', port=11000):
    """Listen for Redis messages and forward to Socket.IO"""
    global redis_client, pubsub, running
    
    try:
        # Connect to Redis
        redis_client = redis.Redis(host=host, port=port, db=0)
        pubsub = redis_client.pubsub()
        
        # Subscribe to channels
        channels = ['plc:signal_update', 'plc:command', 'plc:status']
        pubsub.subscribe(channels)
        
        print(f"Connected to Redis at {host}:{port}")
        print(f"Monitoring channels: {', '.join(channels)}")
        
        # Process messages
        for message in pubsub.listen():
            if not running:
                break
                
            if message['type'] == 'message':
                channel = message['channel']
                data = message['data']
                
                # Convert bytes to string if needed
                if isinstance(channel, bytes):
                    channel = channel.decode('utf-8')
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                
                # Parse JSON data
                try:
                    json_data = json.loads(data)
                except:
                    json_data = data
                
                # Forward to Socket.IO - use a single event type for simplicity
                print(f"Forwarding {channel} message to {len(clients)} clients: {data[:100]}...")
                
                # Send all messages on a single 'message' event with type and data
                sio.emit('message', {
                    'type': channel,
                    'data': json_data,
                    'timestamp': time.time()
                })
                
                # Also send a heartbeat every 5 seconds to keep the connection alive
                current_time = time.time()
                if int(current_time) % 5 == 0:
                    sio.emit('message', {
                        'type': 'heartbeat',
                        'data': {'timestamp': current_time},
                        'timestamp': current_time
                    })
                
    except Exception as e:
        print(f"Redis listener error: {e}")
    finally:
        # Clean up
        if pubsub:
            try:
                pubsub.unsubscribe()
                pubsub.close()
            except:
                pass

def start_server(redis_host='127.0.0.1', redis_port=11000, socketio_port=12345):
    """Start the Socket.IO server and Redis listener"""
    global running
    
    # Start Redis listener in a separate thread
    redis_thread = threading.Thread(
        target=redis_listener, 
        args=(redis_host, redis_port),
        daemon=True
    )
    redis_thread.start()
    
    # Start Socket.IO server
    print(f"Starting Socket.IO server on port {socketio_port}")
    print(f"Open bridge_monitor.html in your browser and connect to: http://localhost:{socketio_port}")
    
    try:
        eventlet.wsgi.server(eventlet.listen(('', socketio_port)), app)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        running = False
        # Wait for Redis thread to finish
        redis_thread.join(timeout=1.0)
        print("Server stopped")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Redis to Socket.IO Bridge")
    parser.add_argument("--redis-host", default="127.0.0.1", help="Redis hostname")
    parser.add_argument("--redis-port", type=int, default=11000, help="Redis port")
    parser.add_argument("--socketio-port", type=int, default=12345, help="Socket.IO server port")
    args = parser.parse_args()
    
    # Start server
    start_server(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        socketio_port=args.socketio_port
    )