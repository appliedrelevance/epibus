#!/usr/bin/env python
# init_redis_client.py - Script to initialize the Redis client

import frappe
from epibus.utils.plc_redis_client import PLCRedisClient


def init_redis_client():
    """Initialize the fixed Redis client in Frappe"""
    print("Initializing fixed Redis client in Frappe...")

    # Initialize the Redis client
    client = PLCRedisClient.get_instance()

    print("Redis client initialized successfully")
    return client


if __name__ == "__main__":
    init_redis_client()
