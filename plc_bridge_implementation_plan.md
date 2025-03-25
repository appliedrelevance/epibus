# Technical Implementation Plan: Standalone PLC Bridge with REST API

## Objective
Rewrite `plc_redis_client.py` functionality to work directly within the PLC Bridge as a standalone service that communicates with Frappe via REST API instead of using Redis as an intermediary.

## Implementation Steps

### 1. Create Frappe API Client in PLC Bridge

```python
# Add to plc_bridge.py or create new file frappe_api_client.py

import requests
import json
import time
from typing import Dict, Any, Optional, Union
import logging

class FrappeAPIClient:
    """Client for communicating with Frappe REST API"""
    
    def __init__(self, frappe_url: str, api_key: str, api_secret: str):
        self.frappe_url = frappe_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = self._create_authenticated_session()
        self.cache = {}  # Simple cache for API responses
        self.logger = logging.getLogger("plc_bridge.api_client")
        
    def _create_authenticated_session(self):
        """Create an authenticated session for API calls"""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'token {self.api_key}:{self.api_secret}',
            'Content-Type': 'application/json'
        })
        return session
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     retry_count: int = 3, cache_key: Optional[str] = None, 
                     cache_ttl: int = 60) -> Dict[str, Any]:
        """Make an API request with retry logic and caching"""
        # Check cache if this is a GET request and cache_key is provided
        if method == "GET" and cache_key and cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < cache_ttl:
                return cached_data
        
        url = f"{self.frappe_url}{endpoint}"
        
        for attempt in range(retry_count):
            try:
                if method == "GET":
                    response = self.session.get(url, timeout=10)
                elif method == "POST":
                    response = self.session.post(url, json=data, timeout=10)
                elif method == "PUT":
                    response = self.session.put(url, json=data, timeout=10)
                
                response.raise_for_status()  # Raise exception for 4XX/5XX responses
                result = response.json()
                
                # Cache successful GET responses if cache_key is provided
                if method == "GET" and cache_key:
                    self.cache[cache_key] = (result, time.time())
                
                return result
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"API request failed (attempt {attempt+1}/{retry_count}): {str(e)}")
                if attempt == retry_count - 1:
                    # Last attempt failed
                    return {"success": False, "message": f"API request failed: {str(e)}"}
                # Wait before retrying (exponential backoff)
                time.sleep(2 ** attempt)
    
    def get_modbus_settings(self) -> Dict[str, Any]:
        """Get Modbus settings from Frappe"""
        return self._make_request(
            "GET", 
            "/api/method/epibus.api.plc.get_modbus_settings",
            cache_key="modbus_settings",
            cache_ttl=300  # Cache for 5 minutes
        )
    
    def get_all_signals(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get all Modbus signals and connections"""
        if force_refresh:
            # Clear cache if force refresh
            if "all_signals" in self.cache:
                del self.cache["all_signals"]
                
        return self._make_request(
            "GET", 
            "/api/method/epibus.api.plc.get_all_signals",
            cache_key="all_signals",
            cache_ttl=60  # Cache for 1 minute
        )
    
    def signal_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a signal update to Frappe"""
        return self._make_request(
            "POST", 
            "/api/method/epibus.api.plc.signal_update",
            data=data
        )
    
    def write_signal(self, signal_name: str, value: Union[bool, int, float]) -> Dict[str, Any]:
        """Write a signal value via Frappe API"""
        return self._make_request(
            "POST", 
            "/api/method/epibus.api.plc.write_signal",
            data={
                "signal_name": signal_name,
                "value": value
            }
        )
```

### 2. Enhance PLC Bridge to Use API Client

