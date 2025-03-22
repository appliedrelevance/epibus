#!/bin/bash

# Script to set up and build the Modbus Dashboard React application

echo "Setting up Modbus Dashboard React application..."

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "Node.js version 18 or higher is required. Current version: $(node -v)"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Build the application
echo "Building the application..."
npm run build

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Build successful! The application is now available in the public/modbus_dashboard directory."
    echo "You can access it through your Frappe instance."
else
    echo "Build failed. Please check the error messages above."
    exit 1
fi

echo "Setup complete!"