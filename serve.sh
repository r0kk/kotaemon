#!/bin/bash

# Define container name
CONTAINER_NAME="koteamon"

# Function to set up the cron job
setup_cron_job() {
    CRON_JOB="0 * * * * /usr/bin/docker restart $CONTAINER_NAME"

    # Check if the cron job already exists
    if crontab -l 2>/dev/null | grep -Fq "$CRON_JOB"; then
        echo "Cron job already exists: Restarting $CONTAINER_NAME every hour."
    else
        # Add cron job if not found
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "Cron job added: Restarting $CONTAINER_NAME every hour."
    fi
}

echo "Starting Koteamon Deployment..."

# Normal build and deployment
docker compose build --no-cache
docker compose up -d

# Set up the cron job for automatic restarts
setup_cron_job

echo "Deployment completed."
