import os
import subprocess

import yaml
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Environment Variables
ORD_PATH = os.getenv("ORD_PATH", "/usr/local/bin/ord")
YAML_FILE_PATH = os.getenv("YAML_FILE_PATH", "/blockchain/ord-flask-server/tmp-batch.yaml")

# Bitcoin RPC Configuration for Mainnet
BITCOIN_RPC_USER_MAINNET = os.getenv("BITCOIN_RPC_USER_MAINNET", "bitcoin_mainnet")
BITCOIN_RPC_PASSWORD_MAINNET = os.getenv("BITCOIN_RPC_PASSWORD_MAINNET", "password_mainnet")
BITCOIN_RPC_URL_MAINNET = os.getenv("BITCOIN_RPC_URL_MAINNET", "http://bitcoin-node-ip:18443")

# Bitcoin RPC Configuration for Regtest
BITCOIN_RPC_USER_REGTEST = os.getenv("BITCOIN_RPC_USER_REGTEST", "bitcoin_regtest")
BITCOIN_RPC_PASSWORD_REGTEST = os.getenv("BITCOIN_RPC_PASSWORD_REGTEST", "password_regtest")
BITCOIN_RPC_URL_REGTEST = os.getenv("BITCOIN_RPC_URL_REGTEST", "http://regtest-node-ip:18443")

# Ordinal Server Configuration
ORD_SERVER_URL_MAINNET = os.getenv("ORD_SERVER_URL_MAINNET", "http://ord-server-ip:9001")
ORD_SERVER_URL_REGTEST = os.getenv("ORD_SERVER_URL_REGTEST", "http://regtest-server-ip:9001")

# Wallet Configuration
WALLET_NAME_MAINNET = os.getenv("WALLET_NAME_MAINNET", "master-wallet")
WALLET_NAME_REGTEST = os.getenv("WALLET_NAME_REGTEST", "regtest-wallet")
WALLET_ADDRESS_REGTEST = os.getenv("WALLET_ADDRESS_REGTEST", "bcrt1")

# Default Batch Transaction Output
DEFAULT_OUTPUT = {"address": WALLET_ADDRESS_REGTEST, "runes": {"BLT•BACON•TOKENS": 1}}


@app.route("/mainnet/send-bacon-tokens", methods=["POST"])
def send_bacon_tokens():
    yaml_content = request.json.get("yaml_content")
    fee_rate = request.json.get("fee_rate")
    is_dry_run = request.json.get("dry_run", False)

    if not yaml_content:
        return jsonify({"success": False, "error": "YAML content missing"}), 400
    if not fee_rate or not isinstance(fee_rate, (int, float)):
        return jsonify({"success": False, "error": "Valid fee_rate is required"}), 400

    # Write YAML to a temporary file
    with open(YAML_FILE_PATH, "w") as file:
        file.write(yaml_content)

    command = [
        "sudo",
        ORD_PATH,
        f"--bitcoin-rpc-username={BITCOIN_RPC_USER_MAINNET}",
        f"--bitcoin-rpc-password={BITCOIN_RPC_PASSWORD_MAINNET}",
        f"--bitcoin-rpc-url={BITCOIN_RPC_URL_MAINNET}",
        "wallet",
        f"--server-url={ORD_SERVER_URL_MAINNET}",
        f"--name={WALLET_NAME_MAINNET}",
        "split",
        f"--splits={YAML_FILE_PATH}",
        f"--fee-rate={fee_rate}",
    ]

    if is_dry_run:
        command.append("--dry-run")

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return jsonify({"success": True, "output": result.stdout, "dry_run": is_dry_run})
    except subprocess.CalledProcessError as e:
        return jsonify({"success": False, "error": e.stderr, "dry_run": is_dry_run})


@app.route("/regtest/send-bacon-tokens", methods=["POST"])
def send_bacon_tokens_regtest():
    num_users = request.json.get("num_users")
    fee_rate = request.json.get("fee_rate")

    if not num_users or not isinstance(num_users, int) or num_users <= 0:
        return jsonify({"success": False, "error": "num_users must be a positive integer"}), 400
    if not fee_rate or not isinstance(fee_rate, (int, float)):
        return jsonify({"success": False, "error": "Valid fee_rate is required"}), 400

    # Generate YAML batch transaction file
    yaml_data = {"outputs": [DEFAULT_OUTPUT] * num_users}

    with open(YAML_FILE_PATH, "w") as file:
        yaml.dump(yaml_data, file, default_flow_style=False)

    command = [
        "sudo",
        ORD_PATH,
        f"--bitcoin-rpc-username={BITCOIN_RPC_USER_REGTEST}",
        f"--bitcoin-rpc-password={BITCOIN_RPC_PASSWORD_REGTEST}",
        f"--bitcoin-rpc-url={BITCOIN_RPC_URL_REGTEST}",
        "-r",
        "wallet",
        f"--server-url={ORD_SERVER_URL_REGTEST}",
        f"--name={WALLET_NAME_REGTEST}",
        "split",
        f"--splits={YAML_FILE_PATH}",
        f"--fee-rate={fee_rate}",
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        txid = result.stdout.strip()  # Extract the transaction ID from output
        return jsonify({"success": True, "txid": txid})
    except subprocess.CalledProcessError as e:
        return jsonify({"success": False, "error": e.stderr})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("FLASK_PORT", 9002)))
