# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient
from pymodbus.framer import FramerType
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.utils.signal_handler import SignalHandler
import asyncio
from contextlib import contextmanager

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

    def validate(self):
        self.validate_connection_settings()

    def validate_connection_settings(self):
        if not (1 <= self.port <= 65535):
            frappe.throw("Port must be between 1 and 65535")

    @contextmanager
    def get_client(self):
        """Get a connected ModbusTcpClient instance

        Yields:
            ModbusTcpClient: Connected client instance

        Raises:
            ConnectionError: If connection fails
        """
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
                raise ConnectionError(
                    f"Failed to connect to {self.host}:{self.port}")
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
        """Test connection to device and read all signals"""
        logger.info(
            f"Testing connection to device {self.device_name} at {self.host}:{self.port}")

        try:
            with self.get_client() as client:
                handler = SignalHandler(client)
                results = []

                # Collect results
                for signal in self.signals:
                    try:
                        value = handler.read(
                            signal.signal_type, signal.modbus_address)

                        if isinstance(value, bool):
                            signal.digital_value = value
                            state = "HIGH" if value else "LOW"
                            indicator_color = "green" if value else "gray"
                        else:
                            signal.value = value
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
            with self.get_client() as client:
                handler = SignalHandler(client)
                value = handler.read(signal.signal_type, signal.modbus_address)

                # Update signal's stored value
                if isinstance(value, bool):
                    signal.digital_value = value
                else:
                    signal.value = value
                signal.save()

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
            with self.get_client() as client:
                handler = SignalHandler(client)
                handler.write(signal.signal_type, signal.modbus_address, value)

                # Read back and update stored value
                current_value = handler.read(
                    signal.signal_type, signal.modbus_address)
                if isinstance(current_value, bool):
                    signal.digital_value = current_value
                else:
                    signal.value = current_value
                signal.save()

        except Exception as e:
            logger.error(f"Error writing signal: {str(e)}")
            raise
