# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from epibus.epibus.utils.epinomy_logger import get_logger
import re

logger = get_logger(__name__)

# Define PLC address ranges and their corresponding Modbus mappings
PLC_ADDRESS_MAPPINGS = {
    'QX': {  # Digital Outputs
        'range': (0, 199, 7),  # Format: (start_byte, end_byte, max_bit)
        'modbus_ranges': [
            {'plc_range': (0, 99), 'modbus_range': (0, 799), 'type': 'Coil'},
            {'plc_range': (100, 199), 'modbus_range': (800, 1599), 'type': 'Slave Coil'}
        ],
        'access': 'RW'
    },
    'IX': {  # Digital Inputs
        'range': (0, 199, 7),
        'modbus_ranges': [
            {'plc_range': (0, 99), 'modbus_range': (0, 799), 'type': 'Contact'},
            {'plc_range': (100, 199), 'modbus_range': (800, 1599), 'type': 'Slave Contact'}
        ],
        'access': 'R'
    },
    'IW': {  # Analog Inputs
        'range': (0, 1023, None),
        'modbus_ranges': [
            {'plc_range': (0, 1023), 'modbus_range': (0, 1023), 'type': 'Input Register'}
        ],
        'access': 'R'
    },
    'QW': {  # Analog Outputs
        'range': (0, 1023, None),
        'modbus_ranges': [
            {'plc_range': (0, 1023), 'modbus_range': (0, 1023), 'type': 'Holding Register'}
        ],
        'access': 'RW'
    },
    'MW': {  # Memory (16-bit)
        'range': (0, 1023, None),
        'modbus_ranges': [
            {'plc_range': (0, 1023), 'modbus_range': (1024, 2047), 'type': 'Memory Register'}
        ],
        'access': 'RW'
    },
    'MD': {  # Memory (32-bit)
        'range': (0, 1023, None),
        'modbus_ranges': [
            {'plc_range': (0, 1023), 'modbus_range': (2048, 4095), 'type': 'Memory Register'}
        ],
        'access': 'RW'
    },
    'ML': {  # Memory (64-bit)
        'range': (0, 1023, None),
        'modbus_ranges': [
            {'plc_range': (0, 1023), 'modbus_range': (4096, 8191), 'type': 'Memory Register'}
        ],
        'access': 'RW'
    }
}

class ModbusSignal(Document):
    def validate(self):
        """Validate the PLC address format and ranges"""
        try:
            self.validate_plc_address()
            self.validate_signal_type()
            self.validate_modbus_address()
        except Exception as e:
            logger.error(f"Validation error for ModbusSignal {self.name}: {str(e)}")
            raise

    def validate_plc_address(self):
        """Validate PLC address format and range"""
        pattern = r'^%([A-Z]{2})(\d+)\.?(\d+)?$'
        match = re.match(pattern, self.plc_address)
        
        if not match:
            frappe.throw(_("Invalid PLC address format. Expected format: %XX0.0"))
            
        prefix, byte, bit = match.groups()
        byte = int(byte)
        bit = int(bit) if bit else None
        
        if prefix not in PLC_ADDRESS_MAPPINGS:
            frappe.throw(_("Invalid PLC address prefix: {0}").format(prefix))
            
        mapping = PLC_ADDRESS_MAPPINGS[prefix]
        start_byte, end_byte, max_bit = mapping['range']
        
        if not start_byte <= byte <= end_byte:
            frappe.throw(_("Byte address {0} out of range ({1}-{2})").format(
                byte, start_byte, end_byte))
        
        if bit is not None and (bit < 0 or bit > max_bit):
            frappe.throw(_("Bit address {0} out of range (0-{1})").format(
                bit, max_bit))

    def validate_signal_type(self):
        """Validate signal type matches PLC address type"""
        prefix = self.plc_address[1:3]
        expected_types = []
        
        for range_info in PLC_ADDRESS_MAPPINGS[prefix]['modbus_ranges']:
            expected_types.append(range_info['type'])
            
        if not any(t in self.signal_type for t in expected_types):
            frappe.throw(_("Signal type {0} does not match PLC address type {1}").format(
                self.signal_type, prefix))

    def validate_modbus_address(self):
        """Validate Modbus address is within correct range"""
        prefix = self.plc_address[1:3]
        byte = int(re.match(r'^%[A-Z]{2}(\d+)', self.plc_address).group(1))
        
        valid_range = False
        for range_info in PLC_ADDRESS_MAPPINGS[prefix]['modbus_ranges']:
            plc_start, plc_end = range_info['plc_range']
            modbus_start, modbus_end = range_info['modbus_range']
            
            if plc_start <= byte <= plc_end:
                if not modbus_start <= self.modbus_address <= modbus_end:
                    frappe.throw(_("Modbus address {0} out of range ({1}-{2})").format(
                        self.modbus_address, modbus_start, modbus_end))
                valid_range = True
                break
                
        if not valid_range:
            frappe.throw(_("Invalid Modbus address range for PLC address type"))

    @frappe.whitelist()
    def toggle_location_pin(self):
        """Toggle the value of a location pin"""
        logger.info(f"Toggling location pin for {self.name}")
        
        try:
            # Verify this is a writable signal
            prefix = self.plc_address[1:3]
            if PLC_ADDRESS_MAPPINGS[prefix]['access'] != 'RW':
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