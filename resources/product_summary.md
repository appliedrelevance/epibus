# Epibus Product Summary

## Overview

Epibus is a system designed for monitoring and controlling Modbus devices via a PLC bridge. It integrates the following key components: Signal Handler, Signal Monitor, PLCRedisClient, and PLC Bridge Adapter to provide real-time data acquisition, control, and monitoring capabilities.

## Architecture

The system follows a modular architecture. Key components include:

*   **Signal Handler:** Handles read/write operations for different Modbus signal types.
*   **Signal Monitor:** Monitors Modbus signals and publishes changes via Frappe's realtime.
*   **PLCRedisClient:** Redis client for communicating with the PLC bridge.
*   **PLC Bridge Adapter:** Provides functions for getting signals from and writing signals via the PLC bridge.

These components interact through a combination of Redis pub/sub for real-time communication and Frappe's realtime system for frontend updates. The Signal Monitor publishes changes to Frappe's realtime, which the frontend subscribes to. The PLCRedisClient interacts with the PLC bridge via Redis.

## Key Functionalities

*   **Real-time Signal Monitoring:** Monitors Modbus signals and publishes changes to the frontend.
*   **PLC Communication:** Communicates with the PLC bridge to read and write signal values.
*   **Action Triggering:** Triggers actions based on signal changes.

## Intercomponent Relationships

The Signal Handler provides the core logic for reading and writing Modbus signals. The Signal Monitor uses the Signal Handler to read signal values and publishes changes via Frappe's realtime system. The PLCRedisClient interacts with the PLC bridge to communicate with Modbus devices. The PLC Bridge Adapter provides an abstraction layer for interacting with the PLC bridge.

## LLM Consumption Notes

This document provides a high-level overview of the Epibus system. For more detailed information, please refer to the technical artifact.