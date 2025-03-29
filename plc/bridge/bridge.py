#!/usr/bin/env python3
import os
import sys
import time
import logging
import threading
import argparse
import requests
import json
import queue
import random
from typing import Dict, List, Union, Optional, Set
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from flask import Flask, Response, jsonify, request
from flask_cors import CORS

# Import from local config file
import config

class SSEClient:
    """Client for SSE connections"""
    def __init__(self):
        self.queue = queue.Queue()
    
    def add_event(self, event):
        """Add an event to the client's queue"""
        self.queue.put(event)
    
    def has_event(self):
        """Check if the client has events"""
        return not self.queue.empty()
    
    def get_event(self):
        """Get the next event from the queue"""
        return self.queue.get()

class SSEServer:
    """Server-Sent Events server"""
    def __init__(self, host='0.0.0.0', port=7654, plc_bridge=None):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.clients = set()
        self.plc_bridge = plc_bridge
        self.logger = logging.getLogger(__name__)
        
        # Configure CORS
        CORS(self.app)
        
        # Set up routes
        self.app.route('/events')(self.sse_stream)
        self.app.route('/signals')(self.get_signals)
        self.app.route('/write_signal', methods=['POST'])(self.write_signal)
        self.app.route('/events/history')(self.get_event_history)
        self.app.route('/shutdown')(self.shutdown)
        
    def _cleanup_stale_connections(self):
        """Periodically clean up stale connections"""
        while True:
            try:
                # Log current connection count
                self.logger.info(f"Connection cleanup check - Current clients: {len(self.clients)}")
                
                # Sleep for a while
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in connection cleanup: {e}")
                time.sleep(5)  # Prevent tight error loop
    def start(self):
        """Start the SSE server in a separate thread"""
        # Check if the port is available
        try:
            # Try to create a socket on the port to check if it's available
            import socket
            import subprocess
            
            # First, check if the port is in use
            try:
                # Try to bind to the port without SO_REUSEADDR to check if it's truly available
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind((self.host, self.port))
                s.close()
                self.logger.info(f"Port {self.port} is available")
            except socket.error:
                self.logger.warning(f"Port {self.port} is already in use, checking for processes")
            
            # Try to find and kill any processes using this port
            try:
                result = subprocess.run(
                    f"lsof -i :{self.port} -t",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    self.logger.info(f"Found processes using port {self.port}: {pids}")
                    
                    # Kill each process
                    for pid in pids:
                        if pid.strip():
                            try:
                                self.logger.info(f"Killing process {pid} using port {self.port}")
                                subprocess.run(f"kill -9 {pid}", shell=True)
                            except Exception as kill_error:
                                self.logger.warning(f"Error killing process {pid}: {kill_error}")
                    
                    # Wait a moment for the processes to be killed
                    import time
                    time.sleep(1)
            except Exception as proc_error:
                self.logger.warning(f"Error checking/killing processes: {proc_error}")
            
            # Now try to bind to the port without SO_REUSEADDR
            # This was already done at the beginning of this method, so we can skip it here
            # and just start the server
            self.logger.info(f"Starting SSE server on http://{self.host}:{self.port}")
        except socket.error:
            # Port is not available
            self.logger.error(f"Port {self.port} is already in use. Cannot start SSE server.")
            self.logger.error("Please ensure all other instances of the PLC Bridge are stopped.")
            self.logger.error("You can use 'pkill -f \"python bridge.py\"' to kill all instances.")
            raise RuntimeError(f"Port {self.port} is already in use. Cannot start SSE server.")
            raise RuntimeError(f"Port {self.port} is already in use. Cannot start SSE server.")
        
        # Start the Flask app in a separate thread
        threading.Thread(target=self.app.run,
                         kwargs={'host': self.host, 'port': self.port, 'threaded': True},
                         daemon=True).start()
        
        # Start the connection cleanup thread
        threading.Thread(target=self._cleanup_stale_connections,
                         daemon=True).start()
        
    def sse_stream(self):
        """SSE stream endpoint with proper event formatting and connection cleanup"""
        def event_stream():
            client = SSEClient()
            client_id = id(client)  # Get unique ID for this client
            self.clients.add(client)
            self.logger.info(f"New SSE client connected (ID: {client_id}). Total clients: {len(self.clients)}")
            
            try:
                # Send initial connection message (properly formatted)
                yield "data: {}\n\n".format(json.dumps({'type': 'connection', 'status': 'connected'}))
                
                # Keep connection alive with timeout detection
                heartbeat_count = 0
                max_missed_heartbeats = 3  # Consider connection dead after 3 missed heartbeats
                
                while True:
                    if client.has_event():
                        event = client.get_event()
                        # Yield complete event in one statement
                        yield "event: {}\ndata: {}\n\n".format(event['type'], json.dumps(event['data']))
                    else:
                        # Send heartbeat every 5 seconds
                        yield "event: heartbeat\ndata: {}\n\n".format(time.time())
                        heartbeat_count += 1
                        
                        # Check if client is still connected every few heartbeats
                        if heartbeat_count >= max_missed_heartbeats:
                            heartbeat_count = 0
                            # This will raise an exception if the client is disconnected
                            yield ""
                            
                        time.sleep(5)
            except Exception as e:
                self.logger.error(f"Error in SSE stream for client {client_id}: {e}")
            finally:
                if client in self.clients:
                    self.clients.remove(client)
                    self.logger.info(f"SSE client disconnected (ID: {client_id}). Remaining clients: {len(self.clients)}")
                
        return Response(event_stream(), mimetype="text/event-stream")
    
    def get_signals(self):
        """API endpoint to get all signals"""
        if not self.plc_bridge:
            return jsonify({"signals": [], "error": "PLC Bridge not initialized"})
            
        signals_data = []
        for signal_name, signal in self.plc_bridge.signals.items():
            signals_data.append({
                "name": signal.name,
                "signal_name": signal.signal_name,
                "value": signal.value,
                "timestamp": signal.last_update
            })
            
        return jsonify({"signals": signals_data})
    
    def write_signal(self):
        """API endpoint to write a signal value"""
        if not self.plc_bridge:
            return jsonify({"success": False, "message": "PLC Bridge not initialized"})
            
        try:
            data = request.json
            signal_id = data.get('signal_id')
            value = data.get('value')
            
            if not signal_id or value is None:
                return jsonify({"success": False, "message": "Missing signal_id or value"})
                
            # Find the signal
            if signal_id not in self.plc_bridge.signals:
                return jsonify({"success": False, "message": f"Signal {signal_id} not found"})
                
            signal = self.plc_bridge.signals[signal_id]
            
            # Find the connection for this signal
            connection_name = self.plc_bridge._get_connection_name(signal_id)
            if not connection_name:
                return jsonify({"success": False, "message": f"Connection for signal {signal_id} not found"})
                
            # Write the value
            success = self.plc_bridge._write_signal(connection_name, signal, value)
            
            return jsonify({"success": success})
            
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    def get_event_history(self):
        """API endpoint to get event history"""
        if not self.plc_bridge:
            return jsonify({"events": [], "error": "PLC Bridge not initialized"})
            
        return jsonify({"events": self.plc_bridge.event_history})
    
    def shutdown(self):
        """Shutdown the Flask server"""
        self.logger.info("Shutdown request received")
        
        # Function to shutdown the Werkzeug server
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            self.logger.warning("Not running with Werkzeug server, cannot shut down cleanly")
            return jsonify({"status": "error", "message": "Not running with Werkzeug server"})
            
        func()
        return jsonify({"status": "success", "message": "Server shutting down..."})
        return jsonify({"events": self.plc_bridge.event_history})
        
    def stop(self):
        """Stop the SSE server and release resources"""
        self.logger.info("Stopping SSE server...")
        
        # Clear all clients
        self.clients.clear()
        
        # Attempt to shutdown the Flask server
        try:
            # Get the werkzeug server
            import requests
            # Make a request to shut down the server
            try:
                requests.get(f"http://localhost:{self.port}/shutdown", timeout=2)
                # Wait a moment for the server to process the shutdown request
                import time
                time.sleep(1)
            except Exception as req_error:
                self.logger.warning(f"Error requesting server shutdown: {req_error}")
            
            # Force kill any processes using this port
            import subprocess
            import os
            try:
                # Find processes using the port
                self.logger.info(f"Checking for processes using port {self.port}")
                result = subprocess.run(
                    f"lsof -i :{self.port} -t",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    self.logger.info(f"Found processes using port {self.port}: {pids}")
                    
                    # Kill each process
                    for pid in pids:
                        if pid.strip():
                            try:
                                # Check if this is our own process
                                if int(pid.strip()) != os.getpid():
                                    self.logger.info(f"Killing process {pid} using port {self.port}")
                                    subprocess.run(f"kill -9 {pid}", shell=True)
                            except Exception as kill_error:
                                self.logger.warning(f"Error killing process {pid}: {kill_error}")
            except Exception as proc_error:
                self.logger.warning(f"Error checking/killing processes: {proc_error}")
            
            self.logger.info(f"SSE server on port {self.port} stopped")
        except Exception as e:
            self.logger.error(f"Error stopping SSE server: {e}")
    
    def publish_event(self, event_type, data):
        """Publish an event to all connected clients with proper error handling and throttling"""
        # Skip if no clients are connected
        if not self.clients:
            return
            
        # Initialize throttling data structures if they don't exist
        if not hasattr(self, '_last_event_updates'):
            self._last_event_updates = {}
        if not hasattr(self, '_event_counts'):
            self._event_counts = {}
        if not hasattr(self, '_last_event_log_time'):
            self._last_event_log_time = time.time()
            
        # Get the current time
        now = time.time()
        
        # Define throttling intervals for different event types (in seconds)
        throttle_intervals = {
            'signal_update': 1.0,        # Max 1 update per second per signal
            'signal_updates_batch': 1.0,  # Max 1 batch per second
            'status_update': 5.0,        # Max 1 status update every 5 seconds
            'heartbeat': 10.0,           # Max 1 heartbeat every 10 seconds
            'event_log': 2.0,            # Max 1 event log every 2 seconds
            'error': 5.0,                # Max 1 error event every 5 seconds
            'default': 1.0               # Default for other event types
        }
        
        # Get the appropriate throttle interval
        throttle_interval = throttle_intervals.get(event_type, throttle_intervals['default'])
        
        # For signal updates, throttle by signal name
        if event_type == 'signal_update':
            signal_name = data.get('name', '')
            if signal_name:
                # Check if we've published this signal recently
                last_update = self._last_event_updates.get(f"signal:{signal_name}", 0)
                if now - last_update < throttle_interval:
                    return
                
                # Update the last update time
                self._last_event_updates[f"signal:{signal_name}"] = now
        # For other event types, throttle by event type
        else:
            # Check if we've published this event type recently
            last_update = self._last_event_updates.get(event_type, 0)
            if now - last_update < throttle_interval:
                return
                
            # Update the last update time
            self._last_event_updates[event_type] = now
            
        # Count events for logging
        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1
        
        # Log event counts periodically
        if now - self._last_event_log_time > 10.0:  # Every 10 seconds
            if self._event_counts:
                self.logger.info(f"Events published in last 10s: {self._event_counts}")
            self._event_counts = {}
            self._last_event_log_time = now
        
        # Make a copy of the clients set to avoid "set changed size during iteration" errors
        clients_copy = set(self.clients)
        
        # Skip if no clients
        if not clients_copy:
            return
            
        # Track how many clients we successfully sent to
        success_count = 0
        
        for client in clients_copy:
            try:
                client.add_event({
                    'type': event_type,
                    'data': data
                })
                success_count += 1
            except Exception as e:
                # If we can't add an event to a client, it's likely disconnected
                self.logger.warning(f"Failed to add event to client (ID: {id(client)}): {e}")
                # Try to remove the client from the set
                try:
                    if client in self.clients:
                        self.clients.remove(client)
                        self.logger.info(f"Removed stale client (ID: {id(client)}). Remaining clients: {len(self.clients)}")
                except Exception as remove_error:
                    self.logger.error(f"Error removing stale client: {remove_error}")
        
        # Log summary
        if success_count > 0:
            self.logger.debug(f"Published {event_type} event to {success_count}/{len(clients_copy)} clients")

class ModbusSignal:
    """Representation of a Modbus signal"""
    def __init__(self, name: str, address: int, signal_type: str, signal_name: str = None):
        self.name = name
        self.address = address
        self.type = signal_type
        self.signal_name = signal_name or name
        self.value = None
        self.last_update = 0

class PLCBridge:
    """Standalone PLC Bridge with REST API communication"""
    
    def __init__(self, 
                 frappe_url: str, 
                 api_key: str, 
                 api_secret: str, 
                 poll_interval: float = 1.0):
        # Load configuration
        config_data = config.load_config()
        
        # Override with provided values
        self.frappe_url = frappe_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.poll_interval = poll_interval or config_data["poll_interval"]
        
        # Logging setup
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, config_data["log_level"]))
        
        # Clear any existing handlers to avoid duplicates
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
            
        # Add handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # File handler
        file_handler = logging.FileHandler("plc_bridge.log")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Session for API calls
        self.session = self._create_authenticated_session()
        
        # Signal management
        self.signals: Dict[str, ModbusSignal] = {}
        
        # Modbus clients for connections
        self.modbus_clients: Dict[str, Dict] = {}
        
        # Control flags
        self.running = False
        self.poll_thread = None
        
        # Event history
        self.event_history = []
        self.max_events = 100
        
        # Initialize SSE server
        self.sse_server = SSEServer(
            host=config_data.get("sse_host", "0.0.0.0"),
            port=config_data.get("sse_port", 7654),
            plc_bridge=self
        )
    
    def _get_connection_name(self, signal_name):
        """Get the connection name for a signal"""
        # Try method 1: Check the cache
        if hasattr(self, 'signal_connections') and signal_name in self.signal_connections:
            return self.signal_connections[signal_name]
            
        # Try method 2: Split by hyphen
        if "-" in signal_name:
            connection_name = signal_name.split("-")[0]
            # Cache the result for future use
            if hasattr(self, 'signal_connections'):
                self.signal_connections[signal_name] = connection_name
            return connection_name
        
        # Try method 3: API call to get parent (only if cache miss)
        try:
            self.logger.warning(f"Cache miss for signal {signal_name}, making API call")
            response = self.session.get(
                f"{self.frappe_url}/api/resource/Modbus Signal/{signal_name}",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            connection_name = data.get('data', {}).get('parent')
            
            # Cache the result for future use
            if connection_name and hasattr(self, 'signal_connections'):
                self.signal_connections[signal_name] = connection_name
                self.logger.info(f"Cached connection {connection_name} for signal {signal_name} from API")
                
            return connection_name
        except Exception as e:
            self.logger.warning(f"API call failed for signal {signal_name}: {e}")
        
        # Try method 4: Use first Modbus client as default
        if self.modbus_clients:
            default_connection = list(self.modbus_clients.keys())[0]
            # Cache the result for future use
            if hasattr(self, 'signal_connections'):
                self.signal_connections[signal_name] = default_connection
                self.logger.warning(f"Using default connection {default_connection} for signal {signal_name}")
            return default_connection
        
        return None
    
    def _add_event_to_history(self, event):
        """Add an event to the history"""
        # Add unique ID if not present
        if 'id' not in event:
            event['id'] = f"event-{time.time()}-{random.randint(1000, 9999)}"
            
        # Add to beginning of array and limit size
        self.event_history.insert(0, event)
        if len(self.event_history) > self.max_events:
            self.event_history = self.event_history[:self.max_events]
    
    def _create_authenticated_session(self):
        """Create an authenticated session for API calls"""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'token {self.api_key}:{self.api_secret}',
            'Content-Type': 'application/json'
        })
        return session
    
    def load_signals(self):
        """Load signals from Frappe"""
        try:
            self.logger.info("Loading signals from Frappe API...")
            response = self.session.get(
                f"{self.frappe_url}/api/method/epibus.api.plc.get_all_signals",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Debug: Log the full response data
            # Pretty print the API response for better readability
            import json
            self.logger.debug(f"API Response: {json.dumps(data, indent=2)}")
            
            # Handle nested response structure - Frappe API methods wrap results in a 'message' field
            if 'message' in data:
                self.logger.debug("Found nested message structure in API response")
                data = data.get('message', {})
            
            if not data.get('success'):
                import json
                self.logger.error(f"Failed to load signals: {json.dumps(data, indent=2)}")
                return False
            
            # Initialize modbus clients and signals
            self.modbus_clients = {}
            self.signals = {}
            self.signal_connections = {}  # Cache for signal to connection mapping
            
            connections = data.get('data', [])
            if not connections:
                self.logger.warning("No PLC connections found in API response")
                return False
                
            for connection in connections:
                # Create Modbus client for this connection
                conn_name = connection.get('name')
                host = connection.get('host')
                port = connection.get('port', 502)
                
                if not conn_name or not host:
                    self.logger.warning(f"Skipping invalid connection: {connection}")
                    continue
                
                self.logger.debug(f"Setting up connection to {conn_name} at {host}:{port}")
                self.modbus_clients[conn_name] = {
                    'client': ModbusTcpClient(host=host, port=port),
                    'connected': False,
                    'host': host,
                    'port': port
                }
                
                # Process signals for this connection
                signals_list = connection.get('signals', [])
                if not signals_list:
                    self.logger.warning(f"No signals found for connection {conn_name}")
                    continue
                    
                for signal_data in signals_list:
                    try:
                        signal = ModbusSignal(
                            name=signal_data['name'],
                            address=signal_data['modbus_address'],
                            signal_type=signal_data['signal_type'],
                            signal_name=signal_data.get('signal_name')
                        )
                        self.signals[signal.name] = signal
                        
                        # Store the connection information for this signal
                        self.signal_connections[signal.name] = conn_name
                        self.logger.debug(f"Cached connection {conn_name} for signal {signal.name}")
                    except KeyError as ke:
                        self.logger.warning(f"Skipping signal with missing required field: {ke} in {signal_data}")
                    except Exception as se:
                        self.logger.warning(f"Error processing signal {signal_data.get('name', 'unknown')}: {se}")
            
            if not self.signals:
                self.logger.warning("No valid signals were loaded")
                return False
                
            self.logger.info(f"Successfully loaded {len(self.signals)} signals from {len(self.modbus_clients)} connections")
            return True
        
        except Exception as e:
            self.logger.error(f"Error loading signals: {e}")
            return False
    
    def _connect_client(self, connection_name):
        """Connect to a Modbus client with improved error handling and throttling"""
        if connection_name not in self.modbus_clients:
            self.logger.error(f"Unknown connection: {connection_name}")
            return False
            
        client_info = self.modbus_clients[connection_name]
        
        # If already connected, return True
        if client_info['connected']:
            return True
            
        # Check if we've tried to connect recently
        now = time.time()
        last_attempt = client_info.get('last_connect_attempt', 0)
        retry_interval = client_info.get('retry_interval', 5.0)  # Start with 5 seconds
        
        # If we've tried recently, don't try again yet
        if now - last_attempt < retry_interval:
            return False
            
        # Update last attempt time
        client_info['last_connect_attempt'] = now
        
        # Try to connect
        try:
            client = client_info['client']
            host = client_info['host']
            port = client_info['port']
            
            # Try to connect
            if client.connect():
                client_info['connected'] = True
                client_info['retry_interval'] = 5.0  # Reset retry interval on success
                client_info['connect_failures'] = 0  # Reset failure count
                self.logger.info(f"Connected to {connection_name} at {host}:{port}")
                return True
            else:
                # Increment failure count and increase retry interval
                failures = client_info.get('connect_failures', 0) + 1
                client_info['connect_failures'] = failures
                
                # Exponential backoff with max of 60 seconds
                client_info['retry_interval'] = min(retry_interval * 1.5, 60.0)
                
                self.logger.error(f"Failed to connect to {connection_name} (attempt {failures}). Will retry in {client_info['retry_interval']:.1f}s")
                return False
                
        except Exception as e:
            # Increment failure count and increase retry interval
            failures = client_info.get('connect_failures', 0) + 1
            client_info['connect_failures'] = failures
            
            # Exponential backoff with max of 60 seconds
            client_info['retry_interval'] = min(retry_interval * 1.5, 60.0)
            
            self.logger.error(f"Error connecting to {connection_name} (attempt {failures}): {e}")
            return False
    
    def _poll_signals(self):
        """Continuously poll signals and update via SSE with improved throttling"""
        last_status_update = 0
        status_update_interval = 10  # Send status updates every 10 seconds (increased from 2)
        
        # Add counters for API calls
        api_call_count = 0
        poll_cycle_count = 0
        
        while self.running:
            try:
                # Reset API call counter for this cycle
                api_call_count = 0
                poll_cycle_count += 1
                
                # Publish status update periodically (only if there are clients)
                current_time = time.time()
                if current_time - last_status_update > status_update_interval:
                    # The _publish_status_update method now checks for clients
                    self._publish_status_update()
                    last_status_update = current_time
                
                # Group signals by connection for efficient polling
                signals_by_connection = {}
                for signal_name, signal in self.signals.items():
                    # Use the _get_connection_name method which now uses caching
                    connection_name = self._get_connection_name(signal_name)
                    
                    # If no connection, log error and skip
                    if not connection_name and self.modbus_clients:
                        connection_name = list(self.modbus_clients.keys())[0]
                        self.logger.warning(f"Using default connection {connection_name} for signal {signal_name}")
                    
                    # If still no connection, log error and skip
                    if not connection_name:
                        self.logger.error(f"Cannot determine connection for signal {signal_name}")
                        continue
                    
                    if connection_name not in signals_by_connection:
                        signals_by_connection[connection_name] = []
                    signals_by_connection[connection_name].append(signal)
                
                # Process signals by connection
                for connection_name, signals in signals_by_connection.items():
                    # Connect to the Modbus client if needed
                    if not self._connect_client(connection_name):
                        continue
                    
                    # Read signals for this connection
                    for signal in signals:
                        new_value = self._read_signal(connection_name, signal)
                        
                        if new_value is not None and new_value != signal.value:
                            old_value = signal.value
                            signal.value = new_value
                            signal.last_update = time.time()
                            
                            # Log detailed signal change
                            self.logger.info(
                                f"Signal Change: {signal.signal_name} "
                                f"(Address: {signal.address}, Type: {signal.type}) "
                                f"changed from {old_value} to {new_value}"
                            )
                            
                            # Send update to Frappe
                            self._publish_signal_update(signal)
                
                # Log API call statistics every 10 cycles
                if poll_cycle_count % 10 == 0:
                    self.logger.warning(f"API Call Stats: Made {api_call_count} API calls to Modbus Signal in polling cycle {poll_cycle_count}")
                
                # Sleep for configured poll interval
                time.sleep(self.poll_interval)
            
            except Exception as e:
                self.logger.error(f"Error in signal polling: {e}")
                time.sleep(1)  # Prevent tight error loop
    
    def _read_signal(self, connection_name: str, signal: ModbusSignal) -> Optional[Union[bool, int, float]]:
        """Read a signal value from the PLC"""
        if connection_name not in self.modbus_clients:
            self.logger.error(f"Unknown connection: {connection_name}")
            return None
            
        client_info = self.modbus_clients[connection_name]
        if not client_info['connected']:
            if not self._connect_client(connection_name):
                return None
        
        client = client_info['client']
        
        try:
            if signal.type == "Digital Input Contact":
                result = client.read_discrete_inputs(
                    address=signal.address, count=1)
                if result.isError():
                    self.logger.error(
                        f"Error reading Digital Input Contact {signal.name}: "
                        f"Address {signal.address}, Error: {result}"
                    )
                    return None
                return result.bits[0]
            
            elif signal.type == "Digital Output Coil":
                result = client.read_coils(
                    address=signal.address, count=1)
                if result.isError():
                    self.logger.error(
                        f"Error reading Digital Output Coil {signal.name}: "
                        f"Address {signal.address}, Error: {result}"
                    )
                    return None
                return result.bits[0]
            
            elif signal.type == "Holding Register":
                result = client.read_holding_registers(
                    address=signal.address, count=1)
                if result.isError():
                    self.logger.error(
                        f"Error reading Holding Register {signal.name}: "
                        f"Address {signal.address}, Error: {result}"
                    )
                    return None
                return result.registers[0]
            
            elif signal.type == "Analog Input Register":
                result = client.read_input_registers(
                    address=signal.address, count=1)
                if result.isError():
                    self.logger.error(
                        f"Error reading Analog Input Register {signal.name}: "
                        f"Address {signal.address}, Error: {result}"
                    )
                    return None
                return result.registers[0]
            
            else:
                self.logger.warning(
                    f"Unsupported signal type for {signal.name}: {signal.type}. "
                    "Supported types: Digital Input Contact, Digital Output Coil, "
                    "Holding Register, Analog Input Register"
                )
                return None
                
        except ModbusException as e:
            self.logger.error(f"Modbus error reading {signal.name}: {e}")
            client_info['connected'] = False
            return None
        except Exception as e:
            self.logger.error(f"Error reading {signal.name}: {e}")
            return None
    
    def _write_signal(self, connection_name: str, signal: ModbusSignal, value: Union[bool, int, float]) -> bool:
        """Write a signal value to the PLC"""
        if connection_name not in self.modbus_clients:
            self.logger.error(f"Unknown connection: {connection_name}")
            return False
            
        client_info = self.modbus_clients[connection_name]
        if not client_info['connected']:
            if not self._connect_client(connection_name):
                return False
        
        client = client_info['client']
        
        try:
            if signal.type == "Digital Output Coil":
                result = client.write_coil(
                    address=signal.address, value=bool(value))
                if result.isError():
                    self.logger.error(f"Error writing to {signal.name}: {result}")
                    return False
                
                # Update local cache
                signal.value = bool(value)
                signal.last_update = time.time()
                
                # Publish update to Frappe
                self._publish_signal_update(signal)
                
                return True
                
            elif signal.type == "Holding Register":
                result = client.write_register(
                    address=signal.address, value=int(value))
                if result.isError():
                    self.logger.error(f"Error writing to {signal.name}: {result}")
                    return False
                
                # Update local cache
                signal.value = int(value)
                signal.last_update = time.time()
                
                # Publish update to Frappe
                self._publish_signal_update(signal)
                
                return True
                
            else:
                self.logger.warning(f"Cannot write to read-only signal type: {signal.type}")
                return False
                
        except ModbusException as e:
            self.logger.error(f"Modbus error writing to {signal.name}: {e}")
            client_info['connected'] = False
            return False
        except Exception as e:
            self.logger.error(f"Error writing to {signal.name}: {e}")
            return False
    
    def _publish_signal_update(self, signal: ModbusSignal):
        """Publish a signal update via SSE with improved batching and throttling"""
        try:
            # Initialize batch collection if it doesn't exist
            if not hasattr(self, '_signal_update_batch'):
                self._signal_update_batch = []
                self._last_batch_time = time.time()
                self._batch_sizes = []  # Track batch sizes for logging
                
            # Create event data
            update_data = {
                'name': signal.name,
                'signal_name': signal.signal_name,
                'value': signal.value,
                'timestamp': signal.last_update,
                'source': 'plc_bridge'  # Explicitly set source to 'plc_bridge'
            }
            
            # Log the update data for debugging
            self.logger.debug(f"Signal update data: {update_data}")
            
            # Add to batch
            self._signal_update_batch.append(update_data)
            
            # Check if it's time to send the batch
            now = time.time()
            batch_interval = 1.0  # Send batch every 1 second (increased from 0.5)
            max_batch_size = 25   # Maximum batch size (increased from 10)
            
            # Only send batches if there are clients connected
            if self.sse_server.clients and (now - getattr(self, '_last_batch_time', 0) >= batch_interval or
                                           len(self._signal_update_batch) >= max_batch_size):
                # Send the batch
                if len(self._signal_update_batch) > 1:
                    # Send as batch
                    self.sse_server.publish_event('signal_updates_batch', {'updates': self._signal_update_batch})
                    self.logger.debug(f"Published batch of {len(self._signal_update_batch)} signal updates")
                    
                    # Track batch sizes for logging
                    self._batch_sizes.append(len(self._signal_update_batch))
                    if len(self._batch_sizes) > 10:
                        avg_batch_size = sum(self._batch_sizes) / len(self._batch_sizes)
                        self.logger.info(f"Average batch size: {avg_batch_size:.1f} signals (last 10 batches)")
                        self._batch_sizes = []
                        
                elif len(self._signal_update_batch) == 1:
                    # Send as single update
                    self.sse_server.publish_event('signal_update', self._signal_update_batch[0])
                
                # Reset batch
                self._signal_update_batch = []
                self._last_batch_time = now
            # If no clients are connected, periodically clear the batch to prevent memory buildup
            elif not self.sse_server.clients and (now - getattr(self, '_last_batch_time', 0) >= 5.0 or
                                                 len(self._signal_update_batch) >= 100):
                self.logger.debug(f"No clients connected, discarding batch of {len(self._signal_update_batch)} signal updates")
                self._signal_update_batch = []
                self._last_batch_time = now
            
            # Log the event (but don't send individual event_log events for each signal update)
            event_data = {
                'event_type': 'Signal Update',
                'status': 'Success',
                'connection': self._get_connection_name(signal.name),
                'signal': signal.name,
                'new_value': str(signal.value),
                'message': f"Signal {signal.signal_name} updated to {signal.value} via PLC Bridge",
                'timestamp': time.time()
            }
            
            # Add to event history
            self._add_event_to_history(event_data)
            
            # Only send event_log events very occasionally to reduce traffic
            if random.random() < 0.01:  # Only send ~1% of event logs (reduced from 10%)
                self.sse_server.publish_event('event_log', event_data)
            
            # Process any actions triggered by this signal
            self._process_signal_actions(signal.name, signal.value)
            
        except Exception as e:
            self.logger.error(f"Error publishing signal update: {e}")
            # Publish error event
            error_data = {
                'event_type': 'Error',
                'status': 'Failed',
                'message': f"Error publishing signal update: {str(e)}",
                'timestamp': time.time()
            }
            self.sse_server.publish_event('error', error_data)
            self._add_event_to_history(error_data)
    
    def _log_event_to_frappe(self, event_data):
        """Log an event to Frappe for persistence"""
        try:
            response = self.session.post(
                f"{self.frappe_url}/api/method/epibus.api.plc.log_event",
                json=event_data,
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Error logging event to Frappe: {e}")
    
    def _process_signal_actions(self, signal_name, signal_value):
        """Process any actions triggered by this signal"""
        try:
            # Find any Modbus Action documents with this signal linked
            self.logger.info(f"Looking for Modbus Actions linked to signal: {signal_name}")
            
            # Use the signal name as the ID (they should be the same)
            signal_id = signal_name
            
            # Create a placeholder for signal data that we'll populate if needed
            signal_data = {'name': signal_name, 'signal_name': signal_name}
            
            # Query for Modbus Actions using the signal ID
            filter_json = json.dumps([["modbus_signal", "=", signal_id]])
            action_response = self.session.get(
                f"{self.frappe_url}/api/resource/Modbus Action",
                params={"filters": filter_json},
                timeout=10
            )
            action_response.raise_for_status()
            actions_data = action_response.json()
            
            if 'data' in actions_data:
                actions = actions_data['data']
                self.logger.info(f"Found {len(actions)} Modbus Actions for signal {signal_name}")
                
                # For each Modbus Action, execute the linked Server Script
                for action in actions:
                    action_name = action.get('name')
                    
                    # Get the full Modbus Action document to find the linked Server Script
                    action_detail_response = self.session.get(
                        f"{self.frappe_url}/api/resource/Modbus Action/{action_name}",
                        timeout=10
                    )
                    action_detail_response.raise_for_status()
                    action_detail = action_detail_response.json().get('data', {})
                    
                    server_script = action_detail.get('server_script')
                    if server_script:
                        self.logger.info(f"Executing Server Script '{server_script}' for Modbus Action '{action_name}'")
                        
                        # Execute the Server Script
                        script_response = self.session.post(
                            f"{self.frappe_url}/api/method/epibus.epibus.doctype.modbus_action.modbus_action.test_action_script",
                            json={
                                "action_name": action_name
                            },
                            timeout=30
                        )
                        
                        if script_response.status_code == 200:
                            self.logger.info(f"Successfully executed Server Script '{server_script}'")
                            
                            # Log action execution event
                            # Extract signal_name and action_name from the API responses
                            signal_name_display = signal_data.get('signal_name', signal_name)
                            action_name_display = action_detail.get('action_name', action_name)
                            
                            action_event = {
                                'event_type': 'Action Execution',
                                'status': 'Success',
                                'signal': signal_name,
                                'signal_name': signal_name_display,
                                'action': action_name,
                                'action_name': action_name_display,
                                'message': f"Executed action {action_name_display} for signal {signal_name_display}",
                                'timestamp': time.time()
                            }
                            self._add_event_to_history(action_event)
                            self.sse_server.publish_event('event_log', action_event)
                        else:
                            error_msg = f"Error executing Server Script '{server_script}': {script_response.text}"
                            self.logger.error(error_msg)
                            
                            # Log action error event
                            # Extract signal_name and action_name from the API responses
                            signal_name_display = signal_data.get('signal_name', signal_name)
                            action_name_display = action_detail.get('action_name', action_name)
                            
                            error_event = {
                                'event_type': 'Action Execution',
                                'status': 'Failed',
                                'signal': signal_name,
                                'signal_name': signal_name_display,
                                'action': action_name,
                                'action_name': action_name_display,
                                'message': f"Failed to execute action {action_name_display} for signal {signal_name_display}",
                                'error_message': error_msg,
                                'timestamp': time.time()
                            }
                            self._add_event_to_history(error_event)
                            self.sse_server.publish_event('event_log', error_event)
                    else:
                        self.logger.warning(f"No Server Script linked to Modbus Action '{action_name}'")
            else:
                self.logger.info(f"No Modbus Actions found for signal {signal_name}")
                
        except Exception as e:
            self.logger.error(f"Error processing actions for signal {signal_name}: {e}")
    
    def _publish_status_update(self):
        """Publish PLC Bridge status update with client check"""
        # Only publish if there are clients connected
        if not self.sse_server.clients:
            return
            
        # Initialize last status update time if it doesn't exist
        if not hasattr(self, '_last_status_update_time'):
            self._last_status_update_time = 0
            
        # Throttle status updates to once every 5 seconds
        now = time.time()
        if now - getattr(self, '_last_status_update_time', 0) < 5.0:
            return
            
        self._last_status_update_time = now
        
        status_data = {
            'connected': self.running,
            'connections': [
                {
                    'name': conn_name,
                    'connected': conn_info['connected'],
                    'last_error': conn_info.get('last_error', None)
                }
                for conn_name, conn_info in self.modbus_clients.items()
            ],
            'timestamp': now
        }
        
        # Publish via SSE
        self.sse_server.publish_event('status_update', status_data)
    
    def start(self):
        """Start the PLC bridge"""
        if self.running:
            self.logger.warning("Bridge already running")
            return
            
        # Check for existing processes using port 7654
        try:
            import socket
            import psutil
            
            # Try to create a socket on port 7654 to check if it's available
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('0.0.0.0', 7654))
            s.close()
            self.logger.info("Port 7654 is available")
        except socket.error:
            self.logger.warning("Port 7654 is already in use, checking for processes")
            
            # Find processes using port 7654
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    for conn in proc.connections(kind='inet'):
                        if conn.laddr.port == 7654:
                            self.logger.warning(f"Process using port 7654: PID={proc.pid}, Name={proc.name()}, Command={' '.join(proc.cmdline())}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except ImportError:
            self.logger.warning("psutil module not available, cannot check for processes using port 7654")
        
        # Load signals
        if not self.load_signals():
            self.logger.error("Failed to load signals - check logs above for details")
            return
        
        # Print initial connection and signal states
        self.logger.info("Initial Modbus Connections:")
        for conn_name, conn_info in self.modbus_clients.items():
            self.logger.info(f"Connection: {conn_name}")
            self.logger.info(f"  Host: {conn_info['host']}:{conn_info['port']}")
            self.logger.info(f"  Connected: {conn_info['connected']}")
        
        self.logger.info("\nInitial Signal States:")
        for signal_name, signal in self.signals.items():
            # Use the _get_connection_name method which now uses caching
            connection_name = self._get_connection_name(signal_name)
            
            # If still no connection, log error
            if not connection_name:
                self.logger.error(f"Cannot determine connection for signal {signal_name}")
                continue
            
            # Read initial signal value
            initial_value = self._read_signal(connection_name, signal)
            
            self.logger.info(f"Signal: {signal.signal_name} ({signal_name})")
            self.logger.info(f"  Connection: {connection_name}")
            self.logger.info(f"  Type: {signal.type}")
            self.logger.info(f"  Address: {signal.address}")
            self.logger.info(f"  Initial Value: {initial_value}")
        
        # Start SSE server
        self.logger.info("Starting SSE server...")
        self.sse_server.start()
        self.logger.info(f"SSE server started on http://{self.sse_server.host}:{self.sse_server.port}")
        
        # Start polling
        self.running = True
        self.poll_thread = threading.Thread(target=self._poll_signals)
        self.poll_thread.daemon = True
        self.poll_thread.start()
        
        # Publish initial status
        self._publish_status_update()
        
        self.logger.info("PLC Bridge started successfully")
    
    def stop(self):
        """Stop the PLC bridge"""
        self.logger.info("Stopping PLC Bridge...")
        
        # Publish final status update
        try:
            self._publish_status_update()
        except Exception as e:
            self.logger.error(f"Error publishing final status update: {e}")
            
        self.running = False
        
        # Stop the polling thread
        if self.poll_thread:
            self.logger.info("Waiting for polling thread to stop...")
            self.poll_thread.join(timeout=3)
            if self.poll_thread.is_alive():
                self.logger.warning("Polling thread did not stop gracefully within timeout")
                # Force terminate if possible
                import ctypes
                try:
                    thread_id = self.poll_thread.ident
                    if thread_id:
                        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                            ctypes.c_long(thread_id),
                            ctypes.py_object(SystemExit)
                        )
                        if res > 1:
                            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
                            self.logger.error("Failed to terminate polling thread")
                except Exception as thread_error:
                    self.logger.error(f"Error terminating polling thread: {thread_error}")
        
        # Stop the SSE server
        try:
            self.logger.info("Stopping SSE server...")
            self.sse_server.stop()
            
            # Verify the port is actually released
            import socket
            import time
            max_retries = 5
            retry_count = 0
            port_released = False
            
            while retry_count < max_retries and not port_released:
                try:
                    # Try to bind to the port to check if it's released
                    # Do not use SO_REUSEADDR to ensure the port is truly available
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.bind(('0.0.0.0', self.sse_server.port))
                    s.close()
                    port_released = True
                    self.logger.info(f"Confirmed port {self.sse_server.port} is released")
                except socket.error:
                    retry_count += 1
                    self.logger.warning(f"Port {self.sse_server.port} still in use, retrying ({retry_count}/{max_retries})...")
                    time.sleep(1)
            
            if not port_released:
                self.logger.error(f"Failed to release port {self.sse_server.port} after {max_retries} attempts")
                self.logger.error("This may cause issues when restarting the PLC Bridge")
                self.logger.error("Please check for any processes still using the port and stop them manually")
                
                # List processes using the port for diagnostic purposes
                import subprocess
                try:
                    self.logger.info(f"Processes using port {self.sse_server.port}:")
                    list_result = subprocess.run(
                        f"lsof -i :{self.sse_server.port}",
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if list_result.stdout:
                        for line in list_result.stdout.splitlines():
                            self.logger.info(line)
                    else:
                        self.logger.info("No processes found using lsof")
                except Exception as list_error:
                    self.logger.error(f"Error listing processes: {list_error}")
                    
        except Exception as e:
            self.logger.error(f"Error stopping SSE server: {e}")
        
        # Disconnect all Modbus clients
        for connection_name, client_info in self.modbus_clients.items():
            if client_info['connected']:
                try:
                    client_info['client'].close()
                    client_info['connected'] = False
                    self.logger.info(f"Disconnected from {connection_name}")
                except Exception as e:
                    self.logger.error(f"Error disconnecting from {connection_name}: {e}")
        
        # Log final shutdown message
        self.logger.info("PLC Bridge stopped successfully")

def main():
    """Entry point for PLC Bridge"""
    parser = argparse.ArgumentParser(description="Standalone PLC Bridge")
    parser.add_argument("--frappe-url", required=True, help="Frappe server URL")
    parser.add_argument("--api-key", required=True, help="Frappe API key")
    parser.add_argument("--api-secret", required=True, help="Frappe API secret")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Signal polling interval")
    
    args = parser.parse_args()
    
    bridge = PLCBridge(
        frappe_url=args.frappe_url,
        api_key=args.api_key,
        api_secret=args.api_secret,
        poll_interval=args.poll_interval
    )
    
    # Set up signal handlers for graceful shutdown
    import signal
    
    def signal_handler(sig, frame):
        print(f"Received signal {sig}, shutting down gracefully...")
        bridge.stop()
        sys.exit(0)
    
    # Register signal handlers for both SIGINT (Ctrl+C) and SIGTERM (kill, supervisor stop)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        bridge.start()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        # This is a fallback in case the signal handler doesn't catch it
        bridge.stop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
        bridge.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()