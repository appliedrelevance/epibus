import psm  # type: ignore
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Key addresses from the original file
BIN_1_ADDRESS = "QX1.3"  # PICK_BIN_01
PICK_TO_RECEIVING_IN_PROCESS = "IX0.5"
PICK_TO_RECEIVING_COMPLETE = "IX0.6"


def hardware_init():
    """Initialize the PSM hardware layer"""
    logger.info("Initializing Beachside PLC minimal simulator...")
    psm.start()
    # Reset all signals we'll be using
    psm.set_var(PICK_TO_RECEIVING_IN_PROCESS, False)
    psm.set_var(PICK_TO_RECEIVING_COMPLETE, False)
    logger.info("PLC simulator initialized and ready")


def reset_signals():
    """Reset all signals that we set"""
    logger.info("Resetting all signals")
    psm.set_var(PICK_TO_RECEIVING_IN_PROCESS, False)
    psm.set_var(PICK_TO_RECEIVING_COMPLETE, False)


def main_loop():
    """Main processing loop"""
    logger.info("Starting main loop - waiting for bin 1 to be set")

    # Track previous bin state to detect changes
    previous_bin_state = False

    while not psm.should_quit():
        # Check bin 1 state
        current_bin_state = psm.get_var(BIN_1_ADDRESS)

        # If bin 1 just got set (changed from False to True)
        if current_bin_state and not previous_bin_state:
            logger.info("Bin 1 has been set!")

            # Wait 10 seconds
            logger.info(
                "Waiting 10 seconds before setting PICK_TO_RECEIVING_IN_PROCESS...")
            time.sleep(10)

            # Set PICK_TO_RECEIVING_IN_PROCESS
            logger.info("Setting PICK_TO_RECEIVING_IN_PROCESS")
            psm.set_var(PICK_TO_RECEIVING_IN_PROCESS, True)

            # Wait another 10 seconds
            logger.info(
                "Waiting 10 seconds before setting PICK_TO_RECEIVING_COMPLETE...")
            time.sleep(10)

            # Set PICK_TO_RECEIVING_COMPLETE
            logger.info("Setting PICK_TO_RECEIVING_COMPLETE")
            psm.set_var(PICK_TO_RECEIVING_COMPLETE, True)

            # Reset all signals we set
            logger.info("Waiting 2 seconds before resetting signals...")
            time.sleep(2)
            reset_signals()

            logger.info(
                "Cycle complete - waiting for bin 1 to be reset and set again")

        # Update previous state
        previous_bin_state = current_bin_state

        # Small delay to prevent CPU hogging
        time.sleep(0.1)


if __name__ == "__main__":
    hardware_init()
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        logger.info("Shutting down PLC simulator")
        psm.stop()
