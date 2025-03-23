#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run tests for the enhanced Modbus Action functionality.
This script will:
1. Run the test_modbus_action_conditions.py tests
2. Run the test_signal_update.py tests
3. Print a summary of the results
"""

import frappe
import os
import sys
import time
import traceback


def print_header(text):
    """Print a header with the given text"""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80 + "\n")


def run_test_module(module_name):
    """Run a test module and return success status"""
    try:
        print(f"Running {module_name}...")
        module = __import__(module_name, fromlist=["run_tests"])
        module.run_tests()
        print(f"✅ {module_name} completed successfully")
        return True
    except Exception as e:
        print(f"❌ Error running {module_name}: {str(e)}")
        traceback.print_exc()
        return False


def main():
    """Main function to run all tests"""
    print_header("MODBUS ACTION ENHANCEMENT TESTS")

    # Track test results
    results = {}

    # Run test_modbus_action_conditions
    print_header("TESTING CONDITION HANDLING")
    results["condition_tests"] = run_test_module(
        "epibus.tests.test_modbus_action_conditions")

    # Run test_signal_update
    print_header("TESTING SIGNAL UPDATE HANDLING")
    results["signal_update_tests"] = run_test_module(
        "epibus.tests.test_signal_update")

    # Print summary
    print_header("TEST SUMMARY")
    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    print("\nOverall result:",
          "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED")

    # Print next steps
    print_header("NEXT STEPS")
    print("1. Review the test results and fix any issues")
    print("2. Check the Modbus Event log for action execution records")
    print("3. Create some real Modbus Actions with different conditions")
    print("4. Test with real PLC signals")
    print("\nDocumentation: /workspace/development/frappe-bench/apps/epibus/epibus/docs/modbus_action_enhancements.md")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
