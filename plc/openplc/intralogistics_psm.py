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


# Operation timeouts in seconds
OPERATION_TIMEOUT = 5  # How long an operation takes
ERROR_CHANCE = 0.05   # 5% chance of error per operation

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


def hardware_init():
    """Initialize the PSM hardware layer"""
    print("🔧 Initializing Beachside PLC simulator...")
    psm.start()
    # Start with cycle stopped
    psm.set_var("IX0.0", True)  # PLC_CYCLE_STOPPED
    print("✅ PLC simulator initialized and ready")


def handle_bin_selection():
    """Check which bin is selected through output coils and log changes"""
    selected_bin = None

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
        if current_state and selected_bin is None:
            selected_bin = bin_num

    return selected_bin


def handle_station_selection():
    """Check which station operation is requested"""
    if psm.get_var("QX4.0"):    # TO_RECEIVING_STA_1
        return "to_receiving"
    elif psm.get_var("QX4.1"):  # FROM_RECEIVING
        return "from_receiving"
    elif psm.get_var("QX4.2"):  # TO_ASSEMBLY_STA_1
        return "to_assembly"
    elif psm.get_var("QX4.3"):  # FROM_ASSEMBLY
        return "from_assembly"
    return None


def clear_operation_flags():
    """Clear all operation in-process and complete flags"""
    # Clear in-process flags
    psm.set_var("IX0.3", False)  # PICK_TO_ASSEMBLY_IN_PROCESS
    psm.set_var("IX0.5", False)  # PICK_TO_RECEIVING_IN_PROCESS
    psm.set_var("IX0.7", False)  # PICK_TO_WAREHOUSE_IN_PROCESS

    # Clear complete flags
    psm.set_var("IX0.4", False)  # PICK_TO_ASSEMBLY_COMPLETE
    psm.set_var("IX0.6", False)  # PICK_TO_RECEIVING_COMPLETE
    psm.set_var("IX1.0", False)  # PICK_TO_WAREHOUSE_COMPLETE


def set_error_state():
    """Set error state and clear operations"""
    print("❌ Error detected in operation!")
    state.error_state = True
    psm.set_var("IX0.2", True)  # PICK_ERROR
    clear_operation_flags()
    state.current_operation = None


def clear_error_state():
    """Clear error state"""
    state.error_state = False
    psm.set_var("IX0.2", False)  # PICK_ERROR


def start_operation(operation: str, bin_num: int):
    """Start a new robot operation"""
    state.current_operation = operation
    state.operation_start_time = time.time()
    state.selected_bin = bin_num

    # Set appropriate in-process flag
    if operation == "to_receiving":
        print(f"🏭 Starting movement to receiving with bin {bin_num}")
        psm.set_var("IX0.5", True)  # PICK_TO_RECEIVING_IN_PROCESS
    elif operation == "from_receiving":
        print(f"🏭 Starting movement from receiving with bin {bin_num}")
        psm.set_var("IX0.7", True)  # PICK_TO_WAREHOUSE_IN_PROCESS
    elif operation == "to_assembly":
        print(f"🏭 Starting movement to assembly with bin {bin_num}")
        psm.set_var("IX0.3", True)  # PICK_TO_ASSEMBLY_IN_PROCESS
    elif operation == "from_assembly":
        print(f"🏭 Starting movement from assembly with bin {bin_num}")
        psm.set_var("IX0.7", True)  # PICK_TO_WAREHOUSE_IN_PROCESS


def complete_operation():
    """Complete the current operation"""
    # Set completion flag based on operation
    if state.current_operation == "to_receiving":
        print(
            f"✅ Completed movement to receiving with bin {state.selected_bin}")
        psm.set_var("IX0.5", False)  # Clear PICK_TO_RECEIVING_IN_PROCESS
        psm.set_var("IX0.6", True)   # Set PICK_TO_RECEIVING_COMPLETE
    elif state.current_operation == "from_receiving":
        print(
            f"✅ Completed movement from receiving with bin {state.selected_bin}")
        psm.set_var("IX0.7", False)  # Clear PICK_TO_WAREHOUSE_IN_PROCESS
        psm.set_var("IX1.0", True)   # Set PICK_TO_WAREHOUSE_COMPLETE
    elif state.current_operation == "to_assembly":
        print(
            f"✅ Completed movement to assembly with bin {state.selected_bin}")
        psm.set_var("IX0.3", False)  # Clear PICK_TO_ASSEMBLY_IN_PROCESS
        psm.set_var("IX0.4", True)   # Set PICK_TO_ASSEMBLY_COMPLETE
    elif state.current_operation == "from_assembly":
        print(
            f"✅ Completed movement from assembly with bin {state.selected_bin}")
        psm.set_var("IX0.7", False)  # Clear PICK_TO_WAREHOUSE_IN_PROCESS
        psm.set_var("IX1.0", True)   # Set PICK_TO_WAREHOUSE_COMPLETE

    # Clear operation state
    state.current_operation = None
    state.selected_bin = None


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
        # Look for new operation
        bin_num = handle_bin_selection()
        if bin_num:
            operation = handle_station_selection()
            if operation:
                clear_error_state()  # Clear any previous errors
                start_operation(operation, bin_num)


def update_outputs():
    """Handle output updates on PLC cycle"""
    # Update cycle status indicators
    if state.cycle_running:
        psm.set_var("IX0.0", False)  # PLC_CYCLE_STOPPED
        psm.set_var("IX0.1", True)   # PLC_CYCLE_RUNNING
    else:
        psm.set_var("IX0.0", True)   # PLC_CYCLE_STOPPED
        psm.set_var("IX0.1", False)  # PLC_CYCLE_RUNNING


def handle_commands():
    """Check for any special commands"""
    # We'll use an analog output register (MW0) for commands:
    # 1 = Start Cycle
    # 2 = Stop Cycle
    # 3 = Clear Error
    command = psm.get_var("MW0")  # Keep using MW0 for multi-value command

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
    psm.set_var("MW0", 0)


# Initialize state
state = PLCState()

if __name__ == "__main__":
    hardware_init()
    print("🔄 Starting main PLC cycle")

    while not psm.should_quit():
        handle_commands()
        update_inputs()
        update_outputs()
        time.sleep(0.1)  # 100ms cycle time

    print("👋 Shutting down PLC simulator")
    psm.stop()
