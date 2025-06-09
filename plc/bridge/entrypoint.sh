#!/bin/bash
python bridge.py --frappe-url "$FRAPPE_URL" --api-key "$FRAPPE_API_KEY" --api-secret "$FRAPPE_API_SECRET" --poll-interval "${PLC_POLL_INTERVAL:-1.0}"