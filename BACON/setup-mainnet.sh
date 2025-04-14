#!/bin/bash

set -euo pipefail
echo "Starting Bitcoin Core setup..."

# === Environment Variables ===
export ARCH=x86_64
export BITCOIN_VERSION=0.21.1
export BITCOIN_URL="https://bitcoincore.org/bin/bitcoin-core-${BITCOIN_VERSION}/bitcoin-${BITCOIN_VERSION}-${ARCH}-linux-gnu.tar.gz"
export BITCOIN_DATA_DIR="/blockchain/bitcoin/data"

# === Create bitcoin user and group ===
echo "Creating bitcoin user and group..."
sudo groupadd -r bitcoin || true
sudo useradd -r -m -g bitcoin -s /bin/bash bitcoin || true

# === Install dependencies ===
echo "Installing dependencies..."
sudo apt update
sudo apt install -y ca-certificates gnupg gpg wget jq --no-install-recommends

# === Download and verify Bitcoin Core ===
echo "Downloading Bitcoin Core..."
cd /tmp
wget "https://bitcoincore.org/bin/bitcoin-core-${BITCOIN_VERSION}/SHA256SUMS.asc"
wget -qO "bitcoin-${BITCOIN_VERSION}-${ARCH}-linux-gnu.tar.gz" "$BITCOIN_URL"

# Optional: SHA256 check (manual or via gpg key import step if desired)
echo "Expected SHA256:"
cat SHA256SUMS.asc | grep "bitcoin-${BITCOIN_VERSION}-${ARCH}-linux-gnu.tar.gz" | awk '{ print $1 }'

# === Extract and install Bitcoin Core ===
echo "Installing Bitcoin Core to /opt/bitcoin..."
sudo mkdir -p "/opt/bitcoin/${BITCOIN_VERSION}"
sudo mkdir -p "${BITCOIN_DATA_DIR}"
sudo tar -xzvf "bitcoin-${BITCOIN_VERSION}-${ARCH}-linux-gnu.tar.gz" -C "/opt/bitcoin/${BITCOIN_VERSION}" --strip-components=1 --exclude=*-qt
sudo ln -sfn "/opt/bitcoin/${BITCOIN_VERSION}" /opt/bitcoin/current
sudo rm -rf /tmp/*
sudo chown -R bitcoin:bitcoin "${BITCOIN_DATA_DIR}"

# === Create bitcoin.conf ===
echo "Creating bitcoin.conf..."
cat > bitcoin.conf.tmp <<EOF
datadir=${BITCOIN_DATA_DIR}
printtoconsole=1
rpcallowip=127.0.0.1
rpcuser=${BITCOIN_RPC_USER:-bitcoin}
rpcpassword=${BITCOIN_RPC_PASSWORD:-$(openssl rand -hex 24)}
testnet=1
prune=1000
[test]
rpcbind=127.0.0.1
rpcport=18332
EOF

# === Create systemd service ===
echo "Creating systemd service file..."
cat > bitcoind.service <<EOF
[Unit]
Description=Bitcoin Core Testnet
After=network.target

[Service]
User=bitcoin
Group=bitcoin
WorkingDirectory=${BITCOIN_DATA_DIR}
Type=simple
ExecStart=/opt/bitcoin/current/bin/bitcoind -conf=${BITCOIN_DATA_DIR}/bitcoin.conf

[Install]
WantedBy=multi-user.target
EOF

# === Move config files and set permissions ===
echo "Setting permissions and moving files..."
sudo mv bitcoin.conf.tmp "${BITCOIN_DATA_DIR}/bitcoin.conf"
sudo chown bitcoin:bitcoin "${BITCOIN_DATA_DIR}/bitcoin.conf"
sudo chown -R bitcoin "${BITCOIN_DATA_DIR}"
sudo ln -sfn "${BITCOIN_DATA_DIR}" /home/bitcoin/.bitcoin
sudo chown -h bitcoin:bitcoin /home/bitcoin
sudo chown -R bitcoin:bitcoin /home/bitcoin

# === Enable and start systemd service ===
echo "Enabling bitcoind systemd service..."
sudo mv bitcoind.service /etc/systemd/system/bitcoind.service
sudo systemctl daemon-reload
sudo systemctl enable bitcoind
sudo systemctl start bitcoind

# === Switch to bitcoin user and update PATH ===
echo "Appending Bitcoin Core to PATH for bitcoin user..."
sudo su - bitcoin -c 'echo "export PATH=\$PATH:/opt/bitcoin/current/bin" >> ~/.profile'

echo "Bitcoin Core setup complete!"
echo "Use 'sudo su - bitcoin' then run 'bitcoin-cli -getinfo' to check sync status."
echo "Or run 'sudo journalctl -fu bitcoind' as root to monitor logs."
