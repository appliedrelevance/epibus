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
        
        # Configure CORS
        CORS(self.app)
        
        # Set up routes
        self.app.route('/events')(self.sse_stream)
        self.app.route('/signals')(self.get_signals)
        self.app.route('/write_signal', methods=['POST'])(self.write_signal)
        self.app.route('/events/history')(self.get_event_history)
        
    def start(self):
        """Start the SSE server in a separate thread"""
        threading.Thread(target=self.app.run,
                         kwargs={'host': self.host, 'port': self.port, 'threaded': True},
                         daemon=True).start()
        
    def sse_stream(self):
        """SSE stream endpoint"""
        def event_stream():
            client = SSEClient()
            self.clients.add(client)
            try:
                # Send initial connection message
                yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
                
                # Keep connection alive
                while True:
                    if client.has_event():
                        event = client.get_event()
                        yield f"event: {event['type']}\n"
                        yield f"data: {json.dumps(event['data'])}\n\n"
                    else:
                        # Send heartbeat every 30 seconds
                        yield f"event: heartbeat\ndata: {time.time()}\n\n"
                        time.sleep(30)
            except:
                pass
            finally:
                self.clients.remove(client)
                
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
        
    def publish_event(self, event_type, data):
        """Publish an event to all connected clients"""
        for client in self.clients:
            client.add_event({'type': event_type, 'data': data})

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
        # Try method 1: Split by hyphen
        if "-" in signal_name:
            return signal_name.split("-")[0]
        
        # Try method 2: API call to get parent
        try:
            response = self.session.get(
                f"{self.frappe_url}/api/resource/Modbus Signal/{signal_name}",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('parent')
        except Exception:
            pass
        
        # Try method 3: Use first Modbus client as default
        if self.modbus_clients:
            return list(self.modbus_clients.keys())[0]
        
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
        """Connect to a Modbus client"""
        if connection_name not in self.modbus_clients:
            self.logger.error(f"Unknown connection: {connection_name}")
            return False
            
        client_info = self.modbus_clients[connection_name]
        if client_info['connected']:
            return True
            
        try:
            client = client_info['client']
            if client.connect():
                client_info['connected'] = True
                self.logger.info(f"Connected to {connection_name} at {client_info['host']}:{client_info['port']}")
                return True
            else:
                self.logger.error(f"Failed to connect to {connection_name}")
                return False
        except Exception as e:
            self.logger.error(f"Error connecting to {connection_name}: {e}")
            return False
    
    def _poll_signals(self):
        """Continuously poll signals and update via SSE"""
        last_status_update = 0
        status_update_interval = 10  # Send status updates every 10 seconds
        
        while self.running:
            try:
                # Publish status update periodically
                current_time = time.time()
                if current_time - last_status_update > status_update_interval:
                    self._publish_status_update()
                    last_status_update = current_time
                
                # Group signals by connection for efficient polling
                signals_by_connection = {}
                for signal_name, signal in self.signals.items():
                    # Robust connection name extraction
                    connection_name = None
                    
                    # Try method 1: Split by hyphen
                    if "-" in signal_name:
                        connection_name = signal_name.split("-")[0]
                    
                    # Try method 2: API call to get parent
                    if not connection_name:
                        try:
                            response = self.session.get(
                                f"{self.frappe_url}/api/resource/Modbus Signal/{signal_name}",
                                timeout=5
                            )
                            response.raise_for_status()
                            data = response.json()
                            connection_name = data.get('data', {}).get('parent')
                        except Exception as e:
                            self.logger.warning(f"Could not retrieve parent for signal {signal_name}: {e}")
                    
                    # Try method 3: Use first Modbus client as default
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
        """Publish a signal update via SSE"""
        try:
            # Create event data
            update_data = {
                'name': signal.name,
                'signal_name': signal.signal_name,
                'value': signal.value,
                'timestamp': signal.last_update,
                'source': 'plc_bridge'
            }
            
            # Publish via SSE
            self.sse_server.publish_event('signal_update', update_data)
            
            # Log the event
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
            
            # Publish event log via SSE
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
            
            # First, get the signal document to find its ID
            signal_response = self.session.get(
                f"{self.frappe_url}/api/resource/Modbus Signal/{signal_name}",
                timeout=10
            )
            signal_response.raise_for_status()
            signal_data = signal_response.json().get('data', {})
            
            # The signal ID might be in the 'name' field of the signal document
            signal_id = signal_data.get('name')
            if not signal_id:
                self.logger.error(f"Could not determine signal ID for {signal_name}")
                return
            
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
                            action_event = {
                                'event_type': 'Action Execution',
                                'status': 'Success',
                                'signal': signal_name,
                                'action': action_name,
                                'message': f"Executed action {action_name} for signal {signal_name}",
                                'timestamp': time.time()
                            }
                            self._add_event_to_history(action_event)
                            self.sse_server.publish_event('event_log', action_event)
                        else:
                            error_msg = f"Error executing Server Script '{server_script}': {script_response.text}"
                            self.logger.error(error_msg)
                            
                            # Log action error event
                            error_event = {
                                'event_type': 'Action Execution',
                                'status': 'Failed',
                                'signal': signal_name,
                                'action': action_name,
                                'message': f"Failed to execute action {action_name} for signal {signal_name}",
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
        """Publish PLC Bridge status update"""
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
            'timestamp': time.time()
        }
        
        # Publish via SSE
        self.sse_server.publish_event('status_update', status_data)
    
    def start(self):
        """Start the PLC bridge"""
        if self.running:
            self.logger.warning("Bridge already running")
            return
        
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
            # Robust connection name extraction
            connection_name = None
            
            # Try method 1: Split by hyphen
            if "-" in signal_name:
                connection_name = signal_name.split("-")[0]
            
            # Try method 2: API call to get parent
            if not connection_name:
                try:
                    response = self.session.get(
                        f"{self.frappe_url}/api/resource/Modbus Signal/{signal_name}",
                        timeout=5
                    )
                    response.raise_for_status()
                    data = response.json()
                    connection_name = data.get('data', {}).get('parent')
                except Exception as e:
                    self.logger.warning(f"Could not retrieve parent for signal {signal_name}: {e}")
            
            # Try method 3: Use first Modbus client as default
            if not connection_name and self.modbus_clients:
                connection_name = list(self.modbus_clients.keys())[0]
                self.logger.warning(f"Using default connection {connection_name} for signal {signal_name}")
            
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
        # Publish final status update
        try:
            self._publish_status_update()
        except Exception as e:
            self.logger.error(f"Error publishing final status update: {e}")
            
        self.running = False
        
        if self.poll_thread:
            self.poll_thread.join(timeout=2)
        
        # Disconnect all clients
        for connection_name, client_info in self.modbus_clients.items():
            if client_info['connected']:
                try:
                    client_info['client'].close()
                    client_info['connected'] = False
                    self.logger.info(f"Disconnected from {connection_name}")
                except Exception as e:
                    self.logger.error(f"Error disconnecting from {connection_name}: {e}")
        
        # Log final shutdown message
        self.logger.info("PLC Bridge stopped")

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
    
    try:
        bridge.start()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        bridge.stop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
        bridge.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()