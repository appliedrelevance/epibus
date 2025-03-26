# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from typing import cast, Union, Optional, overload, TypeVar, Any, TypeGuard, Literal
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.utils.signal_handler import SignalHandler
from epibus.epibus.doctype.modbus_event.modbus_event import ModbusEvent
from epibus.epibus.doctype.modbus_connection.modbus_connection import ModbusConnection
from epibus.epibus.utils.signal_monitor import publish_signal_update

logger = get_logger(__name__)

NumericValue = Union[float, int]
SignalValue = Union[bool, NumericValue]

# Define Signal Types and their corresponding PLC address configurations
SIGNAL_TYPE_MAPPINGS = {
    "Digital Output Coil": {
        "prefix": "QX",
        "modbus_range": (0, 999),
        "access": "RW",
        "bit_addressed": True,
        "plc_major_start": 0,
        "plc_minor_max": 7,
    },
    "Digital Input Contact": {
        "prefix": "IX",
        "modbus_range": (0, 999),
        "access": "R",
        "bit_addressed": True,
        "plc_major_start": 0,
        "plc_minor_max": 7,
    },
    "Analog Input Register": {
        "prefix": "IW",
        "modbus_range": (0, 1023),
        "access": "R",
        "bit_addressed": False,
        "plc_major_start": 0,
    },
    "Analog Output Register": {
        "prefix": "QW",
        "modbus_range": (0, 1023),
        "access": "RW",
        "bit_addressed": False,
        "plc_major_start": 0,
    },
    "Holding Register": {
        "prefix": "MW",
        "modbus_range": (0, 1023),
        "access": "RW",
        "bit_addressed": False,
        "plc_major_start": 0,
    },
}


def is_bool(value: SignalValue) -> TypeGuard[bool]:
    """Type guard to ensure a value is boolean"""
    return isinstance(value, bool)


def read_bool_signal(signal: 'ModbusSignal') -> bool:
    """Read a digital signal value, ensuring boolean return type

    Args:
        signal: The ModbusSignal document to read from

    Returns:
        bool: The current value of the signal

    Raises:
        frappe.ValidationError: If the signal value is not boolean
    """
    if not SIGNAL_TYPE_MAPPINGS[signal.signal_type]["bit_addressed"]:
        frappe.throw(_("Can only read boolean values from digital signals"))

    value = signal.read_signal()
    if not is_bool(value):
        frappe.throw(_("Invalid signal state - expected boolean value"))
    return value


@frappe.whitelist()
def is_signal_writable(signal_id: str) -> bool:
    """Check if a signal is writable based on its type

    Args:
        signal_id (str): The name of the ModbusSignal document to check

    Returns:
        bool: True if the signal is writable, False otherwise

    Raises:
        ValueError: If signal_id is None or empty
    """
    if not signal_id:
        frappe.throw(_("Signal id cannot be empty"))

    signal = cast(ModbusSignal, frappe.get_doc("Modbus Signal", signal_id))
    
    # Check if the signal type has write access
    signal_config = SIGNAL_TYPE_MAPPINGS.get(signal.signal_type, {})
    is_writable = signal_config.get("access", "") == "RW"
    
    logger.debug(f"Signal {signal.signal_name} ({signal.signal_type}) is writable: {is_writable}")
    
    return is_writable


@frappe.whitelist(methods=['POST'])
def toggle_signal(signal_id: str, value: Optional[bool] = None) -> bool:
    """Toggle a digital signal between True/False or set to specific value

    Args:
        signal_name (str): The name of the ModbusSignal document to toggle
        value (Optional[bool]): If provided, set to this specific boolean value instead of toggling

    Returns:
        bool: New value of the signal after toggle/set

    Raises:
        ValueError: If signal_name is None or empty
        frappe.ValidationError: If signal is not a digital type or current value is not boolean
    """
    if not signal_id:
        frappe.throw(_("Signal id cannot be empty"))

    signal = cast(ModbusSignal, frappe.get_doc("Modbus Signal", signal_id))

    # Check if the signal is writable
    if not is_signal_writable(signal_id):
        frappe.throw(_("Cannot write to read-only signal type: {0}").format(signal.signal_type))

    if not SIGNAL_TYPE_MAPPINGS[signal.signal_type]["bit_addressed"]:
        frappe.throw(_("Can only toggle digital signals"))

    try:
        if value is not None:
            # Convert string "True"/"False" to boolean if needed
            if isinstance(value, str):
                value = value.lower() == "true"
            new_value = bool(value)  # Ensure boolean type
        else:
            # Toggle current value if no specific value provided
            current_value = read_bool_signal(signal)
            new_value = not current_value

        # Write the new value and ensure boolean return
        result = signal.write_signal(new_value)
        if not is_bool(result):
            frappe.throw(_("Invalid toggle result - expected boolean value"))
        return result

    except Exception as e:
        logger.error(f"Error toggling signal {signal.signal_name}: {str(e)}")
        raise


