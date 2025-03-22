# -*- coding: utf-8 -*-
# Script to run all Modbus troubleshooting scripts in sequence
# Run with: bench execute epibus.epibus.troubleshoot_modbus.run_all --args "US15-B10-B1"

import frappe
import time
import os
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger("modbus_troubleshoot")


def run_all(device_name):
    """
    Run all Modbus troubleshooting scripts in sequence

    Args:
        device_name: Name of the Modbus Connection document
    """
    frappe.init(site="site1.local")
    frappe.connect()

    logger.info(
        f"Starting comprehensive troubleshooting for device: {device_name}")

    try:
        # Create a timestamped log file
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_dir = os.path.join(frappe.get_site_path(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(
            log_dir, f"modbus_troubleshoot_{device_name}_{timestamp}.log")

        with open(log_file, 'w') as f:
            f.write(f"=== Modbus Troubleshooting for {device_name} ===\n\n")
            f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        logger.info(f"Logging detailed results to {log_file}")

        # Step 1: Check database values
        logger.info("Step 1: Checking database values...")
        append_to_log(log_file, "=== Step 1: Database Check ===\n")

        from epibus.epibus.check_modbus_db_values import check_device_db_values
        check_device_db_values(device_name)

        # Wait a moment for logs to be written
        time.sleep(2)

        # Append recent logs to our log file
        append_recent_logs(log_file, "modbus_db_check")

        # Step 2: Run diagnostic script
        logger.info("Step 2: Running diagnostic script...")
        append_to_log(log_file, "\n=== Step 2: Diagnostic Check ===\n")

        from epibus.epibus.debug_modbus_connection import debug_device
        debug_device(device_name)

        # Wait a moment for logs to be written
        time.sleep(2)

        # Append recent logs to our log file
        append_recent_logs(log_file, "modbus_debug")

        # Step 3: Run fix script
        logger.info("Step 3: Running fix script...")
        append_to_log(log_file, "\n=== Step 3: Fix Attempt ===\n")

        from epibus.epibus.fix_modbus_signals import fix_device_signals
        fix_device_signals(device_name)

        # Wait a moment for logs to be written
        time.sleep(2)

        # Append recent logs to our log file
        append_recent_logs(log_file, "modbus_fix")

        # Step 4: Verify fix
        logger.info("Step 4: Verifying fix...")
        append_to_log(log_file, "\n=== Step 4: Verification ===\n")

        # Check if the fix worked by calling get_modbus_data
        try:
            from epibus.www.warehouse_dashboard import get_modbus_data

            connections = get_modbus_data()
            target_connection = None

            for conn in connections:
                if conn.get('name') == device_name:
                    target_connection = conn
                    break

            if target_connection:
                null_count = 0
                valid_count = 0

                for signal in target_connection.get('signals', []):
                    if signal.get('value') is None:
                        null_count += 1
                    else:
                        valid_count += 1

                result = f"Verification: {valid_count} signals have values, {null_count} signals are still null"
                logger.info(result)
                append_to_log(log_file, result + "\n")

                if null_count > 0:
                    warning = f"Warning: Some signals ({null_count}) still have null values"
                    logger.warning(warning)
                    append_to_log(log_file, warning + "\n")
                else:
                    success = "Success: All signals now have valid values"
                    logger.info(success)
                    append_to_log(log_file, success + "\n")
            else:
                error = f"Error: Connection {device_name} not found in get_modbus_data results"
                logger.error(error)
                append_to_log(log_file, error + "\n")

        except Exception as e:
            error = f"Error verifying fix: {str(e)}"
            logger.error(error)
            append_to_log(log_file, error + "\n")

        # Finalize log file
        append_to_log(
            log_file, f"\nTroubleshooting completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        logger.info(f"Troubleshooting complete. Results saved to {log_file}")

        # Return the path to the log file
        return log_file

    except Exception as e:
        logger.error(f"Error in run_all: {str(e)}")
        return None


def append_to_log(log_file, text):
    """Append text to the log file"""
    with open(log_file, 'a') as f:
        f.write(text)


def append_recent_logs(log_file, logger_name):
    """Append recent logs from the specified logger to our log file"""
    try:
        # Get recent logs from the database
        logs = frappe.get_all(
            "Error Log",
            filters={
                "method": ["like", f"%{logger_name}%"]
            },
            fields=["timestamp", "method", "error"],
            order_by="timestamp desc",
            limit=50
        )

        if logs:
            with open(log_file, 'a') as f:
                for log in reversed(logs):  # Reverse to get chronological order
                    f.write(f"{log.timestamp} [{log.method}] {log.error}\n")

    except Exception as e:
        logger.error(f"Error appending logs: {str(e)}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        log_file = run_all(sys.argv[1])
        if log_file:
            print(f"Troubleshooting complete. Results saved to {log_file}")
        else:
            print("Troubleshooting failed.")
    else:
        print("Please provide a device name")
