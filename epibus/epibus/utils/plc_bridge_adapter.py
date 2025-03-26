# -*- coding: utf-8 -*-
# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from typing import Dict, List, Any, Optional, Union, cast
import requests
import json
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

def get_signals_from_plc_bridge() -> List[Dict[str, Any]]:
    """
    Get signals from the PLC Bridge.
    
    This adapter function provides compatibility with the new PLC Bridge architecture.
    It fetches signals using the API endpoint provided by the new PLC Bridge.
    
    Returns:
        List[Dict[str, Any]]: A list of signals with their current values.
    """
    try:
        logger.info("Fetching signals from PLC Bridge via adapter...")
        
        # Use the API endpoint to get all signals
        response = frappe.call("epibus.epibus.api.plc.get_all_signals")
        
        if not response or not response.get("success", False):
            error_msg = response.get("message", "Unknown error") if response else "No response from PLC Bridge"
            logger.error(f"Failed to get signals from PLC Bridge: {error_msg}")
            return []
        
        # Extract signals from all connections
        all_signals = []
        for connection in response.get("data", []):
            signals = connection.get("signals", [])
            all_signals.extend(signals)
        
        logger.info(f"Successfully retrieved {len(all_signals)} signals from PLC Bridge")
        return all_signals
        
    except Exception as e:
        logger.error(f"Error in get_signals_from_plc_bridge: {str(e)}")
        return []

def write_signal_via_plc_bridge(signal_id: str, value: Any) -> bool:
    """
    Write a signal value via the PLC Bridge.
    
    This adapter function provides compatibility with the new PLC Bridge architecture.
    It writes signal values using the API endpoint provided by the new PLC Bridge.
    
    Args:
        signal_id (str): The ID of the signal to update.
        value (Any): The new value for the signal.
        
    Returns:
        bool: True if the write was successful, False otherwise.
    """
    try:
        logger.info(f"Writing signal {signal_id} = {value} via PLC Bridge adapter...")
        
        # Use the API endpoint to update the signal
        # We'll use the existing update_signal method from the API
        response = frappe.call(
            "epibus.epibus.api.plc.update_signal",
            signal_id=signal_id,
            value=value
        )
        
        if not response or not response.get("success", False):
            error_msg = response.get("message", "Unknown error") if response else "No response from PLC Bridge"
            logger.error(f"Failed to write signal via PLC Bridge: {error_msg}")
            return False
        
        logger.info(f"Successfully wrote signal {signal_id} = {value} via PLC Bridge")
        return True
        
    except Exception as e:
        logger.error(f"Error in write_signal_via_plc_bridge: {str(e)}")
        return False