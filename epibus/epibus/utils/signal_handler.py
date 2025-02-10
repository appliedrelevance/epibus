# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Any, Callable, Optional, Union
from enum import Enum
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

class SignalType(Enum):
    """Enum of supported Modbus signal types"""
    DIGITAL_OUTPUT = "Digital Output Coil"
    DIGITAL_INPUT = "Digital Input Contact" 
    ANALOG_INPUT = "Analog Input Register"
    ANALOG_OUTPUT = "Analog Output Register"
    HOLDING_REGISTER = "Holding Register"

class SignalHandler:
    """Handles read/write operations for different Modbus signal types"""
    
    def __init__(self, client):
        """Initialize with a Modbus client
        
        Args:
            client: A connected ModbusTcpClient instance
        """
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
            SignalType.ANALOG_OUTPUT: (
                lambda addr: self.client.read_holding_registers(address=addr, count=1),
                lambda addr, val: self.client.write_register(address=addr, value=val),
                float
            ),
            SignalType.HOLDING_REGISTER: (
                lambda addr: self.client.read_holding_registers(address=addr, count=1),
                lambda addr, val: self.client.write_register(address=addr, value=val),
                float
            )
        }

    def get_handler(self, signal_type: str) -> tuple[Callable, Optional[Callable], type]:
        """Get the appropriate handler functions for a signal type
        
        Args:
            signal_type: The signal type string from the ModbusSignal doc
            
        Returns:
            Tuple of (read_fn, write_fn, type_converter)
            
        Raises:
            ValueError: If signal type is not supported
        """
        for sig_type in SignalType:
            if sig_type.value == signal_type:
                return self.handlers[sig_type]
        raise ValueError(f"Unsupported signal type: {signal_type}")

    def read(self, signal_type: str, address: int) -> Union[bool, float]:
        """Read a value from a signal
        
        Args:
            signal_type: The signal type string
            address: Modbus address to read from
            
        Returns:
            bool for digital signals, float for analog signals
            
        Raises:
            ValueError: If signal type is not supported
            ModbusException: If read operation fails
        """
        read_fn, _, conv_fn = self.get_handler(signal_type)
        response = read_fn(address)
        return conv_fn(response.bits[0] if hasattr(response, 'bits') else response.registers[0])

    def write(self, signal_type: str, address: int, value: Union[bool, float]) -> None:
        """Write a value to a signal
        
        Args:
            signal_type: The signal type string
            address: Modbus address to write to
            value: Value to write (bool for digital, float for analog)
            
        Raises:
            ValueError: If signal type is not supported or is read-only
            ModbusException: If write operation fails
        """
        _, write_fn, conv_fn = self.get_handler(signal_type)
        if not write_fn:
            raise ValueError(f"Cannot write to read-only signal type: {signal_type}")
        write_fn(address, conv_fn(value))

# In modbus_handlers.py

def handle_doc_event(doc, method):
    """Handle document events and execute relevant Modbus Actions"""
    try:
        # Find all Modbus Actions configured for this doctype and event
        actions = frappe.get_all(
            "Modbus Action",
            filters={
                "trigger_doctype": doc.doctype,
                "docstatus": 1  # Only consider submitted actions
            },
            fields=["name", "server_script"]
        )
        
        if not actions:
            return
            
        logger.debug(
            f"Found {len(actions)} Modbus Action(s) for {doc.doctype} "
            f"event {method}"
        )
        
        # Execute each matching action
        for action in actions:
            try:
                action_doc = frappe.get_doc("Modbus Action", action.name)
                script = frappe.get_doc("Server Script", action.server_script)
                
                if script.script_type == "API":
                    result = action_doc.execute_script(doc)
                    if result.get("status") != "success":
                        logger.error(
                            f"Modbus Action {action.name} failed: "
                            f"{result.get('error', 'Unknown error')}"
                        )
                else:
                    action_doc.execute_script(doc)
                    
            except Exception as e:
                logger.error(
                    f"Error executing Modbus Action {action.name}: {str(e)}"
                )
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Modbus Action Event Handler Error - {action.name}"
                )
                
    except Exception as e:
        logger.error(
            f"Error handling {method} event for {doc.doctype}: {str(e)}"
        )
        frappe.log_error(
            frappe.get_traceback(),
            "Modbus Action Event Handler Error"
        )