#!/bin/bash
# Helper script to run PostgreSQL commands inside the container

# Check if docker command exists
if ! command -v docker &> /dev/null; then
    echo "Error: docker command not found!"
    exit 1
fi

# Ensure postgres container is running
if ! docker ps | grep -q postgres; then
    echo "Error: postgres container is not running!"
    exit 1
fi

# Run the command in the container
docker exec -i postgres psql -U friday_service -d friday "$@"