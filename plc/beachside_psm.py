import psm  # type: ignore
import time
import random

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
ERROR_CHANCE = 0.05   # 5% chance of error per operation
WAIT_TIMEOUT_SECS = 60  # Default timeout for waiting for signals

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
    print("🔧 Initializing Beachside PLC simulator...")
    psm.start()
    # Start with cycle stopped
    psm.set_var("IX0.0", True)  # PLC_CYCLE_STOPPED
    psm.set_var(SIGNALS["PLC_CYCLE_RUNNING"], False)
    print("✅ PLC simulator initialized and ready")


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
            print(f"📦 Bin {bin_num:02d} turned {status}")

        # Return the first active bin
        if current_state:
            active_bins.append(bin_num)
            if selected_bin is None:
                selected_bin = bin_num

    # Debug: Print active bins if any
    if active_bins:
        print(f"🔍 DEBUG: Active bins detected: {active_bins}")

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

    # Check for changes and print only if changed
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

    # Print only if any signal changed
    if signals_changed and changes:
        print(f"🔍 Station signals changed: {', '.join(changes)}")

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
    print("❌ Error detected in operation!")
    state.error_state = True
    psm.set_var(SIGNALS["PICK_ERROR"], True)
    clear_operation_flags()
    state.current_operation = None


def clear_error_state():
    """Clear error state"""
    state.error_state = False
    psm.set_var(SIGNALS["PICK_ERROR"], False)


def start_operation(operation: str, bin_num: int):
    """Start a new robot operation"""
    state.current_operation = operation
    state.operation_start_time = time.time()
    state.selected_bin = bin_num

    # Set appropriate in-process flag based on operation
    if operation == "to_receiving":
        print(
            f"🏭 Starting movement from STORAGE to RECEIVING with bin {bin_num}")
        psm.set_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"], True)
        # Update bin location
        state.bin_locations["storage"] = None
        state.bin_locations["receiving"] = bin_num

    elif operation == "from_receiving":
        print(
            f"🏭 Starting movement from RECEIVING to STORAGE with bin {bin_num}")
        psm.set_var(SIGNALS["PICK_TO_STORAGE_IN_PROCESS"], True)
        # Update bin location
        state.bin_locations["receiving"] = None
        state.bin_locations["storage"] = bin_num

    elif operation == "to_assembly":
        print(
            f"🏭 Starting movement from STORAGE to ASSEMBLY with bin {bin_num}")
        psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_IN_PROCESS"], True)
        # Update bin location
        state.bin_locations["storage"] = None
        state.bin_locations["assembly"] = bin_num

    elif operation == "from_assembly":
        print(
            f"🏭 Starting movement from ASSEMBLY to STORAGE with bin {bin_num}")
        psm.set_var(SIGNALS["PICK_TO_STORAGE_IN_PROCESS"], True)
        # Update bin location
        state.bin_locations["assembly"] = None
        state.bin_locations["storage"] = bin_num


def complete_operation():
    """Complete the current operation"""
    # Set completion flag based on operation
    if state.current_operation == "to_receiving":
        print(
            f"✅ Completed movement to RECEIVING with bin {state.selected_bin}")
        psm.set_var(SIGNALS["PICK_TO_RECEIVING_IN_PROCESS"], False)
        psm.set_var(SIGNALS["PICK_TO_RECEIVING_COMPLETE"], True)
        # Simulate bin present on receiving conveyor
        time.sleep(0.5)  # Small delay to simulate operator action
        psm.set_var(SIGNALS["R1_CONV_2_BIN_PRESENT"], True)

    elif state.current_operation == "from_receiving":
        print(
            f"✅ Completed movement from RECEIVING to STORAGE with bin {state.selected_bin}")
        psm.set_var(SIGNALS["PICK_TO_STORAGE_IN_PROCESS"], False)
        psm.set_var(SIGNALS["PICK_TO_STORAGE_COMPLETE"], True)
        # Clear bin present on receiving conveyor
        psm.set_var(SIGNALS["R1_CONV_2_BIN_PRESENT"], False)

    elif state.current_operation == "to_assembly":
        print(
            f"✅ Completed movement to ASSEMBLY with bin {state.selected_bin}")
        psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_IN_PROCESS"], False)
        psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_COMPLETE"], True)
        # Simulate bin present on assembly conveyor
        time.sleep(0.5)  # Small delay to simulate operator action
        psm.set_var(SIGNALS["R3_CONV_4_BIN_PRESENT"], True)

    elif state.current_operation == "from_assembly":
        print(
            f"✅ Completed movement from ASSEMBLY to STORAGE with bin {state.selected_bin}")
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
            print(
                f"👨‍🔧 Operator placed bin {bin_num} on return conveyor from RECEIVING")
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
            print(
                f"👨‍🔧 Operator placed bin {bin_num} on return conveyor from ASSEMBLY")
            psm.set_var(SIGNALS["R3_CONV_4_BIN_PRESENT"], True)
            # Clear completion flag as we're starting a new phase
            psm.set_var(SIGNALS["PICK_TO_ASSEMBLY_COMPLETE"], False)


