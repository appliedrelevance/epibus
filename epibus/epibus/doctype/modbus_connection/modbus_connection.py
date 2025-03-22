# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient
from pymodbus.framer import FramerType

from epibus.epibus.utils.signal_handler import SignalHandler
import asyncio
from contextlib import contextmanager
from typing import Optional
import time

from epibus.epibus.utils.epinomy_logger import get_logger
logger = get_logger(__name__)


class ModbusConnection(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from epibus.epibus.doctype.modbus_signal.modbus_signal import ModbusSignal
        from frappe.types import DF

        device_name: DF.Data
        device_type: DF.Literal["PLC", "Robot", "Simulator", "Other"]
        enabled: DF.Check
        host: DF.Data
        port: DF.Int
        signals: DF.Table[ModbusSignal]
        thumbnail: DF.AttachImage | None
    # end: auto-generated types

    _client: Optional[ModbusTcpClient] = None
    _last_used: float = 0
    _connection_timeout: int = 30  # Seconds before connection is considered stale

    def validate(self):
        self.validate_connection_settings()

    def validate_connection_settings(self):
        if not (1 <= self.port <= 65535):
            frappe.throw("Port must be between 1 and 65535")

    def get_client(self):
        """Get a ModbusTcpClient instance, reusing existing connection if valid

        Returns:
            ModbusTcpClient: Connected client instance

        Raises:
            ConnectionError: If connection fails
        """
        current_time = time.time()

        # Check if we need a new connection
        if (self._client is None or
            not self._client.connected or
                current_time - self._last_used > self._connection_timeout):

            # Close existing connection if any
            if self._client:
                try:
                    self._client.close()
                except:
                    pass
                self._client = None

            try:
                asyncio.get_event_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

            # Create new connection with retry settings
            self._client = ModbusTcpClient(
                host=self.host,
                port=self.port,
                framer=FramerType.SOCKET,
                timeout=10,
                retries=5,  # Increased from default 3
                reconnect_delay=1  # 1 second delay between retries
            )

            if not self._client.connect():
                raise ConnectionError(
                    f"Failed to connect to {self.host}:{self.port}")

        self._last_used = current_time
        return self._client

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
        """Test connection to device and read all signals"""
        logger.info(
            f"Testing connection to device {self.device_name} at {self.host}:{self.port}")

        try:
            client = self.get_client()
            handler = SignalHandler(client)
            results = []

            # Collect results
            for signal in self.signals:
                try:
                    value = handler.read(
                        signal.signal_type, signal.modbus_address)

                    if isinstance(value, bool):
                        state = "HIGH" if value else "LOW"
                        indicator_color = "green" if value else "gray"
                    else:
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
                    logger.debug(
                        f"Successfully read signal {signal.signal_name}: {state}")

                except Exception as e:
                    results.append({
                        "signal_name": signal.signal_name,
                        "type": signal.signal_type,
                        "address": signal.modbus_address,
                        "state": f"Error: {str(e)}",
                        "status": "error",
                        "indicator": "red"
                    })
                    logger.error(
                        f"Error reading signal {signal.signal_name}: {str(e)}")

            logger.info("Connection test completed successfully")
            return f"Connection successful - {self._build_results_table(results)}"

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg)
            return frappe.msgprint(error_msg, title="Connection Failed", indicator='red')

    @frappe.whitelist(methods=['GET'])
    def read_signal(self, signal):
        """Read value from a signal

        Args:
            signal: ModbusSignal document

        Returns:
            bool|float: Current value of the signal
        """
        logger.debug(
            f"Reading signal {signal.signal_name} from {self.device_name}")

        try:
            client = self.get_client()
            handler = SignalHandler(client)
            value = handler.read(signal.signal_type, signal.modbus_address)

            # No need to update the database for virtual fields
            # The value is returned directly and should not be persisted
            # as digital_value and float_value are virtual fields

            return value

        except Exception as e:
            logger.error(f"Error reading signal: {str(e)}")
            raise

    @frappe.whitelist(methods=['POST'])
    def write_signal(self, signal, value):
        """Write value to a signal

        Args:
            signal: ModbusSignal document
            value: bool|float value to write
        """
        logger.debug(
            f"Writing value {value} to signal {signal.signal_name} on {self.device_name}")

        try:
            client = self.get_client()
            handler = SignalHandler(client)
            handler.write(signal.signal_type, signal.modbus_address, value)

            # Read back value to verify write
            current_value = handler.read(
                signal.signal_type, signal.modbus_address)

        except Exception as e:
            logger.error(f"Error writing signal: {str(e)}")
            raise