```python
# Modify plc_bridge.py

# Add imports
import requests
from frappe_api_client import FrappeAPIClient

class PLCBridge:
    def __init__(self, plc_host: str, plc_port: int, frappe_url: str, api_key: str, api_secret: str):
        self.plc_host = plc_host
        self.plc_port = plc_port
        
        # Initialize API client
        self.api_client = FrappeAPIClient(frappe_url, api_key, api_secret)
        
        # Initialize Modbus client
        self.modbus_client = ModbusTcpClient(host=plc_host, port=plc_port)
        
        # Signals cache
        self.signals: Dict[str, ModbusSignal] = {}
        
        # Control flags
        self.running = False
        self.connected = False
        
        # Threads
        self.poll_thread = None
        self.subscribe_thread = None
        
        logger.info(f"🔧 Initialized PLC Bridge - PLC: {plc_host}:{plc_port}, Frappe: {frappe_url}")
    
    def load_signals(self):
        """Load signals from Frappe via REST API"""
        try:
            logger.info("🔄 Requesting signals from Frappe...")
            
            # Get signals from Frappe API
            response = self.api_client.get_all_signals()
            
            if not response.get("success"):
                logger.error(f"❌ Error loading signals: {response.get('message')}")
                return False
                
            connections_data = response.get("data", [])
            self.signals = {}
            connection_count = len(connections_data)
            signal_count = 0
            
            # Process each connection and its signals
            for connection in connections_data:
                if "signals" in connection and isinstance(connection["signals"], list):
                    for signal_data in connection["signals"]:
                        signal = ModbusSignal(
                            name=signal_data["name"],
                            address=signal_data["modbus_address"],
                            type=signal_data["signal_type"],
                            signal_name=signal_data.get("signal_name", signal_data["name"])
                        )
                        self.signals[signal.name] = signal
                        signal_count += 1
            
            logger.info(f"✅ Loaded {signal_count} signals from {connection_count} connections")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading signals: {str(e)}")
            return False
    
    def _publish_signal_update(self, signal: ModbusSignal):
        """Publish a signal update to Frappe via REST API"""
        try:
            # Prepare message
            message = {
                "name": signal.name,
                "signal_name": signal.signal_name,
                "value": signal.value,
                "timestamp": signal.last_update
            }
            
            # Send to Frappe API
            response = self.api_client.signal_update(message)
            
            if not response.get("success"):
                logger.error(f"❌ Error publishing signal update: {response.get('message')}")
                
        except Exception as e:
            logger.error(f"❌ Error publishing signal update: {str(e)}")
```

### 3. Update Command Line Arguments

```python
# Modify the argument parser in plc_bridge.py

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="PLC Bridge Service")
    parser.add_argument("--plc-host", default="openplc",
                        help="PLC host address")
    parser.add_argument("--plc-port", type=int, default=502, help="PLC port")
    parser.add_argument("--frappe-url", default="http://localhost:8000",
                        help="Frappe server URL")
    parser.add_argument("--api-key", required=True,
                        help="Frappe API key")
    parser.add_argument("--api-secret", required=True,
                        help="Frappe API secret")
    args = parser.parse_args()
    
    # Create bridge instance
    bridge = PLCBridge(
        plc_host=args.plc_host,
        plc_port=args.plc_port,
        frappe_url=args.frappe_url,
        api_key=args.api_key,
        api_secret=args.api_secret
    )
```

### 4. Add Required API Endpoints to plc.py

