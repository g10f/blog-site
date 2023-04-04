#!/bin/bash
tag=$(python3 apps/version.py)
DOCKER_BUILDKIT=1
# docker buildx create --use
docker buildx build --pull --platform linux/amd64 -t ghcr.io/g10f/blog-site:$tag -t g10f/blog-site:latest --load .
