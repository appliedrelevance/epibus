# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from pymodbus.client import ModbusTcpClient
from frappe.model.document import Document


class ModbusConnection(Document):
    @frappe.whitelist()
    def test_connection(self, host, port):
        print("Testing Modbus Connection " + self.name)
        client = ModbusTcpClient(host, port)
        print("Connecting to " + host + ":" + str(port))
        res = client.connect()
        locs = "Locations: "
        for d in self.get("locations"):
            stateBln = client.read_coils(d.modbus_address, 1).bits[0]
            state = "On" if stateBln else "Off"
            if d.modbus_address is None or d.plc_address is None:
                locs += "Not Configured, "
            else:
                locs += (
                    str(d.location_name)
                    + ": "
                    + str(d.plc_address)
                    + " ("
                    + state
                    + "), "
                )
            d.value = state
            d.toggle = stateBln
        return "Connection successful " + locs if res else "Connection failed"

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