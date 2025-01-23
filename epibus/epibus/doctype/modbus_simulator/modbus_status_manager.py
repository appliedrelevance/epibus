# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime
from frappe.utils import now_datetime
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import StatusException

logger = get_logger(__name__)


class StatusManager:
    """Manages simulator status updates and notifications"""

    VALID_STATES = ["Stopped", "Starting", "Running", "Stopping", "Error"]

    def __init__(self, simulator_doc):
        """Initialize with parent simulator document

        Args:
            simulator_doc: Parent ModbusSimulator document
        """
        self.doc = simulator_doc
        self.start_time = None
        self._update_in_progress = False

    def update(self, status, message=None):
        """Update simulator status and notify

        Args:
            status: New status string
            message: Optional status message

        Raises:
            StatusException: If update fails
        """
        if status not in self.VALID_STATES:
            raise StatusException(f"Invalid status: {status}")

        try:
            if self._update_in_progress:
                logger.warning(f"Status update already in progress for {status}")
                return

            self._update_in_progress = True

            try:
                self._update_fields(status, message)
                self._notify_update(status, message)
                frappe.db.commit()

            finally:
                self._update_in_progress = False

        except Exception as e:
            logger.error(f"Status update failed: {str(e)}")
            raise StatusException(f"Failed to update status: {str(e)}")

    def error(self, message):
        """Set error status with message

        Args:
            message: Error message to store
        """
        self.update("Error", message)

    def start_timing(self):
        """Start uptime timer"""
        self.start_time = datetime.now()

    def stop_timing(self):
        """Stop uptime timer"""
        self.start_time = None

    def get_uptime(self):
        """Get current uptime in seconds

        Returns:
            float: Uptime in seconds, or 0 if not running
        """
        if not self.start_time:
            return 0.0

        delta = now_datetime() - self.start_time
        return delta.total_seconds()

    def _update_fields(self, status, message=None):
        """Update document fields for status change

        Args:
            status: New status string
            message: Optional status message
        """
        logger.debug(f"Updating status to: {status}")

        # Update status field
        self.doc.db_set("server_status", status, update_modified=False)

        # Update timing
        if status == "Running":
            self.start_timing()
            self.doc.db_set("last_status_update", now_datetime(), update_modified=False)
            self.doc.db_set("enabled", 1, update_modified=False)
        else:
            self.stop_timing()

        # Update error message
        self.doc.db_set(
            "error_message",
            message if status == "Error" else None,
            update_modified=False,
        )

        # Update computed fields
        self.doc.db_set(
            "server_uptime", float(self.get_uptime()), update_modified=False
        )
        self.doc.db_set(
            "active_connections", 1 if status == "Running" else 0, update_modified=False
        )
        self.doc.db_set(
            "docstatus", 1 if status == "Running" else 0, update_modified=False
        )

    def _notify_update(self, status, message=None):
        """Send realtime notification of status change

        Args:
            status: New status string
            message: Optional status message
        """
        frappe.publish_realtime(
            "simulator_status_update",
            {
                "name": self.doc.name,
                "status": status,
                "message": message,
                "uptime": self.get_uptime(),
            },
            doctype="Modbus Simulator",
            docname=self.doc.name,
        )
