import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient
from pymodbus.framer import FramerType
from epibus.epibus.utils.epinomy_logger import get_logger
import asyncio
from contextlib import contextmanager
from typing import Optional, Any, Callable
from enum import Enum

logger = get_logger(__name__)

class SignalType(Enum):
    DIGITAL_OUTPUT = "Digital Output Coil"
    DIGITAL_INPUT = "Digital Input Contact" 
    ANALOG_INPUT = "Analog Input Register"
    HOLDING_REGISTER = "Holding Register"

class SignalHandler:
    def __init__(self, client: ModbusTcpClient):
        self.client = client
        self.handlers = {
            SignalType.DIGITAL_OUTPUT: (
                lambda addr: self.client.read_coils(address=addr, count=1), 
                lambda addr, val: self.client.write_coil(address=addr, value=val),
                bool
            ),
            SignalType.DIGITAL_INPUT: (
                lambda addr: self.client.read_discrete_inputs(address=addr, count=1),
                None,
                bool
            ),
            SignalType.ANALOG_INPUT: (
                lambda addr: self.client.read_input_registers(address=addr, count=1),
                None,
                float
            ),
            SignalType.HOLDING_REGISTER: (
                lambda addr: self.client.read_holding_registers(address=addr, count=1),
                lambda addr, val: self.client.write_register(address=addr, value=val),
                float
            )
        }

    def get_handler(self, signal_type: str) -> tuple[Callable, Optional[Callable], type]:
        for sig_type in SignalType:
            if sig_type.value in signal_type:
                return self.handlers[sig_type]
        raise ValueError(f"Unsupported signal type: {signal_type}")

    def read(self, signal_type: str, address: int) -> Any:
        read_fn, _, conv_fn = self.get_handler(signal_type)
        response = read_fn(address)
        return conv_fn(response.bits[0] if hasattr(response, 'bits') else response.registers[0])

    def write(self, signal_type: str, address: int, value: Any) -> None:
        _, write_fn, conv_fn = self.get_handler(signal_type)
        if not write_fn:
            raise ValueError(f"Cannot write to signal type: {signal_type}")
        write_fn(address, conv_fn(value))

class ModbusDevice(Document):
    def validate(self):
        self.validate_connection_settings()
        
    def validate_connection_settings(self):
        if not (1 <= self.port <= 65535):
            frappe.throw("Port must be between 1 and 65535")

    @contextmanager
    def get_client(self):
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        client = ModbusTcpClient(
            host=self.host,
            port=self.port,
            framer=FramerType.SOCKET,
            timeout=10
        )
        
        try:
            if not client.connect():
                raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")
            yield client
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass

    def _build_results_table(self, results: list) -> str:
        """Build HTML table for connection test results
        
        Args:
            results: List of dicts with signal test results
            
        Returns:
            Formatted HTML table string
        """
        html = """
        <div style="margin: 10px 0;">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Signal Name</th>
                        <th>Type</th> 
                        <th>Address</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for result in results:
            html += f"""
                <tr>
                    <td>{result['signal_name']}</td>
                    <td>{result['type']}</td>
                    <td>{result['address']}</td>
                    <td>
                        <span class="indicator {result['indicator']}">
                            {result['state']}
                        </span>
                    </td>
                </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        return html

    @frappe.whitelist()
    def test_connection(self):
        """Test connection to device"""
        logger.info(f"Testing connection to device {self.device_name} at {self.host}:{self.port}")
        
        try:
            with self.get_client() as client:
                handler = SignalHandler(client)
                results = []
                
                # Collect results
                for signal in self.signals:
                    try:
                        value = handler.read(signal.signal_type, signal.modbus_address)
                        
                        if isinstance(value, bool):
                            signal.boolean_value = value
                            state = "On" if value else "Off"
                            indicator_color = "green" if value else "gray"
                        else:
                            signal.current_value = value
                            state = str(value)
                            indicator_color = "blue"
                            
                        results.append({
                            "signal_name": signal.signal_name,
                            "type": signal.signal_type,
                            "address": signal.modbus_address,
                            "state": state,
                            "status": "success",
                            "indicator": indicator_color
                        })
                        logger.debug(f"Successfully read signal {signal.signal_name}: {state}")
                        
                    except Exception as e:
                        results.append({
                            "signal_name": signal.signal_name,
                            "type": signal.signal_type,
                            "address": signal.modbus_address,
                            "state": f"Error: {str(e)}",
                            "status": "error", 
                            "indicator": "red"
                        })
                        logger.error(f"Error reading signal {signal.signal_name}: {str(e)}")

                logger.info("Connection test completed successfully")
                return f"Connection successful - {self._build_results_table(results)}"

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg)
            return frappe.msgprint(error_msg, title="Connection Failed", indicator='red')
        
    @frappe.whitelist()
    def read_signal(self, signal):
        """Read value from a signal"""
        logger.debug(f"Reading signal {signal.signal_name} from {self.device_name}")
        
        try:
            with self.get_client() as client:
                handler = SignalHandler(client)
                return handler.read(signal.signal_type, signal.modbus_address)
        except Exception as e:
            logger.error(f"Error reading signal: {str(e)}")
            raise

    @frappe.whitelist()
    def write_signal(self, signal, value):
        """Write value to a signal"""
        logger.debug(f"Writing value {value} to signal {signal.signal_name} on {self.device_name}")
        
        try:
            with self.get_client() as client:
                handler = SignalHandler(client)
                handler.write(signal.signal_type, signal.modbus_address, value)
        except Exception as e:
            logger.error(f"Error writing signal: {str(e)}")
            raise