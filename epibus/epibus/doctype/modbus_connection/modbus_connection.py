# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import asyncio
from pymodbus.client import ModbusTcpClient
from frappe.model.document import Document
from epibus.epibus.utils.epinomy_logger import get_logger


logger = get_logger(__name__)

class ModbusConnection(Document):

    @frappe.whitelist()
    def test_connection(self, host, port):
        """Test connection to Modbus server"""
        logger.info(f"Testing Modbus Connection {self.name}")
        try:
            # Ensure there is an active event loop for the current thread
            try:
                asyncio.get_event_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

            client = ModbusTcpClient(
                host=host,
                port=int(port),
                timeout=10
            )
            
            logger.info(f"Connecting to {host}:{port}")
            
            # Connect using PyModbus 3.x syntax
            if not client.connect():
                logger.error("Connection failed")
                return "Connection failed"

            locs = "Locations: "
            for d in self.get("locations"):
                if not isinstance(d.modbus_address, int) or not d.plc_address:
                    locs += "Not Configured, "
                    continue

                try:
                    addr = int(d.modbus_address)
                    # Read value based on signal type using PyModbus 3.x methods
                    if "Digital Output Coil" in d.signal_type:
                        response = client.read_coils(addr)
                        state = "On" if response.bits[0] else "Off"
                        d.toggle = response.bits[0]
                    elif "Digital Input Contact" in d.signal_type:
                        response = client.read_discrete_inputs(addr)
                        state = "On" if response.bits[0] else "Off"
                        d.toggle = response.bits[0]
                    elif "Analog Input Register" in d.signal_type:
                        response = client.read_input_registers(addr)
                        state = str(response.registers[0])
                    elif "Analog Output" in d.signal_type or "Memory Register" in d.signal_type:
                        response = client.read_holding_registers(addr)
                        state = str(response.registers[0])
                    else:
                        state = "Unknown Type"

                    d.value = state
                    locs += f"{d.location_name}: {d.plc_address} ({state}), "

                except Exception as e:
                    logger.error(f"Error reading location {d.location_name}: {str(e)}")
                    locs += f"{d.location_name}: Error ({str(e)}), "
            
            # Close the connection
            client.close()
            
            logger.info("Connection test successful")
            return "Connection successful " + locs

        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            if 'client' in locals() and client:
                try:
                    client.close()
                except:
                    pass
            return f"Connection failed: {str(e)}"

    @frappe.whitelist()
    def import_from_simulator(self, simulator_name):
        """Import locations from a PLC Simulator"""
        try:
            # Get the simulator document
            simulator = frappe.get_doc("PLC Simulator", simulator_name)
            
            if not simulator.enabled:
                frappe.throw(_("Selected simulator is not enabled"))
                
            # Update connection details to match simulator
            self.host = simulator.get("server_address", "localhost")
            self.port = simulator.server_port
            
            # Clear existing locations
            self.locations = []
            
            # Copy locations from simulator
            for io_point in simulator.io_points:
                self.append("locations", {
                    "location_name": io_point.location_name,
                    "signal_type": io_point.signal_type,
                    "plc_address": io_point.plc_address,
                    "modbus_address": io_point.modbus_address,
                    "value": io_point.value
                })
            
            # Save the document
            self.save()
            
            # Return the number of locations imported
            return len(simulator.io_points)
            
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Failed to import from simulator"))
            frappe.throw(_("Failed to import from simulator: {0}").format(str(e)))

    @frappe.whitelist()
    def toggle_location(self, host, port, modbus_address, signal_type):
        print("Toggling " + str(modbus_address))
        client = ModbusTcpClient(host, port)
        res = client.connect()
        if res:
            state = client.read_coils(modbus_address, 1).bits[0]
            print("Current state: " + str(state))
            client.write_coil(modbus_address, not state)
            client.close()
            print("Toggled from " + str(state) + " to " + str(not state))
        else:
            return "Connection Failed"

    @frappe.whitelist()
    def get_current_values(self):
        # Initialize an empty list to store the values
        plc_pin_values = []

        # Iterate through the locations table in this Modbus Connection document
        for location_entry in self.locations:
            # Fetch the corresponding Modbus Signal document
            location_doc = frappe.get_doc(
                "Modbus Signal", location_entry.location_name
            )

            # Assume we have a method 'read_location_value' to read the actual value from the Modbus device
            current_value = self.read_location_value(location_doc)

            # Update the 'value' field in the Modbus Signal document
            location_doc.value = current_value
            location_doc.save()

            # Store the current value of the PLC Pin/Register Address
            value_entry = {
                "PLC Pin Name": location_doc.location_name,
                "Current Value": current_value,
            }
            plc_pin_values.append(value_entry)

        return plc_pin_values

    def read_location_value(self, location_doc):
        host = self.host
        port = self.port
        unit = self.unit  # Unit ID (Slave ID)

        client = ModbusTcpClient(host, port)

        # Connect to the Modbus server
        if client.connect():
            try:
                # Read based on the location type
                if location_doc.signal_type == "Digital Output Coil":
                    response = client.read_coils(location_doc.modbus_address, unit=unit)
                elif location_doc.signal_type == "Digital Input Contact":
                    response = client.read_discrete_inputs(
                        location_doc.modbus_address, unit=unit
                    )
                elif location_doc.signal_type == "Analog Input Register":
                    response = client.read_input_registers(
                        location_doc.modbus_address, unit=unit
                    )
                elif location_doc.signal_type == "Analog Output Holding Register":
                    response = client.read_holding_registers(
                        location_doc.modbus_address, unit=unit
                    )
                else:
                    return "Unsupported Location Type"

                # Return the value if successful
                if response.isError():
                    return "Error reading value"
                else:
                    return response.registers[0] if hasattr(response, 'registers') else response.bits[0]
            
            finally:
                # Always close the connection
                client.close()
        else:
            return "Connection failed"