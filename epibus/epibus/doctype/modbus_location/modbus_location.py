# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ModbusLocation(Document):
    pass


# The Modbus addresses bind to PLC addresses based on the hierarchical address value, i.e. lower PLC addresses are
# mapped to lower Modbus addresses. Addresses are mapped sequentially whenever possible. The following table shows the
#  Modbus address space for the OpenPLC Linux/Windows runtime:
# Modbus Data Type		Usage					PLC Address			Modbus Data Address	Data Size	Range			Access
# Discrete Output 		Coils Digital Outputs	%QX0.0 – %QX99.7	0 – 799				1 bit		0 or 1			RW
# Discrete Output 		Coils Slave Outputs		%QX100.0 – %QX199.7	800 – 1599			1 bit		0 or 1			RW
# Discrete Input 		Contacts Digital Inputs	%IX0.0 – %IX99.7	0 – 799				1 bit		0 or 1			R
# Discrete Input 		Contacts Slave Inputs	%IX100.0 – %IX199.7	800 – 1599			1 bit		0 or 1			RW
# Analog Input 			Registers Analog Input 	%IW0 – %IW1023		0 – 1023			16 bits		0 – 65535		R
# Holding Registers		Analog Outputs			%QW0 – %QW1023		0 – 1023			16 bits		0 – 65535		RW
# Holding Registers		Memory (16-bits)		%MW0 – %MW1023		1024 – 2048			16 bits		0 – 65535		RW
# Holding Registers		Memory (32-bits)		%MD0 – %MD1023		2048 – 4095			32 bits		0 – 4294967295	RW
# Holding Registers		Memory (64-bits)		%ML0 – %ML1023		4096 – 8191			64 bits		0 – N			RW
