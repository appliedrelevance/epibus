import os
import re
import frappe
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler() # Or use FileHandler if needed
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def after_install():
    """
    This function is called after the epibus app is installed.
    It configures supervisor to manage the PLC bridge process.
    """
    logger.info("Configuring supervisor for PLC Bridge...")

    bench_path = frappe.utils.get_bench_path()
    supervisor_config_dir = os.path.join(bench_path, "config", "supervisor")
    main_supervisor_conf_path = os.path.join(bench_path, "config", "supervisor.conf")
    plc_bridge_conf_path = os.path.join(supervisor_config_dir, "plc_bridge.conf")
    plc_bridge_script_path = os.path.join(bench_path, "apps", "epibus", "plc", "bridge", "start_bridge.sh")
    plc_bridge_dir_path = os.path.join(bench_path, "apps", "epibus", "plc", "bridge")
    logs_dir = os.path.join(bench_path, "logs")
    user = os.environ.get("USER") # Get current user, assuming bench runs as this user

    if not user:
        logger.warning("Could not determine user for supervisor config. Defaulting to 'frappe'.")
        user = "frappe" # Fallback user

    # --- 1. Create plc_bridge.conf ---
    plc_bridge_conf_content = f"""\
[program:bench-frappe-plc-bridge]
command={plc_bridge_script_path}
directory={plc_bridge_dir_path}
user={user}
autostart=true
autorestart=true
stdout_logfile={os.path.join(logs_dir, 'plc_bridge.log')}
stderr_logfile={os.path.join(logs_dir, 'plc_bridge.error.log')}
priority=3
environment=PATH="{os.path.join(bench_path, 'env', 'bin')}:/usr/bin:/bin"
"""
    try:
        os.makedirs(supervisor_config_dir, exist_ok=True)
        with open(plc_bridge_conf_path, "w") as f:
            f.write(plc_bridge_conf_content)
        logger.info(f"Created supervisor config: {plc_bridge_conf_path}")
    except Exception as e:
        logger.error(f"Failed to create {plc_bridge_conf_path}: {e}")
        return # Stop if we can't create the file

    # --- 2. Update supervisor.conf to add PLC bridge to workers group ---
    try:
        if os.path.exists(main_supervisor_conf_path):
            with open(main_supervisor_conf_path, "r") as f:
                content = f.read()
                
            # Check if the workers group exists
            workers_group_pattern = r"\[group:(?:bench-)?frappe-bench-workers\]\nprograms=(.*)"
            workers_group_match = re.search(workers_group_pattern, content)
            
            if workers_group_match:
                # Add plc-bridge to the workers group if not already there
                programs = workers_group_match.group(1)
                if "plc-bridge" not in programs:
                    new_programs = programs.strip() + ",bench-frappe-plc-bridge"
                    updated_content = re.sub(
                        workers_group_pattern,
                        f"[group:frappe-bench-workers]\\nprograms={new_programs}",
                        content
                    )
                    
                    with open(main_supervisor_conf_path, "w") as f:
                        f.write(updated_content)
                    
                    logger.info(f"Added PLC bridge to workers group in {main_supervisor_conf_path}")
                else:
                    logger.info(f"PLC bridge already in workers group in {main_supervisor_conf_path}")
            else:
                logger.warning(f"Could not find workers group in {main_supervisor_conf_path}")

        logger.info("Supervisor configuration for PLC Bridge completed.")
        logger.info("Run 'bench setup supervisor' and 'sudo supervisorctl reread && sudo supervisorctl update' to apply changes.")

    except Exception as e:
        logger.error(f"Failed to update {main_supervisor_conf_path}: {e}")

# Example of how to test this function standalone (remove before deployment)
# if __name__ == "__main__":
#     # Mock frappe.utils for testing outside bench
#     class MockUtils:
#         def get_bench_path(self):
#             # Adjust this path for your local testing environment
#             return "/home/intralogisticsuser/frappe-bench" # Adjusted for current environment
#     frappe.utils = MockUtils()
#     after_install()