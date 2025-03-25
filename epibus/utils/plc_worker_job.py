import frappe
import time
from frappe.utils.background_jobs import enqueue
from epibus.epibus.utils.plc_worker import PLCWorker

def start_plc_worker():
    """Start the PLC worker job"""
    # Enqueue the long-running worker job in the 'plc' queue
    enqueue(
        'epibus.epibus.utils.plc_worker_job.run_plc_worker',
        queue='plc',
        timeout=None  # Long-running job
    )
    frappe.logger().info("🚀 Enqueued PLC worker job")

def run_plc_worker():
    """Run the PLC worker as a long-running job"""
    try:
        frappe.logger().info("🚀 Starting PLC worker")
        
        # Initialize the worker
        worker = PLCWorker()
        worker.initialize()
        
        # Connect to the PLC
        if not worker.connect():
            frappe.logger().error("❌ Failed to connect to PLC, retrying in 5 seconds")
            time.sleep(5)
            if not worker.connect():
                frappe.logger().error("❌ Failed to connect to PLC after retry, aborting")
                return
        
        # Load signals
        if not worker.load_signals():
            frappe.logger().error("❌ Failed to load signals, aborting")
            worker.disconnect()
            return
            
        # Set up event handler for commands
        frappe.local.plc_worker = worker
        
        # We'll use the publish_realtime system instead of direct event handlers
        # since frappe.realtime is not available in the worker context
        
        # Main polling loop
        poll_interval = 0.2  # 200ms polling interval for <500ms latency
        
        frappe.logger().info("🔄 Starting main polling loop")
        
        while True:
            # Poll signals
            worker.poll_signals()
            
            # Sleep for the polling interval
            time.sleep(poll_interval)
            
    except frappe.exceptions.RetryBackgroundJobError:
        # Allow Frappe to retry the job
        raise
        
    except Exception as e:
        frappe.logger().error(f"❌ Unhandled exception in PLC worker: {str(e)}")
        
        # Try to clean up
        if 'worker' in locals() and worker:
            worker.disconnect()
            
        # Re-raise to allow Frappe to handle the error
        raise
        
    finally:
        # Clean up
        if 'worker' in locals() and worker:
            worker.disconnect()
            
        frappe.logger().info("🛑 PLC worker stopped")