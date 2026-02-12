#!/bin/bash

# Set your token project name
TOKEN_NAME="your-token-name"

# Create the project directory
mkdir "$TOKEN_NAME"

# Jump into the directory
cd "$TOKEN_NAME" || exit

# Create a Dockerfile with nano or auto-fill it
cat <<'EOF' > Dockerfile
# Use a lightweight base image
FROM debian:bullseye-slim

# Set non-interactive frontend for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install required dependencies and Rust
RUN apt-get update && apt-get install -y \
    curl build-essential libssl-dev pkg-config nano \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Add Rust to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Verify Rust installation
RUN rustc --version

# Install Solana CLI
RUN curl -sSfL https://release.anza.xyz/stable/install | sh \
    && echo 'export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"' >> ~/.bashrc

# Add Solana CLI to PATH
ENV PATH="/root/.local/share/solana/install/active_release/bin:$PATH"

# Verify Solana CLI installation
RUN solana --version

# Set up Solana config for Devnet
RUN solana config set -ud

# Set working directory
WORKDIR /solana-token

# Default command to run a shell
CMD ["/bin/bash"]
EOF

# Build Docker image
docker build -t heysolana .

# Run Docker container interactively
docker run -it --rm \
  -v "$(pwd)":/solana-token \
  -v "$(pwd)/solana-data":/root/.config/solana \
  heysolana

# After container starts, you can run:
# solana-keygen grind --starts-with dad:1
