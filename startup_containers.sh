#!/bin/bash
set -e

# Define pod name and volume names
POD_NAME="mypod"
OPEN_WEBUI_VOLUME="open-webui"
QDRANT_VOLUME="qdrant-data"

echo "Creating pod '$POD_NAME' with ports 8080 and 6333..."
podman pod create --name "$POD_NAME" -p 8080:8080 -p 6333:6333

# Create named volumes if they don't exist already
echo "Creating volume '$OPEN_WEBUI_VOLUME'..."
podman volume create "$OPEN_WEBUI_VOLUME" >/dev/null 2>&1 || true
echo "Creating volume '$QDRANT_VOLUME'..."
podman volume create "$QDRANT_VOLUME" >/dev/null 2>&1 || true

# Pull latest images
echo "Pulling the latest images..."
podman pull ollama/ollama:latest
podman pull ghcr.io/open-webui/open-webui:main
podman pull qdrant/qdrant:latest

# Start the 'ollama' container
echo "Starting container 'ollama'..."
podman run --name ollama \
  --pod "$POD_NAME" \
  --detach \
  --restart=unless-stopped \
  -t \
  -v "$HOME/.ollama/models":/root/.ollama/models \
  ollama/ollama:latest

# Wait briefly to allow 'ollama' to initialize before starting dependent containers
sleep 5

# Start the 'open-webui' container
echo "Starting container 'open-webui'..."
podman run --name open-webui \
  --pod "$POD_NAME" \
  --detach \
  --restart=unless-stopped \
  --env OLLAMA_API_URL="http://ollama:11434" \
  --add-host host.docker.internal:host-gateway \
  -v "$OPEN_WEBUI_VOLUME":/app/backend/data \
  ghcr.io/open-webui/open-webui:main

# Start the 'qdrant' container
echo "Starting container 'qdrant'..."
podman run --name qdrant \
  --pod "$POD_NAME" \
  --detach \
  --restart=unless-stopped \
  -v "$QDRANT_VOLUME":/qdrant/storage \
  qdrant/qdrant:latest

echo "All containers have been started in pod '$POD_NAME'."
