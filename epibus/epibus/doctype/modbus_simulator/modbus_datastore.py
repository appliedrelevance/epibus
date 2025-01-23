# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import threading
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import DatastoreException

logger = get_logger(__name__)


class DatastoreManager:
    """Manages Modbus datastore operations and state"""

    # Default block sizes
    BLOCK_SIZES = {
        "coils": 1000,
        "discrete_inputs": 1000,
        "holding_registers": 1000,
        "input_registers": 1000,
    }

    def __init__(self, simulator_doc):
        """Initialize datastore manager

        Args:
            simulator_doc: Parent ModbusSimulator document
        """
        self.doc = simulator_doc
        self.store = None
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self):
        """Initialize or reinitialize the datastore

        Returns:
            ModbusServerContext: Server context for Modbus server

        Raises:
            DatastoreException: If initialization fails
        """
        try:
            with self._lock:
                # Create data blocks
                coils = ModbusSequentialDataBlock(
                    0, [False] * self.BLOCK_SIZES["coils"]
                )
                discrete_inputs = ModbusSequentialDataBlock(
                    0, [False] * self.BLOCK_SIZES["discrete_inputs"]
                )
                holding_registers = ModbusSequentialDataBlock(
                    0, [0] * self.BLOCK_SIZES["holding_registers"]
                )
                input_registers = ModbusSequentialDataBlock(
                    0, [0] * self.BLOCK_SIZES["input_registers"]
                )

                # Create slave context
                self.store = ModbusSlaveContext(
                    di=discrete_inputs,
                    co=coils,
                    hr=holding_registers,
                    ir=input_registers,
                )

                context = ModbusServerContext(slaves=self.store, single=True)
                self._initialized = True

                if self.doc.debug_mode:
                    self._log_datastore_state()

                return context

        except Exception as e:
            error_msg = f"Failed to initialize datastore: {str(e)}"
            logger.error(error_msg)
            raise DatastoreException(error_msg)

    def cleanup(self):
        """Clean up datastore resources"""
        with self._lock:
            self.store = None
            self._initialized = False

    def get_value(self, block_type, address):
        """Read a value from the datastore

        Args:
            block_type: Type of data block ('co', 'di', 'hr', 'ir')
            address: Modbus address to read

        Returns:
            Value from datastore

        Raises:
            DatastoreException: If read fails
        """
        self._check_initialized()

        try:
            with self._lock:
                values = self.store.getValues(block_type, address, 1)

                if self.doc.debug_mode:
                    logger.debug(f"Read {block_type}[{address}] = {values[0]}")

                return values[0]

        except Exception as e:
            error_msg = f"Failed to read {block_type}[{address}]: {str(e)}"
            logger.error(error_msg)
            raise DatastoreException(error_msg)

    def set_value(self, block_type, address, value):
        """Write a value to the datastore

        Args:
            block_type: Type of data block ('co', 'di', 'hr', 'ir')
            address: Modbus address to write
            value: Value to write

        Raises:
            DatastoreException: If write fails
        """
        self._check_initialized()

        try:
            with self._lock:
                self.store.setValues(block_type, address, [value])

                if self.doc.debug_mode:
                    logger.debug(f"Wrote {block_type}[{address}] = {value}")

        except Exception as e:
            error_msg = f"Failed to write {block_type}[{address}]: {str(e)}"
            logger.error(error_msg)
            raise DatastoreException(error_msg)

    def reset_blocks(self):
        """Reset all data blocks to default values"""
        self._check_initialized()

        try:
            with self._lock:
                # Reset coils and discrete inputs to False
                for block_type in ["co", "di"]:
                    for addr in range(self.BLOCK_SIZES["coils"]):
                        self.store.setValues(block_type, addr, [False])

                # Reset registers to 0
                for block_type in ["hr", "ir"]:
                    for addr in range(self.BLOCK_SIZES["holding_registers"]):
                        self.store.setValues(block_type, addr, [0])

                if self.doc.debug_mode:
                    logger.debug("Reset all data blocks to defaults")

        except Exception as e:
            error_msg = f"Failed to reset data blocks: {str(e)}"
            logger.error(error_msg)
            raise DatastoreException(error_msg)

    def _check_initialized(self):
        """Check if datastore is initialized

        Raises:
            DatastoreException: If not initialized
        """
        if not self._initialized or not self.store:
            raise DatastoreException("Datastore not initialized")

    def _log_datastore_state(self):
        """Log current state of data blocks for debugging"""
        logger.debug("Datastore initialized with:")
        logger.debug(f"  Coils: {self.BLOCK_SIZES['coils']}")
        logger.debug(f"  Discrete Inputs: {self.BLOCK_SIZES['discrete_inputs']}")
        logger.debug(f"  Holding Registers: {self.BLOCK_SIZES['holding_registers']}")
        logger.debug(f"  Input Registers: {self.BLOCK_SIZES['input_registers']}")
