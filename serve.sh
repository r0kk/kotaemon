#!/bin/bash
# # docker build
# docker build -t koteamon:v.0.9.8 .
# docker run -d -p 7860:7860 --name koteamon koteamon:v.0.9.8

# # normal build
# docker compose build
# docker compose up -d --env-file .env

# force recreate
docker compose build --no-cache
docker compose --env-file .env up -d --force-recreate
