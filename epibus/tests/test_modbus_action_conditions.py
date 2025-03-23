import frappe
import unittest
from epibus.utils.plc_redis_client import PLCRedisClient
import json
import time
from frappe.utils import now


class TestModbusActionConditions(unittest.TestCase):
    def setUp(self):
        # Create test connection
        if not frappe.db.exists("Modbus Connection", "TEST-CONN-01"):
            self.connection = frappe.get_doc({
                "doctype": "Modbus Connection",
                "device_name": "Test Connection",
                "device_type": "PLC",
                "host": "localhost",
                "port": 502,
                "enabled": 1
            })
            self.connection.insert()
        else:
            self.connection = frappe.get_doc(
                "Modbus Connection", "TEST-CONN-01")

        # Create test signal
        if not frappe.db.exists("Modbus Signal", "TEST-SIG-01"):
            self.signal = frappe.get_doc({
                "doctype": "Modbus Signal",
                "parent": self.connection.name,
                "parenttype": "Modbus Connection",
                "parentfield": "signals",
                "signal_name": "Test Signal",
                "signal_type": "Digital Output Coil",
                "modbus_address": 100,
                "digital_value": False
            })
            self.signal.insert()
        else:
            self.signal = frappe.get_doc("Modbus Signal", "TEST-SIG-01")

        # Create test server script
        if not frappe.db.exists("Server Script", "Test Modbus Action Script"):
            self.script = frappe.get_doc({
                "doctype": "Server Script",
                "name": "Test Modbus Action Script",
                "script_type": "API",
                "api_method": "test_modbus_action",
                "disabled": 0,
                "script": """
# Test Modbus Action Script
import frappe
import json

def test_modbus_action():
    # Get context
    context = frappe.flags.modbus_context
    
    # Log the execution
    frappe.log_error(
        f"Test script executed with signal: {context['signal'].name}, value: {context['value']}",
        "Test Modbus Action"
    )
    
    # Return success
    return {
        "status": "success",
        "message": "Test script executed successfully",
        "context": {
            "signal": context['signal'].name,
            "value": context['value'],
            "params": context.get('params', {})
        }
    }
"""
            })
            self.script.insert()
        else:
            self.script = frappe.get_doc(
                "Server Script", "Test Modbus Action Script")

        # Create test actions with different conditions
        self.create_test_action("TEST-ACT-ANY", "Any Change", None)
        self.create_test_action("TEST-ACT-EQ-TRUE", "Equals", "true")
        self.create_test_action("TEST-ACT-EQ-FALSE", "Equals", "false")
        self.create_test_action("TEST-ACT-GT", "Greater Than", "5")
        self.create_test_action("TEST-ACT-LT", "Less Than", "10")

        # Initialize Redis client
        self.redis_client = PLCRedisClient.get_instance()

    def create_test_action(self, name, condition, value):
        """Create a test Modbus Action with the specified condition"""
        if not frappe.db.exists("Modbus Action", name):
            action = frappe.get_doc({
                "doctype": "Modbus Action",
                "action_name": f"Test Action - {condition}",
                "connection": self.connection.name,
                "signal": self.signal.name,
                "server_script": self.script.name,
                "enabled": 1,
                "trigger_type": "Signal Change",
                "signal_condition": condition,
                "signal_value": value,
                "parameters": [
                    {
                        "parameter": "test_param",
                        "value": "test_value"
                    }
                ]
            })
            action.insert()

    def test_any_change_condition(self):
        """Test that 'Any Change' condition triggers for any value"""
        # Process a signal update with value=True
        self.redis_client._process_signal_actions(self.signal.name, True)
        time.sleep(1)  # Allow time for action to execute

        # Check logs for execution
        self.assertTrue(self.check_action_executed("TEST-ACT-ANY"))

        # Process a signal update with value=False
        self.redis_client._process_signal_actions(self.signal.name, False)
        time.sleep(1)  # Allow time for action to execute

        # Check logs for execution
        self.assertTrue(self.check_action_executed("TEST-ACT-ANY"))

    def test_equals_condition(self):
        """Test that 'Equals' condition only triggers for matching values"""
        # Process a signal update with value=True
        self.redis_client._process_signal_actions(self.signal.name, True)
        time.sleep(1)  # Allow time for action to execute

        # Check logs for execution - TRUE action should execute, FALSE should not
        self.assertTrue(self.check_action_executed("TEST-ACT-EQ-TRUE"))
        self.assertFalse(self.check_action_executed("TEST-ACT-EQ-FALSE"))

        # Process a signal update with value=False
        self.redis_client._process_signal_actions(self.signal.name, False)
        time.sleep(1)  # Allow time for action to execute

        # Check logs for execution - FALSE action should execute, TRUE should not
        self.assertTrue(self.check_action_executed("TEST-ACT-EQ-FALSE"))
        self.assertFalse(self.check_action_executed("TEST-ACT-EQ-TRUE"))

    def test_numeric_conditions(self):
        """Test numeric comparison conditions"""
        # Process a signal update with value=7 (between 5 and 10)
        self.redis_client._process_signal_actions(self.signal.name, 7)
        time.sleep(1)  # Allow time for action to execute

        # Check logs for execution - GT 5 should execute, LT 10 should execute
        self.assertTrue(self.check_action_executed("TEST-ACT-GT"))
        self.assertTrue(self.check_action_executed("TEST-ACT-LT"))

        # Process a signal update with value=3 (less than 5)
        self.redis_client._process_signal_actions(self.signal.name, 3)
        time.sleep(1)  # Allow time for action to execute

        # Check logs for execution - GT 5 should not execute, LT 10 should execute
        self.assertFalse(self.check_action_executed("TEST-ACT-GT"))
        self.assertTrue(self.check_action_executed("TEST-ACT-LT"))

        # Process a signal update with value=15 (greater than 10)
        self.redis_client._process_signal_actions(self.signal.name, 15)
        time.sleep(1)  # Allow time for action to execute

        # Check logs for execution - GT 5 should execute, LT 10 should not execute
        self.assertTrue(self.check_action_executed("TEST-ACT-GT"))
        self.assertFalse(self.check_action_executed("TEST-ACT-LT"))

    def check_action_executed(self, action_name):
        """Check if an action was executed by looking at the Modbus Event log"""
        events = frappe.get_all(
            "Modbus Event",
            filters={
                "event_type": "Action Execution",
                "action": action_name,
                "status": "Success"
            },
            fields=["name"],
            limit=1
        )
        return len(events) > 0

    def tearDown(self):
        """Clean up test data"""
        # We'll leave the test data for inspection
        pass


def run_tests():
    """Run the tests"""
    test = TestModbusActionConditions()
    test.setUp()
    test.test_any_change_condition()
    test.test_equals_condition()
    test.test_numeric_conditions()
    test.tearDown()
    print("All tests completed")


if __name__ == "__main__":
    run_tests()
