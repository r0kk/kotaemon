#!/bin/bash
# docker build -t koteamon:v.0.9.8 .
# docker run -d -p 7860:8000 --name koteamon koteamon:v.0.9.8
docker compose build
docker compose up -d
