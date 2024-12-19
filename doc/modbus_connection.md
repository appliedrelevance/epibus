## EpiBus _Modbus Connection_ DocType

### Overview
The Modbus Connection DocType in EpiBus provides a structure for defining connections to Modbus devices. It is essential for configuring and managing Modbus communication within the system.

### Fields Description
1. **Host**: (Type: Data, Required) The IP address or hostname of the Modbus device. It is set to "0.0.0.0" by default but should be updated to the actual device's address.

2. **Port**: (Type: Int) The port number used for the Modbus connection. Default value is "502", which is the standard port for Modbus TCP.

3. **Device Name**: (Type: Data) A descriptive name for the Modbus device, aiding in identification and management.

4. **Unit**: (Type: Int) Represents the unit identifier in the Modbus network. It is useful for distinguishing between different devices on the same network.

5. **Locations**: (Type: Table, Options: "Modbus Signal") This field links to the Modbus Signal DocType, allowing the specification of various locations or points within the Modbus device.

### Permissions
The permissions for creating, reading, updating, and deleting Modbus Connection are typically restricted to roles like 'System Manager', 'Modbus Administrator', and 'Modbus User'.

### Configuring a Modbus Connection
To set up a Modbus Connection, follow these steps:

1. **Access Modbus Connection DocType**: Navigate to the Modbus Connection DocType in the EpiBus system.

2. **Create New Record**: Start a new Modbus Connection record.

3. **Configure Host and Port**:
   - Enter the Host IP address or hostname of the Modbus device.
   - Specify the Port number, if different from the default 502.

4. **Define Device Name**: Give a descriptive name to the device for easy identification.

5. **Set Unit Identifier**: Enter the unit identifier specific to your Modbus network setup.

6. **Specify Locations**: Add locations using the 'Modbus Signal' DocType to define various points or locations on the Modbus device that you want to interact with.

7. **Save and Test**: After configuring the settings, save the document. Ensure to test the connection for proper communication with the Modbus device.

By completing these steps, users can successfully configure and manage Modbus connections within the EpiBus system, facilitating effective communication with Modbus devices.

---

This documentation provides a straightforward guide for users to set up Modbus connections in the EpiBus environment. It can be expanded or adjusted according to additional features or specific requirements of the system.