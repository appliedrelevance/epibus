import json
import time
import redis
import logging
import argparse
from pymodbus.client import ModbusTcpClient
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Union, Tuple
import threading
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("plc_bridge.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("plc_bridge")

@dataclass
class ModbusSignal:
    name: str
    address: int
    type: str
    value: Union[bool, int, float] = None
    last_update: float = 0

class PLCBridge:
    def __init__(self, plc_host: str, plc_port: int, redis_host: str, redis_port: int):
        self.plc_host = plc_host
        self.plc_port = plc_port
        self.redis_host = redis_host
        self.redis_port = redis_port
        
        # Initialize Redis clients
        self.redis_pub = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.redis_sub = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.pubsub = self.redis_sub.pubsub(ignore_subscribe_messages=True)
        
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
        
        logger.info(f"🔧 Initialized PLC Bridge - PLC: {plc_host}:{plc_port}, Redis: {redis_host}:{redis_port}")
    
    def connect(self) -> bool:
        """Connect to the PLC"""
        try:
            if self.modbus_client.connect():
                self.connected = True
                logger.info(f"🔌 Connected to PLC at {self.plc_host}:{self.plc_port}")
                return True
            else:
                logger.error(f"❌ Failed to connect to PLC at {self.plc_host}:{self.plc_port}")
                return False
        except Exception as e:
            logger.error(f"❌ Error connecting to PLC: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from the PLC"""
        try:
            self.modbus_client.close()
            self.connected = False
            logger.info("👋 Disconnected from PLC")
        except Exception as e:
            logger.error(f"❌ Error disconnecting from PLC: {str(e)}")
    
    def load_signals(self):
        """Load signals from Frappe via Redis"""
        try:
            logger.info("🔄 Requesting signals from Frappe...")
            # Request signals from Frappe
            self.redis_pub.publish("plc:command", json.dumps({
                "command": "get_signals"
            }))
            
            # Wait for response (timeout after 10 seconds)
            response = self.redis_pub.blpop("plc:signals", timeout=10)
            
            if not response:
                logger.error("❌ Timeout waiting for signals from Frappe")
                return False
            
            # Parse signals
            signals_data = json.loads(response[1])
            self.signals = {}
            
            for signal_data in signals_data:
                signal = ModbusSignal(
                    name=signal_data["name"],
                    address=signal_data["modbus_address"],
                    type=signal_data["signal_type"]
                )
                self.signals[signal.name] = signal
            
            logger.info(f"✅ Loaded {len(self.signals)} signals from Frappe")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading signals: {str(e)}")
            return False
    
    def start(self):
        """Start the PLC bridge service"""
        if self.running:
            logger.warning("⚠️ PLC Bridge already running")
            return
        
        # Connect to PLC
        if not self.connect():
            logger.error("❌ Cannot start bridge - PLC connection failed")
            return
        
        # Load signals
        if not self.load_signals():
            logger.error("❌ Cannot start bridge - Failed to load signals")
            self.disconnect()
            return
        
        # Set running flag
        self.running = True
        
        # Start subscription thread
        self.subscribe_thread = threading.Thread(target=self._subscribe_worker)
        self.subscribe_thread.daemon = True
        self.subscribe_thread.start()
        
        # Start polling thread
        self.poll_thread = threading.Thread(target=self._poll_worker)
        self.poll_thread.daemon = True
        self.poll_thread.start()
        
        logger.info("🚀 PLC Bridge started successfully")
    
    def stop(self):
        """Stop the PLC bridge service"""
        self.running = False
        
        # Wait for threads to exit
        if self.poll_thread:
            self.poll_thread.join(timeout=2)
        
        if self.subscribe_thread:
            self.subscribe_thread.join(timeout=2)
        
        # Disconnect from PLC
        self.disconnect()
        
        logger.info("🛑 PLC Bridge stopped")
    
    def _read_signal(self, signal: ModbusSignal) -> Union[bool, int, None]:
        """Read a signal value from the PLC"""
        try:
            if signal.type == "Digital Input Contact":
                result = self.modbus_client.read_discrete_inputs(signal.address, 1)
                return result.bits[0] if not result.isError() else None
                
            elif signal.type == "Digital Output Coil":
                result = self.modbus_client.read_coils(signal.address, 1)
                return result.bits[0] if not result.isError() else None
                
            elif signal.type == "Holding Register":
                result = self.modbus_client.read_holding_registers(signal.address, 1)
                return result.registers[0] if not result.isError() else None
                
            elif signal.type == "Analog Input Register":
                result = self.modbus_client.read_input_registers(signal.address, 1)
                return result.registers[0] if not result.isError() else None
            
            else:
                logger.warning(f"⚠️ Unknown signal type: {signal.type}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error reading signal {signal.name}: {str(e)}")
            self.connected = False  # Mark as disconnected to force reconnect
            return None
    
    def _write_signal(self, signal: ModbusSignal, value: Union[bool, int]) -> bool:
        """Write a signal value to the PLC"""
        try:
            if signal.type == "Digital Output Coil":
                result = self.modbus_client.write_coil(signal.address, bool(value))
                success = not result.isError()
                
            elif signal.type == "Holding Register":
                result = self.modbus_client.write_register(signal.address, int(value))
                success = not result.isError()
                
            else:
                logger.warning(f"⚠️ Cannot write to read-only signal type: {signal.type}")
                return False
            
            if success:
                # Update local cache
                signal.value = value
                signal.last_update = time.time()
                logger.info(f"✏️ Wrote {value} to {signal.name}")
                
                # Publish update to Redis
                self._publish_signal_update(signal)
                
                return True
            else:
                logger.error(f"❌ Error writing to {signal.name}: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error writing to signal {signal.name}: {str(e)}")
            self.connected = False  # Mark as disconnected to force reconnect
            return False
    
    def _publish_signal_update(self, signal: ModbusSignal):
        """Publish a signal update to Redis"""
        try:
            # Prepare message
            message = {
                "name": signal.name,
                "value": signal.value,
                "timestamp": signal.last_update
            }
            
            # Publish to Redis
            self.redis_pub.publish("plc:signal_update", json.dumps(message))
            
        except Exception as e:
            logger.error(f"❌ Error publishing signal update: {str(e)}")
    
    def _handle_command(self, message):
        """Handle a command message from Redis"""
        try:
            data = json.loads(message["data"])
            command = data.get("command")
            
            if command == "write_signal":
                signal_name = data.get("signal")
                value = data.get("value")
                
                if signal_name and signal_name in self.signals and value is not None:
                    signal = self.signals[signal_name]
                    self._write_signal(signal, value)
                else:
                    logger.warning(f"⚠️ Invalid write command: {data}")
            
            elif command == "reload_signals":
                self.load_signals()
            
            elif command == "status":
                self._publish_status()
            
            else:
                logger.warning(f"⚠️ Unknown command: {command}")
                
        except Exception as e:
            logger.error(f"❌ Error handling command: {str(e)}")
    
    def _publish_status(self):
        """Publish bridge status to Redis"""
        try:
            # Prepare status message
            status = {
                "connected": self.connected,
                "running": self.running,
                "signal_count": len(self.signals),
                "timestamp": time.time()
            }
            
            # Publish to Redis
            self.redis_pub.publish("plc:status", json.dumps(status))
            
        except Exception as e:
            logger.error(f"❌ Error publishing status: {str(e)}")
    
    def _subscribe_worker(self):
        """Worker thread for Redis subscriptions"""
        logger.info("🔄 Starting subscription worker")
        
        # Subscribe to command channel
        self.pubsub.subscribe("plc:command")
        
        # Process messages
        while self.running:
            try:
                message = self.pubsub.get_message()
                if message and message["type"] == "message":
                    self._handle_command(message)
                
                time.sleep(0.01)  # Small sleep to reduce CPU usage
                
            except Exception as e:
                logger.error(f"❌ Error in subscription worker: {str(e)}")
                time.sleep(1)  # Longer sleep on error
    
    def _poll_worker(self):
        """Worker thread for polling the PLC"""
        logger.info("🔄 Starting polling worker")
        
        poll_interval = 0.05  # 50ms polling interval for <200ms latency
        
        while self.running:
            try:
                # Check connection
                if not self.connected:
                    logger.info("🔄 Reconnecting to PLC...")
                    if not self.connect():
                        time.sleep(1)  # Wait before retry
                        continue
                
                start_time = time.time()
                
                # Group signals by type for batch reading
                coils = {}
                inputs = {}
                holding_regs = {}
                input_regs = {}
                
                for name, signal in self.signals.items():
                    if signal.type == "Digital Output Coil":
                        coils[signal.address] = signal
                    elif signal.type == "Digital Input Contact":
                        inputs[signal.address] = signal
                    elif signal.type == "Holding Register":
                        holding_regs[signal.address] = signal
                    elif signal.type == "Analog Input Register":
                        input_regs[signal.address] = signal
                
                # Process input contacts (optimize for batch reading later)
                for addr, signal in inputs.items():
                    new_value = self._read_signal(signal)
                    if new_value is not None and new_value != signal.value:
                        signal.value = new_value
                        signal.last_update = time.time()
                        self._publish_signal_update(signal)
                
                # Process output coils
                for addr, signal in coils.items():
                    new_value = self._read_signal(signal)
                    if new_value is not None and new_value != signal.value:
                        signal.value = new_value
                        signal.last_update = time.time()
                        self._publish_signal_update(signal)
                
                # Process input registers
                for addr, signal in input_regs.items():
                    new_value = self._read_signal(signal)
                    if new_value is not None and new_value != signal.value:
                        signal.value = new_value
                        signal.last_update = time.time()
                        self._publish_signal_update(signal)
                
                # Process holding registers
                for addr, signal in holding_regs.items():
                    new_value = self._read_signal(signal)
                    if new_value is not None and new_value != signal.value:
                        signal.value = new_value
                        signal.last_update = time.time()
                        self._publish_signal_update(signal)
                
                # Calculate polling time and sleep for the remainder of the interval
                elapsed = time.time() - start_time
                sleep_time = max(0, poll_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                elif elapsed > poll_interval * 2:
                    # If polling takes too long, log a warning
                    logger.warning(f"⚠️ Polling cycle taking too long: {elapsed:.3f}s")
                    
            except Exception as e:
                logger.error(f"❌ Error in polling worker: {str(e)}")
                self.connected = False
                time.sleep(1)  # Wait before retry

def handle_exit(signum, frame):
    """Handle exit signals"""
    logger.info("Received exit signal. Shutting down...")
    if bridge:
        bridge.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="PLC Bridge Service")
    parser.add_argument("--plc-host", default="openplc", help="PLC host address")
    parser.add_argument("--plc-port", type=int, default=502, help="PLC port")
    parser.add_argument("--redis-host", default="localhost", help="Redis host address")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    args = parser.parse_args()
    
    # Create bridge instance
    bridge = PLCBridge(
        plc_host=args.plc_host,
        plc_port=args.plc_port,
        redis_host=args.redis_host,
        redis_port=args.redis_port
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
