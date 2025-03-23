import psm  # type: ignore
import time
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("beachside_psm")

# Debug mode flag - set to True for verbose logging
DEBUG_MODE = True

# Global state variables


class PLCState:
    def __init__(self):
        self.cycle_running: bool = False
        self.current_operation: str | None = None
        self.operation_start_time: float = 0.0
        self.error_state: bool = False
        self.selected_bin: int | None = None
        # Track previous bin states
        self.previous_bin_states: dict[int, bool] = {
            i: False for i in range(1, 13)}
        # Track which bin is at which location
        self.bin_locations: dict[str, int | None] = {
            "storage": None,
            "receiving": None,
            "assembly": None
        }


# Operation timeouts in seconds
OPERATION_TIMEOUT = 5  # How long an operation takes
ERROR_CHANCE = 0.0   # 0% chance of error per operation (disabled for testing)
WAIT_TIMEOUT_SECS = 60  # Default timeout for waiting for signals

# Helper function for conditional debug logging


def debug_log(message):
    """Log debug messages only when DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        logger.debug(message)


# Map bin numbers to their addresses
BIN_ADDRESSES = {
    1: "QX1.3",  # PICK_BIN_01
    2: "QX1.4",  # PICK_BIN_02
    3: "QX1.5",  # PICK_BIN_03
    4: "QX1.6",  # PICK_BIN_04
    5: "QX1.7",  # PICK_BIN_05
    6: "QX2.0",  # PICK_BIN_06
    7: "QX2.1",  # PICK_BIN_07
    8: "QX2.2",  # PICK_BIN_08
    9: "QX2.3",  # PICK_BIN_09
    10: "QX2.4",  # PICK_BIN_10
    11: "QX2.5",  # PICK_BIN_11
    12: "QX2.6"  # PICK_BIN_12
}

# MODBUS Signal Addresses
SIGNALS = {
    # Input signals (IX) - From PLC to ERP
    "PLC_CYCLE_RUNNING": "IX0.1",
    "PICK_ERROR": "IX0.2",
    "PICK_TO_ASSEMBLY_IN_PROCESS": "IX0.3",
    "PICK_TO_ASSEMBLY_COMPLETE": "IX0.4",
    "PICK_TO_RECEIVING_IN_PROCESS": "IX0.5",
    "PICK_TO_RECEIVING_COMPLETE": "IX0.6",
    "PICK_TO_STORAGE_IN_PROCESS": "IX0.7",
    "PICK_TO_STORAGE_COMPLETE": "IX1.0",
    "R1_CONV_2_BIN_PRESENT": "IX1.1",  # Receiving conveyor 2 bin present
    "R3_CONV_4_BIN_PRESENT": "IX1.2",  # Assembly conveyor 4 bin present

    # Output signals (QX) - From ERP to PLC
    "TO_RECEIVING_STA_1": "QX4.0",
    "FROM_RECEIVING": "QX4.1",
    "TO_ASSEMBLY_STA_1": "QX4.2",
    "FROM_ASSEMBLY": "QX4.3"
}


def hardware_init():
    """Initialize the PSM hardware layer"""
    logger.info("Initializing Beachside PLC simulator")
    psm.start()
    # Start with cycle running
    psm.set_var("IX0.0", False)  # PLC_CYCLE_STOPPED = FALSE (i.e., running)
    psm.set_var(SIGNALS["PLC_CYCLE_RUNNING"], True)
    logger.info("PLC simulator initialized and ready with cycle RUNNING")


def handle_bin_selection():
    """Check which bin is selected through output coils and log changes"""
    selected_bin = None
    active_bins = []

    # Check each bin's current state and compare with previous
    for bin_num, address in BIN_ADDRESSES.items():
        current_state = psm.get_var(address)
        previous_state = state.previous_bin_states[bin_num]

        # Log any state changes
        if current_state != previous_state:
            state.previous_bin_states[bin_num] = current_state
            status = "ON" if current_state else "OFF"
            logger.info(f"Bin {bin_num:02d} turned {status}")

        # Return the first active bin
        if current_state:
            active_bins.append(bin_num)
            if selected_bin is None:
                selected_bin = bin_num

    # Log active bins if any
    if active_bins:
        logger.info(f"Active bins detected: {active_bins}")

    # Special case for bin 1 and to_receiving operation
    to_receiving_active = psm.get_var(SIGNALS["TO_RECEIVING_STA_1"])
    if to_receiving_active:
        # If TO_RECEIVING_STA_1 is active but no bin is selected, force select bin 1
        if not selected_bin:
            logger.info(
                "TO_RECEIVING_STA_1 is active but no bin selected, forcing bin 1 selection")
            # Force bin 1 to be selected
            psm.set_var(BIN_ADDRESSES[1], True)
            selected_bin = 1

    return selected_bin


# Track previous signal states to only log changes
previous_signal_states = {
    "TO_RECEIVING_STA_1": False,
    "FROM_RECEIVING": False,
    "TO_ASSEMBLY_STA_1": False,
    "FROM_ASSEMBLY": False
}


def handle_station_selection():
    """Check which station operation is requested"""
    # Read all station signals
    to_receiving = psm.get_var(SIGNALS["TO_RECEIVING_STA_1"])
    from_receiving = psm.get_var(SIGNALS["FROM_RECEIVING"])
    to_assembly = psm.get_var(SIGNALS["TO_ASSEMBLY_STA_1"])
    from_assembly = psm.get_var(SIGNALS["FROM_ASSEMBLY"])

    # Check for changes and log only if changed
    signals_changed = False
    changes = []

    if to_receiving != previous_signal_states["TO_RECEIVING_STA_1"]:
        previous_signal_states["TO_RECEIVING_STA_1"] = to_receiving
        signals_changed = True
        changes.append(f"TO_RECEIVING: {to_receiving}")

    if from_receiving != previous_signal_states["FROM_RECEIVING"]:
        previous_signal_states["FROM_RECEIVING"] = from_receiving
        signals_changed = True
        changes.append(f"FROM_RECEIVING: {from_receiving}")

    if to_assembly != previous_signal_states["TO_ASSEMBLY_STA_1"]:
        previous_signal_states["TO_ASSEMBLY_STA_1"] = to_assembly
        signals_changed = True
        changes.append(f"TO_ASSEMBLY: {to_assembly}")

    if from_assembly != previous_signal_states["FROM_ASSEMBLY"]:
        previous_signal_states["FROM_ASSEMBLY"] = from_assembly
        signals_changed = True
        changes.append(f"FROM_ASSEMBLY: {from_assembly}")

    # Log only if any signal changed
    if signals_changed and changes:
        debug_log(f"Station signals changed: {', '.join(changes)}")

    if to_receiving:
        return "to_receiving"
    elif from_receiving:
        return "from_receiving"
    elif to_assembly:
        return "to_assembly"
    elif from_assembly:
        return "from_assembly"
    return None


def clear_operation_flags():
    """Clear all operation in-process and complete flags"""
    # Clear in-process flags
    psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_IN_PROCESS"], False)
    psm.set_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"], False)
    psm.set_var(SIGNALS["PICK_TO_STORAGE_IN_PROCESS"], False)

    # Clear complete flags
    psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_COMPLETE"], False)
    psm.set_var(SIGNALS["PICK_TO_RECEIVING_COMPLETE"], False)
    psm.set_var(SIGNALS["PICK_TO_STORAGE_COMPLETE"], False)


def set_error_state():
    """Set error state and clear operations"""
    logger.error("Error detected in operation!")
    state.error_state = True
    psm.set_var(SIGNALS["PICK_ERROR"], True)
    clear_operation_flags()
    state.current_operation = None


def clear_error_state():
    """Clear error state"""
    state.error_state = False
    psm.set_var(SIGNALS["PICK_ERROR"], False)
    logger.info("Error state cleared")


def start_operation(operation: str, bin_num: int):
    """Start a new robot operation"""
    state.current_operation = operation
    state.operation_start_time = time.time()
    state.selected_bin = bin_num

    # Set appropriate in-process flag based on operation
    if operation == "to_receiving":
        logger.info(
            f"Starting movement from STORAGE to RECEIVING with bin {bin_num}")

        # Explicitly set the flag and verify it was set
        logger.info(
            f"Setting PICK_TO_RECEIVING_IN_PROCESS to TRUE using address: {SIGNALS['PICK_TO_RECEIVING_IN_PROCESS']}")
        psm.set_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"], True)

        # Verify the flag was set correctly
        flag_value = psm.get_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"])
        logger.info(
            f"Verification: PICK_TO_RECEIVING_IN_PROCESS = {flag_value}")

        if flag_value:
            logger.info(
                "Successfully set PICK_TO_RECEIVING_IN_PROCESS to TRUE")
        else:
            logger.error("Failed to set PICK_TO_RECEIVING_IN_PROCESS to TRUE")
            # Try setting it directly by address
            try:
                logger.info(
                    "Trying to set PICK_TO_RECEIVING_IN_PROCESS directly by address IX0.5")
                psm.set_var("IX0.5", True)
                flag_value = psm.get_var("IX0.5")
                logger.info(
                    f"Direct set result: PICK_TO_RECEIVING_IN_PROCESS (IX0.5) = {flag_value}")
            except Exception as e:
                logger.error(
                    f"Error setting PICK_TO_RECEIVING_IN_PROCESS directly: {str(e)}")

        # Update bin location
        state.bin_locations["storage"] = None
        state.bin_locations["receiving"] = bin_num

    elif operation == "from_receiving":
        logger.info(
            f"Starting movement from RECEIVING to STORAGE with bin {bin_num}")
        psm.set_var(SIGNALS["PICK_TO_STORAGE_IN_PROCESS"], True)
        # Update bin location
        state.bin_locations["receiving"] = None
        state.bin_locations["storage"] = bin_num

    elif operation == "to_assembly":
        logger.info(
            f"Starting movement from STORAGE to ASSEMBLY with bin {bin_num}")
        psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_IN_PROCESS"], True)
        # Update bin location
        state.bin_locations["storage"] = None
        state.bin_locations["assembly"] = bin_num

    elif operation == "from_assembly":
        logger.info(
            f"Starting movement from ASSEMBLY to STORAGE with bin {bin_num}")
        psm.set_var(SIGNALS["PICK_TO_STORAGE_IN_PROCESS"], True)
        # Update bin location
        state.bin_locations["assembly"] = None
        state.bin_locations["storage"] = bin_num
        state.bin_locations["storage"] = bin_num


def complete_operation():
    """Complete the current operation"""
    # Set completion flag based on operation
    if state.current_operation == "to_receiving":
        logger.info(
            f"Completed movement to RECEIVING with bin {state.selected_bin}")
        psm.set_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"], False)
        psm.set_var(SIGNALS["PICK_TO_RECEIVING_COMPLETE"], True)
        # Simulate bin present on receiving conveyor
        time.sleep(0.5)  # Small delay to simulate operator action
        psm.set_var(SIGNALS["R1_CONV_2_BIN_PRESENT"], True)

    elif state.current_operation == "from_receiving":
        logger.info(
            f"Completed movement from RECEIVING to STORAGE with bin {state.selected_bin}")
        psm.set_var(SIGNALS["PICK_TO_STORAGE_IN_PROCESS"], False)
        psm.set_var(SIGNALS["PICK_TO_STORAGE_COMPLETE"], True)
        # Clear bin present on receiving conveyor
        psm.set_var(SIGNALS["R1_CONV_2_BIN_PRESENT"], False)

    elif state.current_operation == "to_assembly":
        logger.info(
            f"Completed movement to ASSEMBLY with bin {state.selected_bin}")
        psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_IN_PROCESS"], False)
        psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_COMPLETE"], True)
        # Simulate bin present on assembly conveyor
        time.sleep(0.5)  # Small delay to simulate operator action
        psm.set_var(SIGNALS["R3_CONV_4_BIN_PRESENT"], True)

    elif state.current_operation == "from_assembly":
        logger.info(
            f"Completed movement from ASSEMBLY to STORAGE with bin {state.selected_bin}")
        psm.set_var(SIGNALS["PICK_TO_STORAGE_IN_PROCESS"], False)
        psm.set_var(SIGNALS["PICK_TO_STORAGE_COMPLETE"], True)
        # Clear bin present on assembly conveyor
        psm.set_var(SIGNALS["R3_CONV_4_BIN_PRESENT"], False)

    # Clear operation state
    state.current_operation = None
    state.selected_bin = None


def simulate_operator_actions():
    """Simulate operator actions like placing bins on conveyors"""
    # If a bin is at receiving and operator has had time to process it
    if (state.bin_locations["receiving"] is not None and
        not state.current_operation and
            psm.get_var(SIGNALS["PICK_TO_RECEIVING_COMPLETE"])):

        # After some time, operator places bin on return conveyor
        if random.random() < 0.1:  # 10% chance per cycle to simulate operator completing task
            bin_num = state.bin_locations["receiving"]
            debug_log(
                f"Operator placed bin {bin_num} on return conveyor from RECEIVING")
            psm.set_var(SIGNALS["R1_CONV_2_BIN_PRESENT"], True)
            # Clear completion flag as we're starting a new phase
            psm.set_var(SIGNALS["PICK_TO_RECEIVING_COMPLETE"], False)

    # If a bin is at assembly and operator has had time to process it
    if (state.bin_locations["assembly"] is not None and
        not state.current_operation and
            psm.get_var(SIGNALS["PICK_TO_ASSEMBLY_COMPLETE"])):

        # After some time, operator places bin on return conveyor
        if random.random() < 0.1:  # 10% chance per cycle to simulate operator completing task
            bin_num = state.bin_locations["assembly"]
            debug_log(
                f"Operator placed bin {bin_num} on return conveyor from ASSEMBLY")
            psm.set_var(SIGNALS["R3_CONV_4_BIN_PRESENT"], True)
            # Clear completion flag as we're starting a new phase
            psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_COMPLETE"], False)


def check_bin_return_conveyors():
    """Check if bins are present on return conveyors and initiate return to storage"""
    # Check if there's already an active operation
    if state.current_operation:
        return

    # Check receiving return conveyor
    if (psm.get_var(SIGNALS["R1_CONV_2_BIN_PRESENT"]) and
            state.bin_locations["receiving"] is not None):

        bin_num = state.bin_locations["receiving"]

        # Check if bin selection is active - if so, don't start a return operation
        bin_address = BIN_ADDRESSES.get(bin_num)
        if bin_address and psm.get_var(bin_address):
            logger.info(
                f"Bin {bin_num} is still selected, not initiating return to storage")
            return

        logger.info(
            f"Detected bin {bin_num} on RECEIVING return conveyor, initiating return to STORAGE")

        # Clear the bin present flag to prevent repeated detection
        psm.set_var(SIGNALS["R1_CONV_2_BIN_PRESENT"], False)

        start_operation("from_receiving", bin_num)

    # Check assembly return conveyor
    if (psm.get_var(SIGNALS["R3_CONV_4_BIN_PRESENT"]) and
            state.bin_locations["assembly"] is not None):

        bin_num = state.bin_locations["assembly"]

        # Check if bin selection is active - if so, don't start a return operation
        bin_address = BIN_ADDRESSES.get(bin_num)
        if bin_address and psm.get_var(bin_address):
            logger.info(
                f"Bin {bin_num} is still selected, not initiating return to storage")
            return

        logger.info(
            f"Detected bin {bin_num} on ASSEMBLY return conveyor, initiating return to STORAGE")

        # Clear the bin present flag to prevent repeated detection
        psm.set_var(SIGNALS["R3_CONV_4_BIN_PRESENT"], False)

        start_operation("from_assembly", bin_num)


def update_inputs():
    """Handle input updates on PLC cycle"""
    if not state.cycle_running:
        logger.warning("PLC cycle not running, skipping input updates")
        return

    # Direct check for PICK_BIN_01 and TO_RECEIVING_STA_1 signals
    # This ensures we always detect these signals regardless of other state
    bin_01_active = psm.get_var(BIN_ADDRESSES[1])  # PICK_BIN_01
    to_receiving_active = psm.get_var(SIGNALS["TO_RECEIVING_STA_1"])
    in_process_active = psm.get_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"])

    # Log any changes to these critical signals
    static_vars = getattr(update_inputs, "static_vars", {
                          "prev_bin_01": None, "prev_to_receiving": None, "prev_in_process": None})
    update_inputs.static_vars = static_vars

    if static_vars["prev_bin_01"] is None:
        static_vars["prev_bin_01"] = bin_01_active
        logger.info(f"Initial PICK_BIN_01 state: {bin_01_active}")
    elif bin_01_active != static_vars["prev_bin_01"]:
        logger.info(
            f"PICK_BIN_01 changed from {static_vars['prev_bin_01']} to {bin_01_active}")
        static_vars["prev_bin_01"] = bin_01_active

    if static_vars["prev_to_receiving"] is None:
        static_vars["prev_to_receiving"] = to_receiving_active
        logger.info(f"Initial TO_RECEIVING_STA_1 state: {to_receiving_active}")
    elif to_receiving_active != static_vars["prev_to_receiving"]:
        logger.info(
            f"TO_RECEIVING_STA_1 changed from {static_vars['prev_to_receiving']} to {to_receiving_active}")
        static_vars["prev_to_receiving"] = to_receiving_active

    if static_vars["prev_in_process"] is None:
        static_vars["prev_in_process"] = in_process_active
        logger.info(
            f"Initial PICK_TO_RECEIVING_IN_PROCESS state: {in_process_active}")
    elif in_process_active != static_vars["prev_in_process"]:
        logger.info(
            f"PICK_TO_RECEIVING_IN_PROCESS changed from {static_vars['prev_in_process']} to {in_process_active}")
        static_vars["prev_in_process"] = in_process_active

    # If both input signals are active but in_process is not, directly set it
    if bin_01_active and to_receiving_active and not in_process_active:
        logger.warning(
            "CRITICAL: PICK_BIN_01 and TO_RECEIVING_STA_1 are both TRUE, but PICK_TO_RECEIVING_IN_PROCESS is not TRUE")
        logger.info("Directly setting PICK_TO_RECEIVING_IN_PROCESS to TRUE")
        psm.set_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"], True)

        # Verify it was set
        in_process_active = psm.get_var(
            SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"])
        if in_process_active:
            logger.info(
                "Successfully set PICK_TO_RECEIVING_IN_PROCESS to TRUE")
        else:
            logger.error("Failed to set PICK_TO_RECEIVING_IN_PROCESS to TRUE")
            # Try a different approach - set the flag directly in the PSM
            try:
                logger.info(
                    "Trying alternative method to set PICK_TO_RECEIVING_IN_PROCESS")
                # Direct address for PICK_TO_RECEIVING_IN_PROCESS
                psm.set_var("IX0.5", True)
                in_process_active = psm.get_var("IX0.5")
                logger.info(
                    f"Direct set result: PICK_TO_RECEIVING_IN_PROCESS = {in_process_active}")
            except Exception as e:
                logger.error(
                    f"Error setting PICK_TO_RECEIVING_IN_PROCESS directly: {str(e)}")

    if bin_01_active and to_receiving_active:
        logger.info("Detected PICK_BIN_01 and TO_RECEIVING_STA_1 both active")

        # Check if we're already in an operation
        if state.current_operation:
            logger.info(
                f"Already in operation: {state.current_operation}, not starting new operation")
        else:
            # Force start the to_receiving operation for bin 1
            logger.info("Forcing start of to_receiving operation for bin 1")
            clear_error_state()  # Clear any previous errors
            start_operation("to_receiving", 1)
            start_operation("to_receiving", 1)

    # Check for active operation
    if state.current_operation:
        # Check for random errors
        if random.random() < ERROR_CHANCE:
            set_error_state()
            return

        # For to_receiving operation, check if PICK_BIN_01 and TO_RECEIVING_STA_1 have been reset
        if state.current_operation == "to_receiving":
            bin_num = state.selected_bin
            if bin_num == 1:  # Only for bin 01
                bin_address = BIN_ADDRESSES[bin_num]
                bin_signal_active = psm.get_var(bin_address)
                to_receiving_active = psm.get_var(
                    SIGNALS["TO_RECEIVING_STA_1"])

                # If both signals are now off, complete the operation
                if not bin_signal_active and not to_receiving_active:
                    logger.info(
                        "PICK_BIN_01 and TO_RECEIVING_STA_1 have been reset, completing operation")
                    complete_operation()
                    return
                # Otherwise, continue waiting (don't use timeout for this specific case)
                return

        # For other operations, use the standard timeout
        if time.time() - state.operation_start_time >= OPERATION_TIMEOUT:
            complete_operation()
            return

    else:
        # Simulate operator actions
        simulate_operator_actions()

        # Check return conveyors
        check_bin_return_conveyors()

        # Look for new operation from ERP
        bin_num = handle_bin_selection()
        if bin_num:
            # Check if this bin is already at a location
            bin_already_at_location = False
            for location, located_bin in state.bin_locations.items():
                if located_bin == bin_num:
                    bin_already_at_location = True
                    logger.info(
                        f"Bin {bin_num} is already at location {location}, not starting new operation")
                    break

            if not bin_already_at_location:
                logger.info(
                    f"Bin {bin_num} selected, checking for station operation")
                operation = handle_station_selection()
                if operation:
                    logger.info(
                        f"Operation {operation} detected, starting operation")
                    clear_error_state()  # Clear any previous errors
                    start_operation(operation, bin_num)
                else:
                    debug_log(
                        f"No station operation detected for bin {bin_num}")


def update_outputs():
    """Handle output updates on PLC cycle"""
    # Update cycle status indicators
    if state.cycle_running:
        psm.set_var("IX0.0", False)  # PLC_CYCLE_STOPPED
        psm.set_var(SIGNALS["PLC_CYCLE_RUNNING"], True)
    else:
        psm.set_var("IX0.0", True)  # PLC_CYCLE_STOPPED
        psm.set_var(SIGNALS["PLC_CYCLE_RUNNING"], False)


def handle_commands():
    """Check for any special commands"""
    # We'll use an analog output register (MW0) for commands:
    # 1 = Start Cycle
    # 2 = Stop Cycle
    # 3 = Clear Error
    command = psm.get_var("MW0")

    # Log the command value for debugging
    if command != 0:
        debug_log(f"Command register value: {command}")

    if command == 1 and not state.cycle_running:
        logger.info("Starting PLC cycle")
        state.cycle_running = True
    elif command == 2 and state.cycle_running:
        logger.info("Stopping PLC cycle")
        state.cycle_running = False
        clear_operation_flags()
    elif command == 3 and state.error_state:
        logger.info("Clearing error state")
        clear_error_state()

    # Clear command
    if command != 0:
        debug_log(f"Clearing command register from {command} to 0")
        psm.set_var("MW0", 0)


# Debug function to dump all signal values
def debug_dump_signals():
    """Dump all signal values for debugging"""
    # Always log critical signals regardless of DEBUG_MODE
    bin_01_active = psm.get_var(BIN_ADDRESSES[1])  # PICK_BIN_01
    to_receiving_active = psm.get_var(SIGNALS["TO_RECEIVING_STA_1"])
    in_process_active = psm.get_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"])

    logger.info(
        f"CRITICAL SIGNALS - PICK_BIN_01: {bin_01_active}, TO_RECEIVING_STA_1: {to_receiving_active}, PICK_TO_RECEIVING_IN_PROCESS: {in_process_active}")

    # If both input signals are active but in_process is not, log a warning
    if bin_01_active and to_receiving_active and not in_process_active:
        logger.warning(
            "ISSUE DETECTED: PICK_BIN_01 and TO_RECEIVING_STA_1 are both TRUE, but PICK_TO_RECEIVING_IN_PROCESS is not TRUE")

        # Force set the in-process flag
        logger.info("Forcing PICK_TO_RECEIVING_IN_PROCESS to TRUE")
        psm.set_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"], True)

    # Skip detailed dump if not in debug mode
    if not DEBUG_MODE:
        return

    logger.debug("Current Signal Values:")
    logger.debug("-" * 40)

    # Input signals
    logger.debug("Input Signals (From PLC to ERP):")
    for name, address in SIGNALS.items():
        if name.startswith("TO_") or name.startswith("FROM_"):
            continue  # Skip output signals
        value = psm.get_var(address)
        logger.debug(f"  {name}: {value}")

    # Output signals
    logger.debug("Output Signals (From ERP to PLC):")
    for name, address in SIGNALS.items():
        if name.startswith("TO_") or name.startswith("FROM_"):
            value = psm.get_var(address)
            logger.debug(f"  {name}: {value}")

    # Bin selections
    logger.debug("Bin Selections:")
    for bin_num, address in BIN_ADDRESSES.items():
        value = psm.get_var(address)
        logger.debug(f"  Bin {bin_num}: {value}")

    # Command register
    command = psm.get_var("MW0")
    logger.debug(f"Command Register (MW0): {command}")
    logger.debug("-" * 40)


# Initialize state
state = PLCState()
# Set cycle running to True by default
state.cycle_running = True

if __name__ == "__main__":
    hardware_init()
    logger.info("Starting main PLC cycle")

    # Explicitly set PLC_CYCLE_RUNNING to True
    psm.set_var(SIGNALS["PLC_CYCLE_RUNNING"], True)
    logger.info("PLC cycle running flag set to TRUE")

    # Debug variables
    last_debug_time = time.time()
    debug_interval = 5  # Dump debug info every 5 seconds

    while not psm.should_quit():
        handle_commands()

        # Check if cycle is running and log if not
        if not state.cycle_running:
            logger.error("PLC cycle not running! Setting it to running...")
            state.cycle_running = True
            psm.set_var(SIGNALS["PLC_CYCLE_RUNNING"], True)

        update_inputs()
        update_outputs()

        # Periodically dump all signal values for debugging
        current_time = time.time()
        if current_time - last_debug_time >= debug_interval:
            debug_dump_signals()
            last_debug_time = current_time

        time.sleep(0.1)  # 100ms cycle time

    logger.info("Shutting down PLC simulator")
    psm.stop()
