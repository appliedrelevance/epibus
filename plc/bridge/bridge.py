#!/usr/bin/env python3
import os
import sys
import time
import logging
import threading
import argparse
import requests
from typing import Dict, List, Union, Optional
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

# Import from local config file
import config

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
        logging.basicConfig(
            level=getattr(logging, config_data["log_level"]),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("plc_bridge.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Session for API calls
        self.session = self._create_authenticated_session()
        
        # Signal management
        self.signals: Dict[str, ModbusSignal] = {}
        
        # Modbus clients for connections
        self.modbus_clients: Dict[str, Dict] = {}
        
        # Control flags
        self.running = False
        self.poll_thread = None
    
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
        """Continuously poll signals and update Frappe"""
        while self.running:
            try:
                # Group signals by connection for efficient polling
                signals_by_connection = {}
                for signal_name, signal in self.signals.items():
                    # Get the connection name from the signal name (parent doctype)
                    parts = signal_name.split("-")
                    if len(parts) >= 2:
                        connection_name = parts[0]
                    else:
                        # Use MCP to get the parent connection
                        try:
                            response = self.session.get(
                                f"{self.frappe_url}/api/resource/Modbus Signal/{signal_name}",
                                timeout=5
                            )
                            response.raise_for_status()
                            data = response.json()
                            connection_name = data.get('data', {}).get('parent')
                        except Exception as e:
                            self.logger.error(f"Error getting connection for signal {signal_name}: {e}")
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
                            signal.value = new_value
                            signal.last_update = time.time()
                            
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
                    self.logger.error(f"Error reading {signal.name}: {result}")
                    return None
                return result.bits[0]
            
            elif signal.type == "Digital Output Coil":
                result = client.read_coils(
                    address=signal.address, count=1)
                if result.isError():
                    self.logger.error(f"Error reading {signal.name}: {result}")
                    return None
                return result.bits[0]
            
            elif signal.type == "Holding Register":
                result = client.read_holding_registers(
                    address=signal.address, count=1)
                if result.isError():
                    self.logger.error(f"Error reading {signal.name}: {result}")
                    return None
                return result.registers[0]
            
            elif signal.type == "Analog Input Register":
                result = client.read_input_registers(
                    address=signal.address, count=1)
                if result.isError():
                    self.logger.error(f"Error reading {signal.name}: {result}")
                    return None
                return result.registers[0]
            
            else:
                self.logger.warning(f"Unknown signal type: {signal.type}")
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
        """Publish a signal update to Frappe"""
        try:
            update_data = {
                'name': signal.name,
                'value': signal.value,
                'timestamp': signal.last_update
            }
            
            response = self.session.post(
                f"{self.frappe_url}/api/method/epibus.api.plc.signal_update", 
                json=update_data,
                timeout=10
            )
            response.raise_for_status()
        
        except Exception as e:
            self.logger.error(f"Error publishing signal update: {e}")
    
    def start(self):
        """Start the PLC bridge"""
        if self.running:
            self.logger.warning("Bridge already running")
            return
        
        # Load signals
        if not self.load_signals():
            self.logger.error("Failed to load signals - check logs above for details")
            return
        
        # Start polling
        self.running = True
        self.poll_thread = threading.Thread(target=self._poll_signals)
        self.poll_thread.daemon = True
        self.poll_thread.start()
        
        self.logger.info("PLC Bridge started successfully")
    
    def stop(self):
        """Stop the PLC bridge"""
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