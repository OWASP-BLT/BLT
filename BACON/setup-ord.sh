#!/bin/bash

# Step 1: Update system packages
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Step 2: Install required dependencies
echo "Installing dependencies..."
sudo apt install -y curl git build-essential libssl-dev pkg-config

# Step 3: Install Rust
echo "Installing Rust..."
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

# Step 4: Check Rust versions
rustc --version
cargo --version

# Step 5: Download and extract ord source code
echo "Downloading ord 0.22.2..."
wget https://github.com/ordinals/ord/archive/refs/tags/0.22.2.tar.gz
tar -xvzf 0.22.2.tar.gz
cd ord-0.22.2

# Step 6: Install build tools (again, just in case)
echo "Installing build tools for compiling ord..."
sudo apt update
sudo apt install -y build-essential clang cmake gcc g++ make pkg-config libssl-dev

# Step 7: Build ord from source
echo "Building ord..."
cargo build --release

# Step 8: Move the binary to /usr/local/bin
echo "Moving ord binary to /usr/local/bin..."
sudo mv target/release/ord /usr/local/bin/

# Step 9: Verify ord installation
ord --version

# Optional: Get the index
echo "Downloading index file..."
sudo apt update && sudo apt install transmission-cli -y
transmission-cli "https://ordstuff.info/indexes/0.22/index-0.22-without-878500.redb.gz.torrent"

# Wait for download to complete manually before continuing

# Optional: Decompress the index file
echo "Installing pv for decompression progress..."
sudo apt install -y pv
pv index-0.22-without-878500.redb.gz | gunzip > index-0.22-without-878500.redb

echo "Setup complete!"
