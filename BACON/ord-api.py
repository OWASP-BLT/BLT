import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)

ORD_PATH = "/usr/local/bin/ord"
YAML_FILE_PATH = "/blockchain/ord-flask-server/tmp-split.yaml"


@app.route("/send-bacon-tokens", methods=["POST"])
def send_bacon_tokens():
    # Extract YAML content from request
    yaml_content = request.json.get("yaml_content")

    if not yaml_content:
        return jsonify({"success": False, "error": "YAML content missing"}), 400

    # Write YAML to a temporary file
    with open(YAML_FILE_PATH, "w") as file:
        file.write(yaml_content)
    # change the ip
    command = [
        "sudo",
        ORD_PATH,
        "--bitcoin-rpc-username=bitcoin",
        "--bitcoin-rpc-password=bitcoin",
        "--bitcoin-rpc-url=http://bitcoin-node-ip:18443",
        "-r",
        "wallet",
        "--server-url=http://ord-server-ip:9001",
        "--name=ord",
        "split",
        f"--splits={YAML_FILE_PATH}",
        "--fee-rate=1",
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return jsonify({"success": True, "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"success": False, "error": e.stderr})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9002)
