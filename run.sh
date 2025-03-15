#!/bin/bash

# Check if SSL certificates exist, if not, generate self-signed certificates
if [ ! -f ./ssl/cert.pem ] || [ ! -f ./ssl/key.pem ]; then
    echo "SSL certificates not found. Generating self-signed certificates..."
    
    # Create ssl directory if it doesn't exist
    mkdir -p ./ssl
    
    # Generate self-signed certificate valid for 365 days
    openssl req -x509 -newkey rsa:4096 -nodes -out ./ssl/cert.pem -keyout ./ssl/key.pem -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:0.0.0.0"
    
    echo "Self-signed certificates generated successfully."
fi

# Run the application with SSL
uvicorn blt.asgi:application --host 0.0.0.0 --port 8443 --ssl-keyfile ./ssl/key.pem --ssl-certfile ./ssl/cert.pem --log-level debug --reload --reload-include *.html