def check_bin_return_conveyors():
    """Check if bins are present on return conveyors and initiate return to storage"""
    # Check receiving return conveyor
    if (psm.get_var(SIGNALS["R1_CONV_2_BIN_PRESENT"]) and
        not state.current_operation and
            state.bin_locations["receiving"] is not None):

        bin_num = state.bin_locations["receiving"]
        print(
            f"🔄 Detected bin {bin_num} on RECEIVING return conveyor, initiating return to STORAGE")
        start_operation("from_receiving", bin_num)

    # Check assembly return conveyor
    if (psm.get_var(SIGNALS["R3_CONV_4_BIN_PRESENT"]) and
        not state.current_operation and
            state.bin_locations["assembly"] is not None):

        bin_num = state.bin_locations["assembly"]
        print(
            f"🔄 Detected bin {bin_num} on ASSEMBLY return conveyor, initiating return to STORAGE")
        start_operation("from_assembly", bin_num)


def update_inputs():
    """Handle input updates on PLC cycle"""
    if not state.cycle_running:
        return

    # Check for active operation
    if state.current_operation:
        # Check for random errors
        if random.random() < ERROR_CHANCE:
            set_error_state()
            return

        # Check if operation is complete
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
            print(
                f"🔍 DEBUG: Bin {bin_num} selected, checking for station operation")
            operation = handle_station_selection()
            if operation:
                print(
                    f"🔍 DEBUG: Operation {operation} detected, starting operation")
                clear_error_state()  # Clear any previous errors
                start_operation(operation, bin_num)
            else:
                print(
                    f"🔍 DEBUG: No station operation detected for bin {bin_num}")


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

    # Always print the command value for debugging
    if command != 0:
        print(f"🔍 DEBUG: Command register value: {command}")

    if command == 1 and not state.cycle_running:
        print("▶️ Starting PLC cycle")
        state.cycle_running = True
    elif command == 2 and state.cycle_running:
        print("⏹️ Stopping PLC cycle")
        state.cycle_running = False
        clear_operation_flags()
    elif command == 3 and state.error_state:
        print("🔄 Clearing error state")
        clear_error_state()

    # Clear command
    if command != 0:
        print(f"🔍 DEBUG: Clearing command register from {command} to 0")
        psm.set_var("MW0", 0)


# Debug function to dump all signal values
def debug_dump_signals():
    """Dump all signal values for debugging"""
    print("\n🔍 DEBUG: Current Signal Values:")
    print("-" * 40)

    # Input signals
    print("Input Signals (From PLC to ERP):")
    for name, address in SIGNALS.items():
        if name.startswith("TO_") or name.startswith("FROM_"):
            continue  # Skip output signals
        value = psm.get_var(address)
        print(f"  {name}: {value}")

    # Output signals
    print("\nOutput Signals (From ERP to PLC):")
    for name, address in SIGNALS.items():
        if name.startswith("TO_") or name.startswith("FROM_"):
            value = psm.get_var(address)
            print(f"  {name}: {value}")

    # Bin selections
    print("\nBin Selections:")
    for bin_num, address in BIN_ADDRESSES.items():
        value = psm.get_var(address)
        print(f"  Bin {bin_num}: {value}")

    # Command register
    command = psm.get_var("MW0")
    print(f"\nCommand Register (MW0): {command}")
    print("-" * 40)


# Initialize state
state = PLCState()

if __name__ == "__main__":
    hardware_init()
    print("🔄 Starting main PLC cycle")

    # Debug variables
    last_debug_time = time.time()
    debug_interval = 5  # Dump debug info every 5 seconds

    while not psm.should_quit():
        handle_commands()
        update_inputs()
        update_outputs()

        # Periodically dump all signal values for debugging
        current_time = time.time()
        if current_time - last_debug_time >= debug_interval:
            debug_dump_signals()
            last_debug_time = current_time

        time.sleep(0.1)  # 100ms cycle time

    print("👋 Shutting down PLC simulator")
    psm.stop()