```python
# Add to apps/epibus/epibus/api/plc.py

@frappe.whitelist(allow_guest=False)
def get_modbus_settings():
    """Get Modbus settings for the PLC Bridge"""
    try:
        settings = frappe.get_doc("Modbus Settings")
        return {
            "success": True,
            "data": settings.as_dict()
        }
    except Exception as e:
        logger.error(f"Error getting Modbus settings: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=False)
def get_all_signals():
    """Get all signals with their connections in a single call"""
    try:
        # Get enabled Modbus Connections with all fields
        connections = frappe.get_all(
            "Modbus Connection",
            filters={"enabled": 1},
            fields=["name", "device_name", "device_type", "host", "port", "enabled"]
        )
        
        # Initialize connections list with signals
        connection_data = []
        
        # Get signals for each connection
        for conn in connections:
            # Get basic signal information
            conn_signals = frappe.get_all(
                "Modbus Signal",
                filters={"parent": conn.name},
                fields=["name", "signal_name", "signal_type", "modbus_address"]
            )
            
            # Process each signal
            processed_signals = []
            for signal in conn_signals:
                try:
                    # Get the full document to access methods and virtual fields
                    signal_doc = frappe.get_doc("Modbus Signal", signal["name"])
                    
                    # Use the document's read_signal method to get the current value
                    try:
                        value = signal_doc.read_signal()
                        signal["value"] = value
                    except Exception as e:
                        logger.warning(f"⚠️ Error reading signal {signal['signal_name']}: {str(e)}")
                        # Fallback to default values based on signal type
                        signal["value"] = False if "Digital" in signal["signal_type"] else 0
                    
                    # Add the PLC address virtual field
                    signal["plc_address"] = signal_doc.get_plc_address()
                    
                except Exception as e:
                    logger.error(f"❌ Error processing signal {signal['name']}: {str(e)}")
                    # Set default values
                    signal["value"] = False if "Digital" in signal["signal_type"] else 0
                    signal["plc_address"] = None
                
                processed_signals.append(signal)
            
            # Add signals to the connection
            conn_data = conn.copy()
            conn_data["signals"] = processed_signals
            connection_data.append(conn_data)
        
        return {
            "success": True,
            "data": connection_data
        }
    except Exception as e:
        logger.error(f"Error getting all signals: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=False)
def signal_update():
    """Handle a signal update from the PLC Bridge"""
    try:
        data = frappe.local.form_dict
        signal_name = data.get("name")
        value = data.get("value")
        
        if not signal_name or value is None:
            return {"success": False, "message": "Invalid signal update"}
        
        # Get signal document
        if not frappe.db.exists("Modbus Signal", signal_name):
            return {"success": False, "message": f"Signal {signal_name} not found"}
        
        signal = frappe.get_doc("Modbus Signal", signal_name)
        
        # Log the update
        frappe.get_doc({
            "doctype": "Modbus Event",
            "event_type": "Signal Update",
            "connection": signal.parent,
            "signal": signal_name,
            "value": str(value)
        }).insert(ignore_permissions=True)
        
        # Find and process actions triggered by this signal
        actions = frappe.get_all(
            "Modbus Action",
            filters={
                "modbus_signal": signal_name,
                "enabled": 1,
                "trigger_type": "Signal Change"
            },
            fields=["name", "signal_condition", "signal_value", "server_script"]
        )
        
        # Process each action based on condition
        for action in actions:
            try:
                # Check if condition is met
                condition_met = False
                
                if not action.signal_condition or action.signal_condition == "Any Change":
                    condition_met = True
                elif action.signal_condition == "Equals":
                    try:
                        # Handle different value types
                        if isinstance(value, bool):
                            # Boolean comparison
                            target_value = action.signal_value.lower() == "true"
                            condition_met = value == target_value
                        elif "." in action.signal_value:
                            # Float comparison
                            target_value = float(action.signal_value)
                            condition_met = float(value) == target_value
                        else:
                            # Integer comparison
                            target_value = int(action.signal_value)
                            condition_met = int(value) == target_value
                    except (ValueError, TypeError):
                        # Fall back to string comparison
                        condition_met = str(value) == action.signal_value
                elif action.signal_condition == "Greater Than":
                    try:
                        target_value = float(action.signal_value)
                        condition_met = float(value) > target_value
                    except (ValueError, TypeError):
                        pass
                elif action.signal_condition == "Less Than":
                    try:
                        target_value = float(action.signal_value)
                        condition_met = float(value) < target_value
                    except (ValueError, TypeError):
                        pass
                
                # Execute action if condition is met
                if condition_met:
                    # Execute action
                    action_doc = frappe.get_doc("Modbus Action", action.name)
                    if action_doc.server_script:
                        # Execute server script
                        script = frappe.get_doc("Server Script", action_doc.server_script)
                        frappe.safe_exec.safe_exec(
                            script.script,
                            _locals={"signal": signal, "value": value}
                        )
            except Exception as e:
                logger.error(f"❌ Error processing action {action.name}: {str(e)}")
        
        # Broadcast to Frappe real-time
        frappe.publish_realtime(
            event='modbus_signal_update',
            message={
                'signal': signal_name,
                'signal_name': signal.signal_name,
                'value': value,
                'timestamp': data.get("timestamp", time.time())
            }
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error handling signal update: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=False)
def write_signal():
    """Write a signal value from the PLC Bridge"""
    try:
        # Get parameters
        signal_name = frappe.local.form_dict.get('signal_name')
        value = frappe.local.form_dict.get('value')
        
        if not signal_name or value is None:
            return {"success": False, "message": "Missing signal_name or value"}
        
        # Get signal document
        if not frappe.db.exists("Modbus Signal", signal_name):
            return {"success": False, "message": f"Signal {signal_name} not found"}
        
        signal = frappe.get_doc("Modbus Signal", signal_name)
        
        # Check if writable
        if not ("Output" in signal.signal_type or "Register" in signal.signal_type):
            return {"success": False, "message": f"Cannot write to read-only signal: {signal_name}"}
        
        # Parse value based on signal type
        if "Digital" in signal.signal_type:
            # Parse digital values
            from epibus.epibus.utils.truthy import truthy, parse_value
            parsed_value = parse_value(value)
            if not isinstance(parsed_value, bool):
                parsed_value = truthy(parsed_value)
        else:
            # For non-digital values, convert to float
            try:
                parsed_value = float(value)
            except (ValueError, TypeError):
                return {"success": False, "message": f"Cannot convert {value} to a number"}
        
        # Write signal using the document's method
        success = signal.write_signal(parsed_value)
        
        if success:
            # Broadcast to Frappe real-time
            frappe.publish_realtime(
                event='modbus_signal_update',
                message={
                    'signal': signal_name,
                    'signal_name': signal.signal_name,
                    'value': parsed_value,
                    'timestamp': time.time(),
                    'source': 'write_request'
                }
            )
            
            return {"success": True, "message": f"Updated signal {signal.signal_name}"}
        else:
            return {"success": False, "message": f"Failed to update signal {signal.signal_name}"}
        
    except Exception as e:
        logger.error(f"Error writing signal: {str(e)}")
        return {"success": False, "message": str(e)}
```

