#!/usr/bin/env python3
"""
Simplified PLC Bridge - No complexity, just basic functionality

This replaces the overly complex bridge.py with:
- Simple 3-second polling loop
- No retry logic, no exponential backoff
- No SSE - just HTTP polling
- Basic error handling - if something fails, try again next cycle
"""

import os
import sys
import time
import logging
import threading
import requests
import json
from typing import Dict, List, Union, Optional
from pymodbus.client import ModbusTcpClient
from flask import Flask, Response, jsonify, request
from flask_cors import CORS

class SimplePLCBridge:
    """Dead simple PLC Bridge - no complexity"""
    
    def __init__(self, frappe_url: str, poll_interval: float = 3.0):
        self.frappe_url = frappe_url
        self.poll_interval = poll_interval
        
        # Simple logging with debug enabled
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Current signal values - just a simple dict
        self.current_signals = {}
        self.last_values = {}
        
        # MODBUS connections - just store what we need
        self.connections = {}
        
        # Connection status tracking
        self.connection_status = {}
        
        # Simple Flask app for the dashboard
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Set up routes
        self.app.route('/')(self.dashboard)
        self.app.route('/signals')(self.get_signals) 
        self.app.route('/connections')(self.get_connections)
        self.app.route('/write_signal', methods=['POST'])(self.write_signal)
        
        # Control flags
        self.running = False
        self.poll_thread = None
        self.flask_thread = None
    
    def load_signals_from_frappe(self):
        """Load signal definitions from Frappe - simple, no retry logic"""
        try:
            self.logger.info("Loading signals from Frappe...")
            response = requests.get(
                f"{self.frappe_url}/api/method/epibus.api.plc.get_signals",
                headers={'Host': 'intralogistics.lab'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Handle Frappe's response format
            if 'message' in data:
                if isinstance(data['message'], list):
                    # Direct list format
                    connections_data = data['message']
                elif isinstance(data['message'], dict) and data['message'].get('success') and 'data' in data['message']:
                    # Wrapped format with success/data
                    connections_data = data['message']['data']
                else:
                    self.logger.error(f"Frappe API error: {data['message']}")
                    return False
            else:
                self.logger.error(f"Unexpected response format: {data}")
                return False
            
            # Process connections and signals
            self.connections = {}
            self.current_signals = {}
            
            for conn_data in connections_data:
                conn_name = conn_data['name']
                host = conn_data['host']
                port = conn_data['port']
                
                self.connections[conn_name] = {
                    'host': host,
                    'port': port,
                    'client': None
                }
                
                # Process signals for this connection
                for signal_data in conn_data.get('signals', []):
                    signal_id = signal_data['name']
                    self.current_signals[signal_id] = {
                        'name': signal_id,
                        'signal_name': signal_data['signal_name'],
                        'type': signal_data['signal_type'],
                        'address': signal_data['modbus_address'],
                        'connection': conn_name,
                        'value': None,
                        'timestamp': None
                    }
            
            self.logger.info(f"Loaded {len(self.current_signals)} signals from {len(self.connections)} connections")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load signals: {e}")
            return False
    
    def get_modbus_client(self, connection_name):
        """Get a MODBUS client - simplified version that actually works"""
        if connection_name not in self.connections:
            self.logger.error(f"Unknown connection: {connection_name}")
            return None
        
        conn = self.connections[connection_name]
        
        # Always create a fresh client - don't reuse connections
        self.logger.debug(f"Creating fresh MODBUS client for {connection_name} at {conn['host']}:{conn['port']}")
        client = ModbusTcpClient(host=conn['host'], port=conn['port'], timeout=5)
        
        # Try to connect
        try:
            if client.connect():
                self.logger.debug(f"Successfully connected to {connection_name}")
                return client
            else:
                self.logger.error(f"Connection to {connection_name} ({conn['host']}:{conn['port']}) failed")
                return None
        except Exception as e:
            self.logger.error(f"Exception connecting to {connection_name}: {e}")
            return None
    
    def read_signal_value(self, signal):
        """Read a single signal value - simple, no complex error handling"""
        client = None
        try:
            client = self.get_modbus_client(signal['connection'])
            if client is None:
                return None
            
            address = signal['address']
            signal_type = signal['type']
            
            # Read based on signal type
            result = None
            if signal_type == "Digital Input Contact":
                result = client.read_discrete_inputs(address=address, count=1)
                if not result.isError():
                    value = result.bits[0]
                    self.logger.debug(f"Read {signal['signal_name']} at {address}: {value}")
                    return value
            elif signal_type == "Digital Output Coil":
                result = client.read_coils(address=address, count=1)
                if not result.isError():
                    value = result.bits[0]
                    self.logger.debug(f"Read {signal['signal_name']} at {address}: {value}")
                    return value
            elif signal_type == "Input Register":
                result = client.read_input_registers(address=address, count=1)
                if not result.isError():
                    value = result.registers[0]
                    self.logger.debug(f"Read {signal['signal_name']} at {address}: {value}")
                    return value
            elif signal_type == "Holding Register":
                result = client.read_holding_registers(address=address, count=1)
                if not result.isError():
                    value = result.registers[0]
                    self.logger.debug(f"Read {signal['signal_name']} at {address}: {value}")
                    return value
            
            if result and result.isError():
                self.logger.error(f"MODBUS read error for {signal['signal_name']} at {address}: {result}")
            else:
                self.logger.error(f"Unknown signal type {signal_type} for {signal['signal_name']}")
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Exception reading {signal['signal_name']}: {e}")
            return None
        finally:
            # Always close the client connection
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def send_signal_change_to_frappe(self, signal_id, old_value, new_value):
        """Send signal change to Frappe - simple, no complex retry"""
        try:
            data = {
                'name': signal_id,
                'value': new_value,
                'timestamp': time.time()
            }
            
            response = requests.post(
                f"{self.frappe_url}/api/method/epibus.api.plc.signal_update",
                json=data,
                headers={'Host': 'intralogistics.lab'},
                timeout=5
            )
            
            if response.status_code == 200:
                self.logger.info(f"Sent signal change: {self.current_signals[signal_id]['signal_name']} = {new_value}")
            else:
                self.logger.warning(f"Failed to send signal change: HTTP {response.status_code}")
                
        except Exception as e:
            self.logger.warning(f"Failed to send signal change: {e}")
    
    def polling_loop(self):
        """Simple polling loop - no complexity"""
        self.logger.info("Starting simple polling loop...")
        
        while self.running:
            try:
                # Read all signals
                changes = []
                
                for signal_id, signal in self.current_signals.items():
                    new_value = self.read_signal_value(signal)
                    self.logger.debug(f"Read signal {signal['signal_name']} ({signal_id}): {new_value}")
                    
                    if new_value is not None:
                        old_value = signal['value']
                        
                        # Always update timestamp when we get a successful read
                        signal['value'] = new_value
                        signal['timestamp'] = time.time()
                        
                        # Check for changes and notify Frappe
                        if new_value != old_value:
                            changes.append((signal_id, old_value, new_value))
                            
                            # Send to Frappe
                            self.send_signal_change_to_frappe(signal_id, old_value, new_value)
                    else:
                        self.logger.warning(f"Failed to read signal {signal['signal_name']} ({signal_id})")
                
                if changes:
                    self.logger.info(f"Processed {len(changes)} signal changes")
                
                # Sleep and repeat
                time.sleep(self.poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                time.sleep(self.poll_interval)  # Just try again
    
    def start(self):
        """Start the bridge"""
        self.logger.info("Starting Simple PLC Bridge...")
        
        # Load signals from Frappe
        if not self.load_signals_from_frappe():
            self.logger.error("Failed to load signals - cannot start")
            return False
        
        # Start polling thread
        self.running = True
        self.poll_thread = threading.Thread(target=self.polling_loop, daemon=True)
        self.poll_thread.start()
        
        # Start Flask server in separate thread
        self.flask_thread = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=7654, debug=False, use_reloader=False),
            daemon=True
        )
        self.flask_thread.start()
        
        self.logger.info("Simple PLC Bridge started successfully")
        return True
    
    def stop(self):
        """Stop the bridge"""
        self.logger.info("Stopping Simple PLC Bridge...")
        self.running = False
        
        # Close MODBUS connections
        for conn in self.connections.values():
            if conn['client']:
                try:
                    conn['client'].close()
                except:
                    pass
    
    # ========== FLASK ROUTES ==========
    
    def get_signals(self):
        """API endpoint to get all current signal values"""
        signals_list = []
        current_time = time.time()
        
        for signal in self.current_signals.values():
            # Only return values that are fresh (within last poll cycle + 1 second buffer)
            # If no timestamp or too old, return None instead of stale values
            value = signal['value']
            timestamp = signal['timestamp']
            
            # Fresh means within the last poll interval + longer buffer for debugging  
            max_age = self.poll_interval + 10.0
            
            if timestamp is None or (current_time - timestamp) > max_age:
                value = None  # Don't lie - return None for stale/unknown values
                
            signals_list.append({
                'name': signal['name'],
                'signal_name': signal['signal_name'],
                'value': value,
                'timestamp': timestamp,
                'address': signal.get('address', '--'),
                'signal_type': signal.get('type', 'UNKNOWN')
            })
        
        return jsonify({'signals': signals_list})
    
    def write_signal(self):
        """API endpoint to write a signal value"""
        try:
            data = request.get_json()
            signal_id = data.get('signal_id')
            value = data.get('value')
            
            if signal_id not in self.current_signals:
                return jsonify({'success': False, 'message': 'Signal not found'}), 404
            
            signal = self.current_signals[signal_id]
            client = self.get_modbus_client(signal['connection'])
            
            if client is None:
                return jsonify({'success': False, 'message': 'Connection failed'}), 500
            
            # Write the signal
            address = signal['address']
            signal_type = signal['type']
            
            try:
                if signal_type == "Digital Output Coil":
                    result = client.write_coil(address, bool(value))
                elif signal_type == "Holding Register":
                    result = client.write_register(address, int(value))
                else:
                    return jsonify({'success': False, 'message': f'Cannot write to {signal_type}'}), 400
                
                if result.isError():
                    return jsonify({'success': False, 'message': f'MODBUS write error: {result}'}), 500
                
                # Update our local copy
                signal['value'] = value
                signal['timestamp'] = time.time()
                
                return jsonify({'success': True, 'message': f'Signal {signal["signal_name"]} updated'})
                
            except Exception as e:
                return jsonify({'success': False, 'message': f'Write failed: {e}'}), 500
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Request error: {e}'}), 400
    
    def dashboard(self):
        """Simple dashboard - no SSE complexity"""
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple PLC Bridge Dashboard</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            margin: 0; padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #2c3e50; line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            text-align: center; margin-bottom: 30px; background: white;
            padding: 30px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .header h1 { margin: 0; color: #2c3e50; font-size: 2.5em; font-weight: 300; }
        .header p { margin: 10px 0 0 0; color: #7f8c8d; font-size: 1.1em; }
        .info {
            background: white; border-radius: 15px; padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-bottom: 30px;
        }
        .signals-table {
            width: 100%; border-collapse: collapse; background: white;
            border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .signals-table th {
            background: #f8f9fa; padding: 12px 16px; text-align: left;
            border-bottom: 2px solid #dee2e6; font-weight: 600; color: #495057;
        }
        .signals-table td {
            padding: 12px 16px; border-bottom: 1px solid #dee2e6;
            vertical-align: middle;
        }
        .signals-table tr:hover {
            background: #f8f9fa;
        }
        .signal-value {
            display: inline-block; padding: 6px 12px; border-radius: 20px;
            font-weight: 600; font-family: monospace; min-width: 60px; text-align: center;
        }
        .value-true {
            background: #d4edda; color: #155724; border: 1px solid #c3e6cb;
        }
        .value-false {
            background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;
        }
        .value-null {
            background: #fff3cd; color: #856404; border: 1px solid #ffeeba;
        }
        .value-numeric {
            background: #e3f2fd; color: #0d47a1; border: 1px solid #bbdefb;
        }
        .refresh-info { text-align: center; margin-top: 20px; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 Simple PLC Bridge Dashboard</h1>
            <p>No SSE, No Complexity - Just Simple HTTP Polling</p>
        </div>

        <div class="info">
            <h3>📊 System Info</h3>
            <div>Signals: <span id="signal-count">0</span></div>
            <div>Last Update: <span id="last-update">Never</span></div>
            <div>Status: <span id="status">Loading...</span></div>
        </div>

        <div class="info">
            <h3>⚡ Live Signals</h3>
            <table class="signals-table">
                <thead>
                    <tr>
                        <th>Signal Name</th>
                        <th>Type</th>
                        <th>Address</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody id="signals"></tbody>
            </table>
        </div>
        
        <div class="refresh-info">
            Dashboard refreshes every 3 seconds via simple HTTP polling
        </div>
    </div>

    <script>
        function updateSignals() {
            fetch('/signals')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('signals');
                    const signals = data.signals || [];
                    
                    container.innerHTML = signals.map(signal => {
                        // All OpenPLC signals are BOOL
                        const signalType = 'BOOL';
                        
                        // Display value based on actual value
                        let displayValue, valueClass;
                        if (signal.value === null || signal.value === undefined) {
                            displayValue = 'NULL';
                            valueClass = 'value-null';
                        } else if (signal.value === true) {
                            displayValue = 'TRUE';
                            valueClass = 'value-true';
                        } else if (signal.value === false) {
                            displayValue = 'FALSE';
                            valueClass = 'value-false';
                        } else {
                            // Fallback for any unexpected values
                            displayValue = signal.value.toString();
                            valueClass = 'value-numeric';
                        }
                        
                        // Use placeholder address for now - we'd need to get this from Frappe
                        const address = signal.address || '--';
                        
                        return `
                            <tr>
                                <td><strong>${signal.signal_name || signal.name}</strong></td>
                                <td>${signalType}</td>
                                <td>${address}</td>
                                <td><span class="signal-value ${valueClass}">${displayValue}</span></td>
                            </tr>
                        `;
                    }).join('');
                    
                    document.getElementById('signal-count').textContent = signals.length;
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                    document.getElementById('status').textContent = 'Connected';
                })
                .catch(error => {
                    document.getElementById('status').textContent = 'Connection Error';
                    console.error('Error:', error);
                });
        }
        
        // Update immediately and then every 3 seconds
        updateSignals();
        setInterval(updateSignals, 3000);
    </script>
</body>
</html>'''
        return html


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple PLC Bridge")
    parser.add_argument("--frappe-url", default="http://backend:8000", help="Frappe server URL")
    parser.add_argument("--poll-interval", type=float, default=3.0, help="Polling interval in seconds")
    
    args = parser.parse_args()
    
    bridge = SimplePLCBridge(
        frappe_url=args.frappe_url,
        poll_interval=args.poll_interval
    )
    
    # Signal handlers
    import signal
    def signal_handler(sig, frame):
        print("Shutting down...")
        bridge.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if bridge.start():
            print("Simple PLC Bridge running on http://localhost:7654")
            # Keep main thread alive
            while True:
                time.sleep(1)
        else:
            print("Failed to start bridge")
            sys.exit(1)
    
    except KeyboardInterrupt:
        bridge.stop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
        bridge.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()