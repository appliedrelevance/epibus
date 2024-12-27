# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

# Define Signal Types and their corresponding PLC address configurations
SIGNAL_TYPE_MAPPINGS = {
    'Digital Output Coil': {
        'prefix': 'QX',
        'modbus_range': (0, 999),
        'access': 'RW',
        'bit_addressed': True,
        'plc_major_start': 0,
        'plc_minor_max': 7
    },
    'Digital Input Contact': {
        'prefix': 'IX',
        'modbus_range': (0, 999),
        'access': 'R',
        'bit_addressed': True,
        'plc_major_start': 0,
        'plc_minor_max': 7
    },
    'Analog Input Register': {
        'prefix': 'IW',
        'modbus_range': (0, 1023),
        'access': 'R',
        'bit_addressed': False,
        'plc_major_start': 0
    },
    'Analog Output Register': {
        'prefix': 'QW',
        'modbus_range': (0, 1023),
        'access': 'RW',
        'bit_addressed': False,
        'plc_major_start': 0
    },
    'Holding Register': {
        'prefix': 'MW',
        'modbus_range': (0, 1023),
        'access': 'RW',
        'bit_addressed': False,
        'plc_major_start': 0
    }
}

class ModbusSignal(Document):
    def validate(self):
        """Validate the signal configuration"""
        try:
            self.validate_signal_type()
            self.validate_modbus_address()
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
        modbus_start, modbus_end = signal_config['modbus_range']
        
        if not modbus_start <= self.modbus_address <= modbus_end:
            frappe.throw(_("Modbus address {0} out of range ({1}-{2}) for signal type {3}").format(
                self.modbus_address, modbus_start, modbus_end, self.signal_type))

    @property
    def plc_address(self):
        """Calculate and return PLC address based on signal type and Modbus address"""
        try:
            signal_config = SIGNAL_TYPE_MAPPINGS[self.signal_type]
            
            if signal_config['bit_addressed']:
                # For bit-addressed signals (Digital I/O)
                plc_major = signal_config['plc_major_start'] + (self.modbus_address // 8)
                plc_minor = self.modbus_address % 8
                
                if plc_minor > signal_config['plc_minor_max']:
                    frappe.throw(_("Invalid bit address calculated"))
                    
                return f"%{signal_config['prefix']}{plc_major}.{plc_minor}"
            else:
                # For word-addressed signals (Analog and Holding Registers)
                plc_major = signal_config['plc_major_start'] + self.modbus_address
                return f"%{signal_config['prefix']}{plc_major}"
        except Exception as e:
            logger.error(f"Error calculating PLC address for signal {self.name}: {str(e)}")
            return ""

    @frappe.whitelist()
    def toggle_location_pin(self):
        """Toggle the value of a location pin"""
        logger.info(f"Toggling location pin for {self.name}")
        
        try:
            # Verify this is a writable signal
            signal_config = SIGNAL_TYPE_MAPPINGS[self.signal_type]
            if signal_config['access'] != 'RW':
                frappe.throw(_("Cannot write to read-only signal"))

            # Fetch the corresponding Modbus Connection document
            connection_doc = frappe.get_doc("Modbus Connection", self.connection_name)

            # Determine the value to write based on the 'toggle' field
            value_to_write = 1 if self.toggle else 0
            
            logger.debug(f"Writing value {value_to_write} to {self.location_name}")

            # Write the value to the corresponding pin
            write_status = connection_doc.write_location_value(self, value_to_write)

            if write_status:
                # Read the value back from the pin
                current_value = connection_doc.read_location_value(self)

                # Update the 'value' field with the read value
                self.value = current_value
                self.save()
                
                logger.info(f"Successfully toggled {self.location_name} to {current_value}")
                return current_value
            else:
                logger.error(f"Failed to write value to {self.location_name}")
                raise frappe.ValidationError(_("Failed to write value to location"))

        except Exception as e:
            logger.error(f"Error toggling location pin: {str(e)}")
            raise