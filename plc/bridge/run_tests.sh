#!/bin/bash

# Run PLC Bridge tests

# Change to script directory
cd "$(dirname "$0")"

# Run tests
python3 -m unittest test_bridge.py

# Exit with the same code as the tests
exit $?