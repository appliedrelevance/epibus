import asyncio
import frappe
from frappe.model.document import Document
from epibus.epibus.background_jobs.modbus_server_jobs import check_server_status


class ModbusServer(Document):
    def onload(self):
        """
        Check and update the server status when the document is loaded.
        """
        self.update_status()

    @frappe.whitelist()
    def start_server(self):
        """
        Enqueue a background job to start the Modbus TCP server after ensuring it's not already running.
        """
        # Ensure current status is up-to-date
        self.update_status()

        if self.server_status in ["Running", "Starting"]:
            frappe.msgprint("Server is already running or starting.")
            return

        frappe.enqueue(
            "epibus.epibus.background_jobs.modbus_server_jobs.start_server",
            queue="long",
            timeout=600,
            is_async=True,
        )
        self.db_set("server_status", "Starting")
        frappe.db.commit()
        frappe.msgprint("Server starting...")

    @frappe.whitelist()
    def stop_server(self):
        """
        Enqueue a background job to stop the Modbus TCP server after ensuring it is currently running.
        """
        # Ensure current status is up-to-date
        self.update_status()

        if self.server_status not in ["Running"]:
            frappe.msgprint("Server is not running.")
            return

        frappe.enqueue(
            "epibus.epibus.epibus.background_jobs.modbus_server_jobs.stop_server",
            queue="long",
            timeout=300,
            is_async=True,
        )
        self.db_set("server_status", "Stopping")
        frappe.db.commit()
        frappe.msgprint("Server stopping...")

    @frappe.whitelist()
    def update_status(self):
        """
        Updates the 'server_status' field based on the actual status of the Modbus server asynchronously.
        """

        def update_server_status(is_running):
            new_status = "Running" if is_running else "Stopped"
            if self.server_status != new_status:
                self.db_set("server_status", new_status)
                frappe.db.commit()

        async def async_check_status():
            is_running = await check_server_status(self.hostname, self.port)
            frappe.enqueue(
                method=update_server_status,
                is_running=is_running,
                queue="long",
                timeout=300,
                is_async=True,
            )

        # Ensure there is an event loop for the current thread
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as e:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Check if the loop is already running, and handle accordingly
        if loop.is_running():
            # If the loop is running, it's likely part of an async environment; consider alternate handling or queuing
            frappe.enqueue(
                method=async_check_status, queue="long", timeout=300, is_async=True
            )
        else:
            # If not, it's safe to run the event loop for the async operation
            loop.run_until_complete(async_check_status())
