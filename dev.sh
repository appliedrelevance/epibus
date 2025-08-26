#!/bin/bash

# Development deployment script for Intralogistics AI
# Provides live editing capabilities with volume mounts

set -e

echo "🚀 Starting Intralogistics AI Development Environment..."
echo "   This provides live editing for PLC Bridge and CODESYS projects"

# Check if environment file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from example.env..."
    cp example.env .env
    echo "✏️  Please edit .env file with your settings before running again."
    exit 1
fi

# Source environment variables
set -a
source .env
set +a

# Check required environment variables for development
if [ -z "$DB_PASSWORD" ]; then
    echo "❌ DB_PASSWORD not set in .env file"
    exit 1
fi

# Development-specific environment variables
export CUSTOM_IMAGE=${CUSTOM_IMAGE:-frappe-epibus}
export CUSTOM_TAG=${CUSTOM_TAG:-latest}
export PULL_POLICY=${PULL_POLICY:-never}
export PLC_LOG_LEVEL=${PLC_LOG_LEVEL:-DEBUG}

echo "📦 Development Configuration:"
echo "   Custom Image: $CUSTOM_IMAGE:$CUSTOM_TAG"
echo "   Pull Policy: $PULL_POLICY"
echo "   PLC Log Level: $PLC_LOG_LEVEL"
echo

# Check if custom image exists (if using custom image)
if [ "$CUSTOM_IMAGE" = "frappe-epibus" ] && [ "$PULL_POLICY" = "never" ]; then
    if ! docker images | grep -q "$CUSTOM_IMAGE.*$CUSTOM_TAG"; then
        echo "🔨 Custom EpiBus image not found. Building..."
        ./development/build-epibus-image.sh
    fi
fi

# Determine platform-specific overrides
PLATFORM_OVERRIDE=""
if [ "$(uname -m)" = "arm64" ] && [ "$(uname)" = "Darwin" ]; then
    PLATFORM_OVERRIDE="-f overrides/compose.mac-m4.yaml"
    echo "🍎 Detected Mac ARM64, using Mac M4 overrides"
fi

# Build the docker-compose command
COMPOSE_CMD="docker compose \
  -f compose.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  -f overrides/compose.codesys.yaml \
  -f overrides/compose.plc-bridge.yaml \
  -f overrides/compose.development.yaml"

if [ -n "$PLATFORM_OVERRIDE" ]; then
    COMPOSE_CMD="$COMPOSE_CMD $PLATFORM_OVERRIDE"
fi

echo "🐳 Starting development stack..."
echo "Command: $COMPOSE_CMD up -d"
echo

# Start the stack
eval "$COMPOSE_CMD up -d"

# Wait a moment for services to start
sleep 5

# Show status
echo
echo "📊 Development Stack Status:"
docker compose ps

echo
echo "✅ Development Environment Ready!"
echo
echo "🔗 Development Access Points:"
echo "   • PLC Bridge Dashboard: http://localhost:7654"
echo "   • ERP System: http://intralogistics.lab (check port with 'docker compose ps')"
echo "   • MODBUS TCP: localhost:502"
echo "   • CODESYS Gateway: localhost:1217 (for Windows CODESYS IDE)"
echo
echo "📁 Live Editing Enabled:"
echo "   • PLC Bridge Code: ./epibus/plc/bridge/"
echo "   • EpiBus App Code: ./epibus/"
echo "   • CODESYS Projects: ./plc_programs/"
echo
echo "🛠️  Development Commands:"
echo "   • Stop: docker compose down"
echo "   • Restart PLC Bridge: docker compose restart plc-bridge"
echo "   • View Logs: docker compose logs -f [service-name]"
echo "   • Shell Access: docker compose exec [service-name] bash"
echo
echo "💡 Changes to Python files will require container restart to take effect."
echo "   For PLC Bridge: docker compose restart plc-bridge"