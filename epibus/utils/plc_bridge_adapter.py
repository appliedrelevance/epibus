# -*- coding: utf-8 -*-
# Copyright (c) 2023, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from epibus.utils.plc_redis_client import PLCRedisClient
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)


def get_signals_from_plc_bridge():
    """Get signals from PLC Bridge instead of directly from Modbus"""
    try:
        client = PLCRedisClient.get_instance()
        signals = client.get_signals()
        logger.info(f"✅ Retrieved {len(signals)} signals from PLC Bridge")
        return signals
    except Exception as e:
        logger.error(f"❌ Error getting signals from PLC Bridge: {str(e)}")
        return []


def write_signal_via_plc_bridge(signal_id, value):
    """Write signal via PLC Bridge instead of directly to Modbus"""
    try:
        client = PLCRedisClient.get_instance()
        result = client.write_signal(signal_id, value)
        if result:
            logger.info(
                f"✅ Successfully wrote signal {signal_id} = {value} via PLC Bridge")
        else:
            logger.warning(
                f"⚠️ Failed to write signal {signal_id} = {value} via PLC Bridge")
        return result
    except Exception as e:
        logger.error(f"❌ Error writing signal via PLC Bridge: {str(e)}")
        return False
