import frappe
import time
import json
from pymodbus.client import ModbusTcpClient
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union

@dataclass
class ModbusSignal:
    name: str
    address: int
    type: str
    signal_name: Optional[str] = None
    value: Optional[Union[bool, int, float]] = None
    last_update: float = 0

class PLCWorker:
    """PLC Worker that runs within Frappe's worker system"""
    
    def __init__(self):
        self.plc_host = None
        self.plc_port = None
        self.modbus_client = None
        self.signals = {}
        self.connected = False
        self.last_status_time = 0
        
    def initialize(self):
        """Initialize the PLC worker with settings from Frappe"""
        try:
            # Try to get settings from Modbus Settings doctype
            settings = frappe.get_doc("Modbus Settings")
            self.plc_host = settings.get("plc_host", "192.168.0.11")
            self.plc_port = settings.get("plc_port", 502)
        except Exception as e:
            # If there's an error, use default settings
            frappe.logger().warning(f"⚠️ Error loading Modbus Settings: {str(e)}")
            frappe.logger().info("⚠️ Using default PLC settings")
            self.plc_host = "192.168.0.11"
            self.plc_port = 502
        
        # Initialize Modbus client
        self.modbus_client = ModbusTcpClient(host=self.plc_host, port=self.plc_port)
        
        # Load signals
        self.load_signals()
        
        frappe.logger().info(f"🔧 Initialized PLC Worker - PLC: {self.plc_host}:{self.plc_port}")
        
    def connect(self) -> bool:
        """Connect to the PLC"""
        try:
            if self.modbus_client.connect():
                self.connected = True
                frappe.logger().info(f"🔌 Connected to PLC at {self.plc_host}:{self.plc_port}")
                return True
            else:
                frappe.logger().error(f"❌ Failed to connect to PLC at {self.plc_host}:{self.plc_port}")
                return False
        except Exception as e:
            frappe.logger().error(f"❌ Error connecting to PLC: {str(e)}")
            return False
            
    def disconnect(self):
        """Disconnect from the PLC"""
        try:
            self.modbus_client.close()
            self.connected = False
            frappe.logger().info("👋 Disconnected from PLC")
        except Exception as e:
            frappe.logger().error(f"❌ Error disconnecting from PLC: {str(e)}")
            
    def load_signals(self):
        """Load signals from Frappe database"""
        try:
            # Get enabled Modbus Connections with all fields
            connections = frappe.get_all(
                "Modbus Connection",
                filters={"enabled": 1},
                fields=["name", "device_name", "device_type", "host", "port", "enabled"]
            )
            
            # Reset signals dictionary
            self.signals = {}
            
            # Get signals for each connection
            for conn in connections:
                # Get basic signal information
                conn_signals = frappe.get_all(
                    "Modbus Signal",
                    filters={"parent": conn.name},
                    fields=["name", "signal_name", "signal_type", "modbus_address"]
                )
                
                # Process each signal
                for signal_data in conn_signals:
                    signal = ModbusSignal(
                        name=signal_data["name"],
                        address=signal_data["modbus_address"],
                        type=signal_data["signal_type"],
                        signal_name=signal_data.get("signal_name", signal_data["name"])
                    )
                    self.signals[signal.name] = signal
                    
            frappe.logger().info(f"✅ Loaded {len(self.signals)} signals")
            return True
            
        except Exception as e:
            frappe.logger().error(f"❌ Error loading signals: {str(e)}")
            return False
            
    def _read_signal(self, signal: ModbusSignal) -> Union[bool, int, None]:
        """Read a signal value from the PLC"""
        try:
            if signal.type == "Digital Input Contact":
                result = self.modbus_client.read_discrete_inputs(
                    address=signal.address, count=1)
                return result.bits[0] if not result.isError() else None
                
            elif signal.type == "Digital Output Coil":
                result = self.modbus_client.read_coils(
                    address=signal.address, count=1)
                return result.bits[0] if not result.isError() else None
                
            elif signal.type == "Holding Register":
                result = self.modbus_client.read_holding_registers(
                    address=signal.address, count=1)
                return result.registers[0] if not result.isError() else None
                
            elif signal.type == "Analog Input Register":
                result = self.modbus_client.read_input_registers(
                    address=signal.address, count=1)
                return result.registers[0] if not result.isError() else None
                
            else:
                frappe.logger().warning(f"⚠️ Unknown signal type: {signal.type}")
                return None
                
        except Exception as e:
            frappe.logger().error(f"❌ Error reading signal {signal.name}: {str(e)}")
            self.connected = False  # Mark as disconnected to force reconnect
            return None
            
    def _write_signal(self, signal: ModbusSignal, value: Union[bool, int]) -> bool:
        """Write a signal value to the PLC"""
        try:
            if signal.type == "Digital Output Coil":
                result = self.modbus_client.write_coil(
                    address=signal.address, value=bool(value))
                success = not result.isError()
                
            elif signal.type == "Holding Register":
                result = self.modbus_client.write_register(
                    address=signal.address, value=int(value))
                success = not result.isError()
                
            else:
                frappe.logger().warning(f"⚠️ Cannot write to read-only signal type: {signal.type}")
                return False
                
            if success:
                # Update local cache
                signal.value = value
                signal.last_update = time.time()
                frappe.logger().info(f"✏️ Wrote {value} to {signal.name}")
                
                # Publish update via Frappe's realtime
                self._publish_signal_update(signal)
                
                return True
            else:
                frappe.logger().error(f"❌ Error writing to {signal.name}: {result}")
                return False
                
        except Exception as e:
            frappe.logger().error(f"❌ Error writing to signal {signal.name}: {str(e)}")
            self.connected = False  # Mark as disconnected to force reconnect
            return False
            
    def _publish_signal_update(self, signal: ModbusSignal):
        """Publish a signal update via Frappe's realtime system"""
        try:
            # Prepare message
            message = {
                "name": signal.name,
                "signal": signal.name,  # For compatibility with existing frontend
                "signal_name": signal.signal_name,
                "value": signal.value,
                "timestamp": signal.last_update
            }
            
            # Publish via Frappe's realtime system
            frappe.publish_realtime(
                event='modbus_signal_update',
                message=message
            )
            
        except Exception as e:
            frappe.logger().error(f"❌ Error publishing signal update: {str(e)}")
            
    def _publish_status(self):
        """Publish bridge status via Frappe's realtime system"""
        try:
            # Prepare status message
            status = {
                "connected": self.connected,
                "signal_count": len(self.signals),
                "timestamp": time.time()
            }
            
            # Publish via Frappe's realtime system
            frappe.publish_realtime(
                event='plc:status',
                message=status
            )
            
            frappe.logger().info(f"✅ Published PLC Worker status")
            
        except Exception as e:
            frappe.logger().error(f"❌ Error publishing status: {str(e)}")
            
    def poll_signals(self):
        """Poll signals from the PLC"""
        try:
            # Check connection
            if not self.connected:
                frappe.logger().info("🔄 Reconnecting to PLC...")
                if not self.connect():
                    time.sleep(1)  # Wait before retry
                    return
                    
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
                    
            # Process input contacts
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
                    
            # Check if we should publish status (every 10 seconds)
            current_time = time.time()
            if current_time - self.last_status_time > 10:
                self._publish_status()
                self.last_status_time = current_time
                
            # Calculate polling time
            elapsed = time.time() - start_time
            if elapsed > 0.2:  # If polling takes too long, log a warning
                frappe.logger().warning(f"⚠️ Polling cycle taking too long: {elapsed:.3f}s")
                
        except Exception as e:
            frappe.logger().error(f"❌ Error in polling: {str(e)}")
            self.connected = False
            
    def handle_command(self, command_data):
        """Handle a command from Frappe"""
        try:
            command = command_data.get("command")
            
            if command == "write_signal":
                signal_name = command_data.get("signal")
                value = command_data.get("value")
                
                if signal_name and signal_name in self.signals and value is not None:
                    signal = self.signals[signal_name]
                    self._write_signal(signal, value)
                else:
                    frappe.logger().warning(f"⚠️ Invalid write command: {command_data}")
                    
            elif command == "reload_signals":
                self.load_signals()
                
            elif command == "status":
                self._publish_status()
                
            else:
                frappe.logger().warning(f"⚠️ Unknown command: {command}")
                
        except Exception as e:
            frappe.logger().error(f"❌ Error handling command: {str(e)}")