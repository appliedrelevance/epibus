import os
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables or defaults"""
    # Default configuration
    config = {
        "poll_interval": float(os.environ.get("PLC_POLL_INTERVAL", 1.0)),
        "log_level": os.environ.get("PLC_LOG_LEVEL", "INFO"),
        "frappe_url": os.environ.get("FRAPPE_URL", "http://localhost:8000"),
        "sse_host": os.environ.get("SSE_HOST", "0.0.0.0"),
        "sse_port": int(os.environ.get("SSE_PORT", 7654))
    }
    
    return config