class ModbusSignal(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        digital_value: DF.Check
        float_value: DF.Float
        modbus_address: DF.Int
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        plc_address: DF.Data | None
        signal_name: DF.Data
        signal_type: DF.Literal["Digital Output Coil", "Digital Input Contact",
                                "Analog Input Register", "Analog Output Register", "Holding Register"]
    # end: auto-generated types

    def validate(self):
        """Validate the signal configuration"""
        try:
            self.validate_signal_type()
            self.validate_modbus_address()
            self.calculate_plc_address()
        except Exception as e:
            logger.error(
                f"Validation error for ModbusSignal {self.name}: {str(e)}")
            raise

    def validate_signal_type(self):
        """Validate that the signal type is recognized"""
        if self.signal_type not in SIGNAL_TYPE_MAPPINGS:
            frappe.throw(
                _("Invalid signal type: {0}").format(self.signal_type))

    def validate_modbus_address(self):
        """Validate Modbus address is within correct range for the signal type"""
        signal_config = SIGNAL_TYPE_MAPPINGS[self.signal_type]
        modbus_start, modbus_end = signal_config["modbus_range"]

        if not modbus_start <= self.modbus_address <= modbus_end:
            frappe.throw(
                _(
                    "Modbus address {0} out of range ({1}-{2}) for signal type {3}"
                ).format(
                    self.modbus_address, modbus_start, modbus_end, self.signal_type
                )
            )

    @frappe.whitelist(methods=['POST'])
    def calculate_plc_address(self):
        """Calculate and set the PLC address based on signal type and Modbus address"""
        signal_config = SIGNAL_TYPE_MAPPINGS[self.signal_type]

        if signal_config["bit_addressed"]:
            # For bit-addressed signals (Digital I/O)
            plc_major = signal_config["plc_major_start"] + \
                (self.modbus_address // 8)
            plc_minor = self.modbus_address % 8

            if plc_minor > signal_config["plc_minor_max"]:
                frappe.throw(_("Invalid bit address calculated"))

            self.plc_address = f"%{signal_config['prefix']}{plc_major}.{plc_minor}"
        else:
            # For word-addressed signals (Analog and Holding Registers)
            plc_major = signal_config["plc_major_start"] + self.modbus_address
            self.plc_address = f"%{signal_config['prefix']}{plc_major}"

    @overload
    def read_signal(self) -> bool:
        """Read a digital signal value"""
        ...

    @overload
    def read_signal(self) -> NumericValue:
        """Read an analog or holding register value"""
        ...

    @frappe.whitelist(methods=['GET'])
    def read_signal(self) -> SignalValue:
        """Read the current value of the signal"""
        logger.debug(f"Reading signal {self.signal_name}")

        try:
            device_doc = cast(
                ModbusConnection, frappe.get_doc(
                    "Modbus Connection", self.parent)
            )

            with device_doc.get_client() as client:
                handler = SignalHandler(client)
                value = handler.read(self.signal_type, self.modbus_address)

                # Log successful read event
                # ModbusEvent.log_event(
                #     event_type="Read",
                #     device=self.parent,
                #     signal=self.name,
                #     new_value=value,
                # )

                return value

        except Exception as e:
            # Log failed read event
            ModbusEvent.log_event(
                event_type="Read",
                device=self.parent,
                signal=self.name,
                status="Failed",
                error=e,
                message=f"Failed to read signal {self.signal_name} (Address: {self.modbus_address}, Type: {self.signal_type})"
            )
            raise

    @overload
    def write_signal(self, value: bool) -> bool:
        """Write a boolean value to a digital signal"""
        ...

    @overload
    def write_signal(self, value: NumericValue) -> NumericValue:
        """Write a numeric value to an analog or holding register"""
        ...

    @frappe.whitelist(methods=['POST'])
    def write_signal(self, value: SignalValue) -> SignalValue:
        """Write a value to the signal"""
        logger.debug(f"Writing value {value} to signal {self.signal_name}")

        try:
            # Get current value for event log
            try:
                current_value = self.read_signal()
            except Exception:
                current_value = None

            device_doc = cast(
                ModbusConnection, frappe.get_doc(
                    "Modbus Connection", self.parent)
            )

            with device_doc.get_client() as client:
                handler = SignalHandler(client)
                handler.write(self.signal_type, self.modbus_address, value)

                # Read back value
                new_value = handler.read(self.signal_type, self.modbus_address)

                # Convert and validate read-back value based on input and output types
                if isinstance(value, bool):
                    # If input was boolean, ensure output is boolean
                    if isinstance(new_value, (int, float)):
                        # Convert numeric 0/1 to boolean safely
                        new_value = bool(new_value)
                    elif not isinstance(new_value, bool):
                        frappe.throw(
                            _("Invalid return type from boolean write operation"))
                elif isinstance(value, (int, float)):
                    # If input was numeric, ensure output is numeric
                    if isinstance(new_value, bool):
                        frappe.throw(
                            _("Expected numeric value from write operation, got boolean"))
                    elif isinstance(new_value, (int, float)):
                        # Ensure consistent numeric type
                        new_value = float(new_value) if isinstance(
                            value, float) else int(new_value)

                # Log successful write event
                ModbusEvent.log_event(
                    event_type="Write",
                    device=self.parent,
                    signal=self.name,
                    previous_value=current_value,
                    new_value=new_value,
                    message=f"Successfully wrote value {new_value} to signal {self.signal_name} (Address: {self.modbus_address}, Type: {self.signal_type})"
                )

                # Publish immediate update
                if self.name:
                    publish_signal_update(str(self.name), new_value)

                return new_value

        except Exception as e:
            # Log failed write event
            ModbusEvent.log_event(
                event_type="Write",
                device=self.parent,
                signal=self.name,
                previous_value=current_value,
                status="Failed",
                error=e,
                message=f"Failed to write value to signal {self.signal_name} (Address: {self.modbus_address}, Type: {self.signal_type})"
            )
            raise

    @frappe.whitelist(methods=['POST'])
    def toggle_signal(self, value: Optional[bool] = None) -> bool:
        """Toggle a digital signal between True/False or set to specific value

        Args:
            value (Optional[bool]): If provided, set to this specific boolean value instead of toggling

        Returns:
            bool: New value of the signal after toggle/set
        """
        if not self.name:
            frappe.throw(_("Document must be saved before toggling"))

        # Cast self.name to str since we've verified it's not None
        return toggle_signal(str(self.name), value)

    @frappe.whitelist(methods=['POST'])
    def toggle_location_pin(self) -> bool:
        """DEPRECATED: Use toggle_signal() instead"""
        frappe.log_error(
            "toggle_location_pin() is deprecated, use toggle_signal() instead",
            "Deprecated Method Used",
        )
        return self.toggle_signal()

    def get_digital_value(self) -> bool:
        """Virtual field getter for digital value"""
        value = self.read_signal()
        if not isinstance(value, bool):
            frappe.throw(_("Invalid signal state - expected boolean value"))
        return value

    def set_digital_value(self, value: bool) -> None:
        """Virtual field setter for digital value"""
        if not isinstance(value, bool):
            frappe.throw(_("Digital value must be boolean"))
        self.write_signal(value)

    def get_float_value(self) -> float:
        """Virtual field getter for float value"""
        value = self.read_signal()
        if not isinstance(value, (int, float)):
            frappe.throw(_("Invalid signal state - expected numeric value"))
        return float(value)

    def set_float_value(self, value: float) -> None:
        """Virtual field setter for float value"""
        if not isinstance(value, (int, float)):
            frappe.throw(_("Float value must be numeric"))
        self.write_signal(float(value))

    def get_plc_address(self) -> Optional[str]:
        """Virtual field getter for PLC address"""
        if not self.signal_type or self.modbus_address is None:
            return None

        signal_config = SIGNAL_TYPE_MAPPINGS[self.signal_type]

        if signal_config["bit_addressed"]:
            # For bit-addressed signals (Digital I/O)
            plc_major = signal_config["plc_major_start"] + \
                (self.modbus_address // 8)
            plc_minor = self.modbus_address % 8

            if plc_minor > signal_config["plc_minor_max"]:
                return None

            return f"%{signal_config['prefix']}{plc_major}.{plc_minor}"
        else:
            # For word-addressed signals (Analog and Holding Registers)
            plc_major = signal_config["plc_major_start"] + self.modbus_address
            return f"%{signal_config['prefix']}{plc_major}"
