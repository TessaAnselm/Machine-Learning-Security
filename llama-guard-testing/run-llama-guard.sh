#!/usr/bin/env bash
# Ephemeral Ollama + Llama Guard setup. No volume mount, no --rm removal step
# needed on your part beyond stopping the container: everything (container fs,
# downloaded model blob) is destroyed on `docker stop` since the container is
# started with --rm and nothing is persisted to a volume.
set -euo pipefail

CONTAINER_NAME="ollama-tmp"
MODEL="llama-guard3:1b"

if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Start Docker Desktop first." >&2
    exit 1
fi

if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    echo "Container $CONTAINER_NAME is already running."
else
    echo "Starting ephemeral Ollama container..."
    docker run -d --rm --name "$CONTAINER_NAME" -p 11434:11434 ollama/ollama
fi

echo "Pulling $MODEL (skips if already present in this container)..."
docker exec "$CONTAINER_NAME" ollama pull "$MODEL"

echo
echo "Launching interactive session. Inside it, try the test prompts and run"
echo "'/show info' to find the ML132.1 flag. Type /bye to exit."
echo
docker exec -it "$CONTAINER_NAME" ollama run "$MODEL"

echo
read -rp "Tear down the container now? [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
    docker stop "$CONTAINER_NAME"
    echo "Container stopped and removed (--rm). Nothing persisted to disk."
else
    echo "Container left running. Stop it later with: docker stop $CONTAINER_NAME"
fi
