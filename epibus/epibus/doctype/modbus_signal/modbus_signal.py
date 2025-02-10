# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.utils.signal_handler import SignalHandler

logger = get_logger(__name__)

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
        signal_type: DF.Literal["Digital Output Coil", "Digital Input Contact", "Analog Input Register", "Analog Output Register", "Holding Register"]
    # end: auto-generated types
    def validate(self):
        """Validate the signal configuration"""
        try:
            self.validate_signal_type()
            self.validate_modbus_address()
            self.set_plc_address()
        except Exception as e:
            logger.error(f"Validation error for ModbusSignal {self.name}: {str(e)}")
            raise

    def validate_signal_type(self):
        """Validate that the signal type is recognized"""
        if self.signal_type not in SIGNAL_TYPE_MAPPINGS:
            frappe.throw(_("Invalid signal type: {0}").format(self.signal_type))

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

    @frappe.whitelist()
    def calculate_plc_address(self):
        """Calculate and set the PLC address based on signal type and Modbus address"""
        signal_config = SIGNAL_TYPE_MAPPINGS[self.signal_type]

        if signal_config["bit_addressed"]:
            # For bit-addressed signals (Digital I/O)
            plc_major = signal_config["plc_major_start"] + (self.modbus_address // 8)
            plc_minor = self.modbus_address % 8

            if plc_minor > signal_config["plc_minor_max"]:
                frappe.throw(_("Invalid bit address calculated"))

            self.plc_address = f"%{signal_config['prefix']}{plc_major}.{plc_minor}"
        else:
            # For word-addressed signals (Analog and Holding Registers)
            plc_major = signal_config["plc_major_start"] + self.modbus_address
            self.plc_address = f"%{signal_config['prefix']}{plc_major}"

    @frappe.whitelist()
    def read_signal(self):
        """Read the current value of the signal

        Returns:
            bool|float: Current value of the signal depending on type
        """
        logger.debug(f"Reading signal {self.signal_name}")

        try:
            # Get the parent device document
            device_doc = frappe.get_doc("Modbus Device", self.parent)

            # Read the value using the device's client
            with device_doc.get_client() as client:
                handler = SignalHandler(client)
                value = handler.read(self.signal_type, self.modbus_address)

                # Update the appropriate field based on signal type
                if isinstance(value, bool):
                    self.digital_value = value
                else:
                    self.value = value
                self.save()

                logger.debug(f"Successfully read {self.signal_name}: {value}")
                return value

        except Exception as e:
            logger.error(f"Error reading signal {self.signal_name}: {str(e)}")
            raise

    @frappe.whitelist()
    def write_signal(self, value):
        """Write a value to the signal

        Args:
            value (bool|float): Value to write, type must match signal type

        Returns:
            bool|float: Value read back from signal after write
        """
        logger.debug(f"Writing value {value} to signal {self.signal_name}")

        try:
            # Verify this is a writable signal
            signal_config = SIGNAL_TYPE_MAPPINGS[self.signal_type]
            if signal_config["access"] != "RW":
                frappe.throw(_("Cannot write to read-only signal"))

            # Validate value type
            is_digital = signal_config["bit_addressed"]
            if is_digital and not isinstance(value, bool):
                frappe.throw(_("Digital signals require boolean values"))
            elif not is_digital and not isinstance(value, (int, float)):
                frappe.throw(_("Analog signals require numeric values"))

            # Get the parent device document
            device_doc = frappe.get_doc("Modbus Device", self.parent)

            # Write the value using the device's client
            with device_doc.get_client() as client:
                handler = SignalHandler(client)
                handler.write(self.signal_type, self.modbus_address, value)

                # Read back the value to confirm
                current_value = handler.read(self.signal_type, self.modbus_address)

                self.value = current_value
                self.save()

                logger.info(f"Successfully wrote {current_value} to {self.signal_name}")
                return current_value

        except Exception as e:
            logger.error(f"Error writing to signal {self.signal_name}: {str(e)}")
            raise

    @frappe.whitelist()
    def toggle_signal(self):
        """Toggle a digital signal between True/False

        Returns:
            bool: New value of the signal after toggle
        """
        if not SIGNAL_TYPE_MAPPINGS[self.signal_type]["bit_addressed"]:
            frappe.throw(_("Can only toggle digital signals"))

        try:
            current_value = self.read_signal()
            if not isinstance(current_value, bool):
                frappe.throw(_("Invalid signal state - expected boolean value"))

            new_value = not current_value
            return self.write_signal(new_value)

        except Exception as e:
            logger.error(f"Error toggling signal {self.signal_name}: {str(e)}")
            raise

    @frappe.whitelist()
    def toggle_location_pin(self):
        """DEPRECATED: Use toggle_signal() instead"""
        frappe.log_error(
            "toggle_location_pin() is deprecated, use toggle_signal() instead",
            "Deprecated Method Used",
        )
        return self.toggle_signal()
