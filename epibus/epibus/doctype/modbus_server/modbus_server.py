import asyncio
import frappe
from frappe.model.document import Document
from epibus.epibus.background_jobs.modbus_server_jobs import check_server_status


class ModbusServer(Document):
    @frappe.whitelist()
    def start_server(self):
        """
        Enqueue a background job to start the Modbus TCP server.
        """
        if self.server_status in ["Running", "Starting"]:
            frappe.msgprint("Server is already running or starting.")
            return

        frappe.enqueue(
            "epibus.epibus.epibus.background_jobs.modbus_server_jobs.start_server",
            queue="long",
            timeout=600,
            is_async=True,
        )
        self.db_set("server_status", "Starting")
        frappe.msgprint("Server starting...")

    @frappe.whitelist()
    def stop_server(self):
        """
        Enqueue a background job to stop the Modbus TCP server.
        """
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
        frappe.msgprint("Server stopping...")

    @frappe.whitelist()
    def update_status(self):
        """
        Updates the 'server_status' field based on the actual status of the Modbus server.
        """
        hostname = self.hostname
        port = self.port

        async def async_check_status():
            is_running = await check_server_status(hostname, port)
            new_status = "Running" if is_running else "Stopped"
            if self.server_status != new_status:
                self.db_set("server_status", new_status)
                frappe.db.commit()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_check_status())
