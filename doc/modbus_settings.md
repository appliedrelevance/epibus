## EpiBus _Modbus Settings_ DocType

### Overview
Modbus Settings DocType in EpiBus is a configuration tool that allows users to set general parameters for Modbus operations within the system. This document explains the fields in the Modbus Settings and how to configure them.

### Fields Description
1. **Enable Triggers**: (Type: Check, Default: Enabled) This field determines whether Modbus Actions are triggered on events. When enabled, any configured Modbus Action will be executed based on specified events.

2. **Default Coil Prefix**: (Type: Data, Default: "COIL_") This field sets the default prefix for coil addresses in Modbus communication. The prefix helps in identifying and categorizing coil addresses.

3. **Default Contact Prefix**: (Type: Data, Default: "CONTACT_") Similar to the coil prefix, this field sets the default prefix for contact addresses in Modbus operations.

4. **Default Register Prefix**: (Type: Data, Default: "REGISTER_") This field defines the default prefix for register addresses used in Modbus communication.

### Permissions
Permissions for accessing and modifying the Modbus Settings are generally restricted to users with roles like 'System Manager'. 

### Configuring Modbus Settings
To configure Modbus Settings for your system, follow these steps:

1. **Navigate to Modbus Settings**: Access the Modbus Settings DocType in the EpiBus system.

2. **Set Trigger Option**:
   - Check or uncheck the 'Enable Triggers' box based on whether you want Modbus Actions to be automatically triggered by events in the system.

3. **Configure Address Prefixes**:
   - In 'Default Coil Prefix', enter a prefix that will be automatically appended to coil addresses if needed.
   - Set the 'Default Contact Prefix' for contact addresses in a similar manner.
   - Define a default prefix for register addresses in the 'Default Register Prefix' field.

4. **Save Changes**: After making the necessary adjustments, save the settings to apply them system-wide.

