#!/bin/bash

# Define container name
echo "Starting Koteamon Deployment..."

# Normal build and deployment
docker compose build --no-cache
docker compose up -d

echo "Deployment completed."