### 5. Create Configuration File for PLC Bridge

```python
# Create plc_bridge_config.py

import os
import json

def load_config(config_file=None):
    """Load configuration from file or environment variables"""
    config = {
        "plc_host": "openplc",
        "plc_port": 502,
        "frappe_url": "http://localhost:8000",
        "api_key": None,
        "api_secret": None,
        "log_level": "INFO"
    }
    
    # Try to load from config file
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
    
    # Override with environment variables if present
    if os.environ.get("PLC_HOST"):
        config["plc_host"] = os.environ.get("PLC_HOST")
    if os.environ.get("PLC_PORT"):
        config["plc_port"] = int(os.environ.get("PLC_PORT"))
    if os.environ.get("FRAPPE_URL"):
        config["frappe_url"] = os.environ.get("FRAPPE_URL")
    if os.environ.get("FRAPPE_API_KEY"):
        config["api_key"] = os.environ.get("FRAPPE_API_KEY")
    if os.environ.get("FRAPPE_API_SECRET"):
        config["api_secret"] = os.environ.get("FRAPPE_API_SECRET")
    if os.environ.get("LOG_LEVEL"):
        config["log_level"] = os.environ.get("LOG_LEVEL")
    
    return config
```

### 6. Update Main Entry Point

```python
# Update main entry point in plc_bridge.py

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="PLC Bridge Service")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--plc-host", help="PLC host address")
    parser.add_argument("--plc-port", type=int, help="PLC port")
    parser.add_argument("--frappe-url", help="Frappe server URL")
    parser.add_argument("--api-key", help="Frappe API key")
    parser.add_argument("--api-secret", help="Frappe API secret")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level")
    args = parser.parse_args()
    
    # Load configuration
    from plc_bridge_config import load_config
    config = load_config(args.config)
    
    # Override config with command line arguments if provided
    if args.plc_host:
        config["plc_host"] = args.plc_host
    if args.plc_port:
        config["plc_port"] = args.plc_port
    if args.frappe_url:
        config["frappe_url"] = args.frappe_url
    if args.api_key:
        config["api_key"] = args.api_key
    if args.api_secret:
        config["api_secret"] = args.api_secret
    if args.log_level:
        config["log_level"] = args.log_level
    
    # Configure logging
    log_level = getattr(logging, config["log_level"])
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("plc_bridge.log"),
            logging.StreamHandler()
        ]
    )
    
    # Validate required configuration
    if not config["api_key"] or not config["api_secret"]:
        logger.error("API key and secret are required")
        sys.exit(1)
    
    # Create bridge instance
    bridge = PLCBridge(
        plc_host=config["plc_host"],
        plc_port=config["plc_port"],
        frappe_url=config["frappe_url"],
        api_key=config["api_key"],
        api_secret=config["api_secret"]
    )
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    try:
        # Start the bridge
        bridge.start()
        
        # Main thread can just sleep
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        bridge.stop()
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        bridge.stop()
```

### 7. Create API Key in Frappe

1. Log in to Frappe as Administrator
2. Go to User list
3. Create a new User named "PLC Bridge" if it doesn't exist
4. Set appropriate permissions for the user
5. Go to "My Settings" for this user
6. Scroll down to "API Access" section
7. Click "Generate Keys"
8. Save the API key and secret for use in PLC Bridge configuration

### 8. Test and Deploy

1. Run the PLC Bridge with the new configuration:
   ```
   python plc_bridge.py --config plc_bridge_config.json
   ```

2. Monitor logs for any errors
   ```
   tail -f plc_bridge.log
   ```

3. Test signal updates and actions