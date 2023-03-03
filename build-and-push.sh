#!/bin/bash
tag=$(python apps/version.py)
export DOCKER_BUILDKIT=1
docker buildx create --use
docker buildx build --platform linux/amd64 -t g10f/blog-site:"$tag" -t g10f/blog-site:latest --load .
