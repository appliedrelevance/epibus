#!/usr/bin/env python
# manual_start_plc_bridge.py - Script to manually start the PLC Bridge with the fixed Redis client

import os
import sys
import time
import signal
import argparse
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("manual_plc_bridge.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("manual_plc_bridge")

# Set paths
BENCH_DIR = Path("/workspace/development/frappe-bench")
APP_DIR = BENCH_DIR / "apps" / "epibus"
BRIDGE_SCRIPT = APP_DIR / "epibus" / "plc_bridge.py"
PID_FILE = BENCH_DIR / "logs" / "plc_bridge.pid"


def run_frappe_command(cmd):
    """Run a command in the Frappe environment"""
    full_cmd = f"cd {BENCH_DIR} && bench --site epinomy.localhost {cmd}"
    logger.info(f"Running: {full_cmd}")

    result = subprocess.run(full_cmd, shell=True,
                            capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"Command failed with exit code {result.returncode}")
        logger.error(f"STDERR: {result.stderr}")
        return False, result.stderr

    return True, result.stdout


def initialize_redis_client():
    """Initialize the fixed Redis client in Frappe"""
    logger.info("Initializing fixed Redis client in Frappe...")

    # Execute Python code in Frappe environment
    code = """
import frappe
from epibus.utils.plc_redis_client_consolidated import PLCRedisClient

# Initialize the Redis client
client = PLCRedisClient.get_instance()
print("Redis client initialized successfully")
"""

    success, output = run_frappe_command(f'execute "{code}"')

    if not success:
        logger.error("Failed to initialize Redis client")
        return False

    logger.info("Redis client initialized successfully")
    return True


def is_plc_running():
    """Check if PLC Bridge is running"""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            # Check if process exists
            os.kill(pid, 0)
            return True
        except OSError:
            # Process doesn't exist
            PID_FILE.unlink()
    return False


def start_plc_bridge(plc_host, redis_host, redis_port):
    """Start the PLC Bridge"""
    if is_plc_running():
        logger.warning(
            f"PLC Bridge is already running with PID {PID_FILE.read_text().strip()}")
        return False

    # Initialize Redis client first
    if not initialize_redis_client():
        logger.error(
            "Failed to initialize Redis client, cannot start PLC Bridge")
        return False

    # Start the PLC Bridge
    logger.info(
        f"Starting PLC Bridge with PLC host {plc_host} and Redis host {redis_host}:{redis_port}...")

    # Build the command
    cmd = [
        f"{BENCH_DIR}/env/bin/python",
        str(BRIDGE_SCRIPT),
        f"--plc-host={plc_host}",
        f"--redis-host={redis_host}",
        f"--redis-port={redis_port}"
    ]

    # Start the process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    # Save PID
    PID_FILE.write_text(str(process.pid))

    logger.info(f"PLC Bridge started with PID {process.pid}")

    # Wait a moment to see if it crashes immediately
    time.sleep(2)

    if process.poll() is not None:
        logger.error(
            f"PLC Bridge exited immediately with code {process.returncode}")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return False

    logger.info("PLC Bridge is running")
    return True


def stop_plc_bridge():
    """Stop the PLC Bridge"""
    if not is_plc_running():
        logger.warning("PLC Bridge is not running")
        return True

    # Get PID
    pid = int(PID_FILE.read_text().strip())

    # Send SIGTERM
    logger.info(f"Stopping PLC Bridge with PID {pid}...")
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        logger.error(f"Failed to send SIGTERM to PID {pid}: {e}")
        return False

    # Wait for process to exit
    for i in range(5):
        time.sleep(1)
        try:
            os.kill(pid, 0)
        except OSError:
            # Process has exited
            logger.info("PLC Bridge stopped")
            if PID_FILE.exists():
                PID_FILE.unlink()
            return True

    # If still running, force kill
    logger.warning(
        "PLC Bridge did not exit gracefully, forcing termination...")
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError as e:
        logger.error(f"Failed to send SIGKILL to PID {pid}: {e}")
        return False

    # Clean up PID file
    if PID_FILE.exists():
        PID_FILE.unlink()

    logger.info("PLC Bridge stopped")
    return True


def show_status():
    """Show status of PLC Bridge"""
    if is_plc_running():
        pid = PID_FILE.read_text().strip()
        logger.info(f"PLC Bridge is running with PID {pid}")

        # Check Redis connection
        code = """
import frappe
import redis
try:
    r = redis.Redis(host='redis-queue', port=6379)
    ping = r.ping()
    print(f"Redis connection: {'OK' if ping else 'Failed'}")
except Exception as e:
    print(f"Redis connection error: {e}")
"""
        run_frappe_command(f'execute "{code}"')

        return True
    else:
        logger.info("PLC Bridge is not running")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Manual PLC Bridge Control")
    parser.add_argument("action", choices=[
                        "start", "stop", "restart", "status"], help="Action to perform")
    parser.add_argument("--plc-host", default="openplc",
                        help="PLC host address")
    parser.add_argument("--redis-host", default="redis-queue",
                        help="Redis host address")
    parser.add_argument("--redis-port", type=int,
                        default=6379, help="Redis port")

    args = parser.parse_args()

    if args.action == "start":
        start_plc_bridge(args.plc_host, args.redis_host, args.redis_port)
    elif args.action == "stop":
        stop_plc_bridge()
    elif args.action == "restart":
        stop_plc_bridge()
        time.sleep(2)
        start_plc_bridge(args.plc_host, args.redis_host, args.redis_port)
    elif args.action == "status":
        show_status()


if __name__ == "__main__":
    main()
