## EpiBus _Modbus Action_ DocType

### Overview
The EpiBus Modbus Action DocType is designed to control or monitor Modbus I/O ports. It is triggered by a hook that watches for the `on_submit` event on Stock Entry documents. When a Stock Entry is submitted, the Modbus Action iterates over the Item entries in the document and triggers the action associated with the source warehouse.

### Fields Description

1. **Connection**: (Type: Link) This field links to the 'Modbus Connection' DocType. It specifies the Modbus connection used by the action.

2. **Location**: (Type: Link, depends on Connection) Links to the 'Modbus Signal' DocType. This field defines the location where the Modbus action will be executed.

3. **Action**: (Type: Select, depends on Location) Allows the selection of either 'Read' or 'Write' actions. This field determines whether the Modbus Action will read from or write to the specified location.

4. **Bit Value**: (Type: Check, default: 1) This checkbox determines the bit value to be used in the action. It is editable based on the action type and other conditions.

5. **Warehouse**: (Type: Link) Links to the 'Warehouse' DocType. This field is crucial as it specifies the warehouse to watch. The action is triggered when an item is moved from this warehouse.

### Permissions
The permissions for creating, reading, updating, and deleting the Modbus Action are restricted to roles like 'System Manager', 'Modbus Administrator', and 'Modbus User'.

### Configuring Modbus Action for a Warehouse

To configure the Modbus Action to process transactions for a given warehouse, follow these steps:

1. **Create a New Modbus Action**: Go to the Modbus Action DocType and create a new record.

2. **Set Connection**: Choose an appropriate Modbus connection from the 'Connection' field.

3. **Specify Location**: Select the Modbus location where the action should take place.

4. **Define Action**: Choose 'Read' or 'Write' in the 'Action' field based on your requirement.

5. **Set Bit Value**: If necessary, change the bit value. This is usually required for 'Write' actions.

6. **Select Warehouse**: In the 'Warehouse' field, link the warehouse that you want to monitor. The action will be triggered when a stock entry submission involves this warehouse.

7. **Save and Enable**: After configuring the fields, save the document to enable the action.

By following these steps, users can set up the Modbus Action to automatically execute actions based on stock movements in specified warehouses, leveraging the EpiBus system's integration with Modbus devices.
