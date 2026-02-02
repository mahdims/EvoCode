# Simple Dockerfile for building a claude-code image
FROM node:24-alpine

# Install build dependencies via apk
RUN apk add --no-cache \
    python3-dev \
    py3-pip \
    openjdk25 \
    bash

RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

COPY evolver/requirements.txt .
RUN pip install --break-system-packages -r requirements.txt

# Set POSIX shell as default
SHELL ["/bin/bash", "c"]

# We could map this directly to claude, but this is a little more easy to debug for now
CMD ["tail", "-f", "/dev/null"]
