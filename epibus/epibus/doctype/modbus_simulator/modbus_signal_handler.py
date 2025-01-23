# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import SignalException

logger = get_logger(__name__)


class SignalHandler:
    """Manages Modbus signal operations and validation"""

    # Signal type mappings to Modbus blocks
    SIGNAL_MAPPINGS = {
        "Digital Output Coil": {
            "block": "co",
            "readable": True,
            "writable": True,
            "value_type": bool,
        },
        "Digital Input Contact": {
            "block": "di",
            "readable": True,
            "writable": False,
            "value_type": bool,
        },
        "Analog Input Register": {
            "block": "ir",
            "readable": True,
            "writable": False,
            "value_type": float,
        },
        "Analog Output Register": {
            "block": "hr",
            "readable": True,
            "writable": True,
            "value_type": float,
        },
        "Holding Register": {
            "block": "hr",
            "readable": True,
            "writable": True,
            "value_type": float,
        },
    }

    def __init__(self, simulator_doc, datastore):
        """Initialize signal handler

        Args:
            simulator_doc: Parent ModbusSimulator document
            datastore: DatastoreManager instance
        """
        self.doc = simulator_doc
        self.datastore = datastore

    def read_signal(self, signal_name):
        """Read a value from a named signal

        Args:
            signal_name: Name of signal to read

        Returns:
            bool or float: Signal value

        Raises:
            SignalException: If read fails
        """
        try:
            # Get signal configuration
            signal = self._get_signal(signal_name)
            if not signal:
                raise SignalException(f"Signal not found: {signal_name}")

            # Get mapping info
            mapping = self._get_mapping(signal.signal_type)
            if not mapping["readable"]:
                raise SignalException(
                    f"Signal type {signal.signal_type} is not readable"
                )

            # Read from datastore
            value = self.datastore.get_value(mapping["block"], signal.modbus_address)

            if self.doc.debug_mode:
                logger.debug(f"Read signal {signal_name} = {value}")

            return value

        except Exception as e:
            error_msg = f"Failed to read signal {signal_name}: {str(e)}"
            logger.error(error_msg)
            raise SignalException(error_msg)

    def write_signal(self, signal_name, value):
        """Write a value to a named signal

        Args:
            signal_name: Name of signal to write
            value: Value to write (bool or float)

        Raises:
            SignalException: If write fails or validation fails
        """
        try:
            # Get signal configuration
            signal = self._get_signal(signal_name)
            if not signal:
                raise SignalException(f"Signal not found: {signal_name}")

            # Get mapping info
            mapping = self._get_mapping(signal.signal_type)
            if not mapping["writable"]:
                raise SignalException(
                    f"Signal type {signal.signal_type} is not writable"
                )

            # Validate value type
            if not isinstance(value, mapping["value_type"]):
                raise SignalException(
                    f"Invalid value type for {signal_name}. "
                    f"Expected {mapping['value_type'].__name__}"
                )

            # Write to datastore
            self.datastore.set_value(mapping["block"], signal.modbus_address, value)

            if self.doc.debug_mode:
                logger.debug(f"Wrote signal {signal_name} = {value}")

        except Exception as e:
            error_msg = f"Failed to write signal {signal_name}: {str(e)}"
            logger.error(error_msg)
            raise SignalException(error_msg)

    def toggle_signal(self, signal_name):
        """Toggle a digital signal between True/False

        Args:
            signal_name: Name of signal to toggle

        Returns:
            bool: New signal value

        Raises:
            SignalException: If toggle fails or signal is not digital
        """
        try:
            # Get signal configuration
            signal = self._get_signal(signal_name)
            if not signal:
                raise SignalException(f"Signal not found: {signal_name}")

            # Verify digital type
            mapping = self._get_mapping(signal.signal_type)
            if mapping["value_type"] != bool:
                raise SignalException(
                    f"Can only toggle digital signals, not {signal.signal_type}"
                )

            if not mapping["writable"]:
                raise SignalException(f"Signal {signal_name} is not writable")

            # Read current value
            current = self.read_signal(signal_name)

            # Write opposite value
            self.write_signal(signal_name, not current)

            return not current

        except Exception as e:
            error_msg = f"Failed to toggle signal {signal_name}: {str(e)}"
            logger.error(error_msg)
            raise SignalException(error_msg)

    def test_signals(self):
        """Test read/write on all configured signals

        Returns:
            list: Test results for each signal
        """
        results = []

        for signal in self.doc.io_points:
            try:
                mapping = self._get_mapping(signal.signal_type)

                if mapping["readable"]:
                    value = self.read_signal(signal.signal_name)
                    results.append(
                        {
                            "signal": signal.signal_name,
                            "type": signal.signal_type,
                            "value": value,
                        }
                    )
                else:
                    results.append(
                        {
                            "signal": signal.signal_name,
                            "type": signal.signal_type,
                            "error": "Signal is not readable",
                        }
                    )

            except Exception as e:
                results.append(
                    {
                        "signal": signal.signal_name,
                        "type": signal.signal_type,
                        "error": str(e),
                    }
                )

        return results

    def _get_signal(self, name):
        """Get signal configuration by name

        Args:
            name: Signal name to find

        Returns:
            ModbusSignal or None: Found signal or None
        """
        return next((s for s in self.doc.io_points if s.signal_name == name), None)

    def _get_mapping(self, signal_type):
        """Get block mapping for signal type

        Args:
            signal_type: Signal type string

        Returns:
            dict: Mapping configuration

        Raises:
            SignalException: If signal type is invalid
        """
        if signal_type not in self.SIGNAL_MAPPINGS:
            raise SignalException(f"Invalid signal type: {signal_type}")

        return self.SIGNAL_MAPPINGS[signal_type]
