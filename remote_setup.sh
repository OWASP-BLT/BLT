#!/bin/bash

# OWASP BLT Remote Setup Script
# This script automates the setup of the OWASP BLT website on a remote VPS
# It handles installation of dependencies, environment configuration, and application setup

set -e  # Exit on any error

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
REPO_URL="https://github.com/OWASP-BLT/BLT.git"
INSTALL_DIR="/opt/blt"
USE_HTTPS=false
DOMAIN=""
EMAIL=""
PORT=8000
POSTGRES_PORT=5432
POSTGRES_PASSWORD=$(openssl rand -base64 12)
POSTGRES_USER="postgres"
POSTGRES_DB="blt_db"

# Log function for better output
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Display usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -d, --domain DOMAIN       Domain name for the website (required for HTTPS)"
    echo "  -e, --email EMAIL         Email for Let's Encrypt certificate (required for HTTPS)"
    echo "  -i, --install-dir DIR     Installation directory (default: /opt/blt)"
    echo "  -p, --port PORT           HTTP port (default: 8000)"
    echo "  -s, --https               Enable HTTPS with Let's Encrypt"
    echo "  --db-port PORT            PostgreSQL port (default: 5432)"
    echo "  --db-user USER            PostgreSQL username (default: postgres)"
    echo "  --db-name NAME            PostgreSQL database name (default: blt_db)"
    echo "  --db-password PASSWORD    PostgreSQL password (default: random generated)"
    echo "  -h, --help                Show this help message"
    echo
    exit 1
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -e|--email)
                EMAIL="$2"
                shift 2
                ;;
            -i|--install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -s|--https)
                USE_HTTPS=true
                shift
                ;;
            --db-port)
                POSTGRES_PORT="$2"
                shift 2
                ;;
            --db-user)
                POSTGRES_USER="$2"
                shift 2
                ;;
            --db-name)
                POSTGRES_DB="$2"
                shift 2
                ;;
            --db-password)
                POSTGRES_PASSWORD="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                warning "Unknown option: $1"
                usage
                ;;
        esac
    done

    # Validate required parameters for HTTPS
    if [[ "$USE_HTTPS" = true ]]; then
        if [[ -z "$DOMAIN" ]]; then
            error "Domain name (-d, --domain) is required when using HTTPS"
        fi
        if [[ -z "$EMAIL" ]]; then
            error "Email (-e, --email) is required when using HTTPS"
        fi
    fi
}

# Check for root privileges
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root" 
    fi
}

# Check and install system dependencies
install_dependencies() {
    log "Checking system dependencies..."
    
    # Update package lists
    apt-get update || error "Failed to update package lists"
    
    # Install essential packages
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        git \
        python3 \
        python3-pip \
        libpq-dev \
        postgresql-client \
        dos2unix \
        || error "Failed to install essential packages"
        
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log "Installing Docker..."
        # Add Docker repository
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
        
        # Install Docker
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io || error "Failed to install Docker"
    else
        log "Docker is already installed"
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log "Installing Docker Compose..."
        # Install Docker Compose
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose 2>/dev/null || true
    else
        log "Docker Compose is already installed"
    fi
    
    # Start Docker service
    systemctl start docker
    systemctl enable docker
    
    log "All dependencies installed successfully!"
}

# Setup Certbot for HTTPS if requested
setup_https() {
    if [[ "$USE_HTTPS" = true ]]; then
        log "Setting up HTTPS with Let's Encrypt..."
        
        # Install Certbot
        apt-get install -y certbot python3-certbot-nginx || error "Failed to install Certbot"
        
        # Install nginx if not already installed
        if ! command -v nginx &> /dev/null; then
            apt-get install -y nginx || error "Failed to install nginx"
        fi
        
        # Create nginx config for the domain
        cat > /etc/nginx/sites-available/blt << EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://localhost:${PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
        
        # Enable the site
        ln -sf /etc/nginx/sites-available/blt /etc/nginx/sites-enabled/
        systemctl reload nginx
        
        # Get SSL certificate
        certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --email "${EMAIL}" || error "Failed to obtain SSL certificate"
        
        log "HTTPS setup completed successfully!"
    else
        log "Skipping HTTPS setup as it was not requested"
    fi
}

# Clone the repository
clone_repository() {
    log "Setting up BLT repository..."
    
    # Create installation directory if it doesn't exist
    mkdir -p "$INSTALL_DIR"
    
    # Check if directory is empty
    if [[ "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
        warning "Installation directory is not empty. Checking if it's a BLT repository..."
        
        if [[ -f "$INSTALL_DIR/manage.py" && -d "$INSTALL_DIR/website" ]]; then
            log "BLT repository already exists. Pulling latest changes..."
            cd "$INSTALL_DIR"
            git pull
        else
            error "Installation directory contains files but doesn't appear to be a BLT repository. Please choose a different directory or clear the existing one."
        fi
    else
        # Clone the repository
        log "Cloning BLT repository..."
        git clone "$REPO_URL" "$INSTALL_DIR" || error "Failed to clone repository"
        cd "$INSTALL_DIR"
    fi
    
    # Ensure proper line endings
    find "$INSTALL_DIR" -name "*.sh" -exec dos2unix {} \;
    dos2unix "$INSTALL_DIR/entrypoint.sh" 2>/dev/null || true
    dos2unix "$INSTALL_DIR/docker-compose.yml" 2>/dev/null || true
    
    log "Repository setup completed!"
}

# Configure environment variables
setup_environment() {
    log "Setting up environment variables..."
    
    cd "$INSTALL_DIR"
    
    # Generate a random string for Django secret key
    DJANGO_SECRET_KEY=$(openssl rand -base64 32)
    SUPERUSER_PASSWORD=$(openssl rand -base64 12)
    
    # Create .env file from template
    if [[ -f .env.example ]]; then
        cp .env.example .env
        
        # Update .env file with production settings
        sed -i "s/DEBUG=True/DEBUG=False/" .env
        sed -i "s/DOMAIN_NAME=localhost/DOMAIN_NAME=${DOMAIN:-localhost}/" .env
        sed -i "s/PORT=8000/PORT=${PORT}/" .env
        sed -i "s/POSTGRES_PASSWORD=postgres/POSTGRES_PASSWORD=${POSTGRES_PASSWORD}/" .env
        sed -i "s/POSTGRES_USER=postgres/POSTGRES_USER=${POSTGRES_USER}/" .env
        sed -i "s/POSTGRES_DB=example_db/POSTGRES_DB=${POSTGRES_DB}/" .env
        sed -i "s/POSTGRES_PORT=5432/POSTGRES_PORT=${POSTGRES_PORT}/" .env
        
        # Update the database URL
        sed -i "s|DATABASE_URL=postgres://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@localhost:\${POSTGRES_PORT}/\${POSTGRES_DB}|DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}|" .env
        
        # Update callback URLs
        if [[ -n "$DOMAIN" ]]; then
            PROTOCOL="http"
            if [[ "$USE_HTTPS" = true ]]; then
                PROTOCOL="https"
            fi
            
            BASE_URL="${PROTOCOL}://${DOMAIN}"
            sed -i "s|CALLBACK_URL_FOR_GITHUB=http://127.0.0.1:8000/|CALLBACK_URL_FOR_GITHUB=${BASE_URL}/|" .env
            sed -i "s|CALLBACK_URL_FOR_GOOGLE=http://127.0.0.1:8000/|CALLBACK_URL_FOR_GOOGLE=${BASE_URL}/|" .env
            sed -i "s|CALLBACK_URL_FOR_FACEBOOK=http://127.0.0.1:8000/|CALLBACK_URL_FOR_FACEBOOK=${BASE_URL}/|" .env
        fi
        
        # Set superuser credentials
        sed -i "s/SUPERUSER=admin11/SUPERUSER=admin/" .env
        sed -i "s/SUPERUSER_MAIL=admin23453453@gmail.com/SUPERUSER_MAIL=admin@${DOMAIN:-example.com}/" .env
        sed -i "s/SUPERUSER_PASSWORD=admi345n@12343453/SUPERUSER_PASSWORD=${SUPERUSER_PASSWORD}/" .env
        
        log "Environment variables configured successfully!"
        log "Admin credentials:"
        log "  Username: admin"
        log "  Password: ${SUPERUSER_PASSWORD}"
        log "  Email: admin@${DOMAIN:-example.com}"
    else
        error ".env.example file not found in the repository"
    fi
}

# Deploy with Docker Compose
deploy_with_docker() {
    log "Starting Docker deployment..."
    
    cd "$INSTALL_DIR"
    
    # Build and start Docker containers
    docker-compose build || error "Failed to build Docker images"
    docker-compose up -d || error "Failed to start Docker containers"
    
    # Wait for the application container to start
    log "Waiting for containers to initialize..."
    sleep 10
    
    # Get the container ID
    container_id=$(docker ps -q --filter "name=app")
    
    if [[ -z "$container_id" ]]; then
        warning "Container not running. Checking logs..."
        docker-compose logs
        error "Failed to start the application container"
    fi
    
    log "Docker deployment completed successfully!"
}

# Configure server for production use
configure_production() {
    log "Configuring server for production use..."
    
    # Create a systemd service for automatic startup
    cat > /etc/systemd/system/blt.service << EOF
[Unit]
Description=OWASP BLT Web Application
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable and start the service
    systemctl daemon-reload
    systemctl enable blt.service
    
    log "Production configuration completed!"
}

# Display final instructions
display_instructions() {
    local app_url
    
    if [[ -n "$DOMAIN" ]]; then
        if [[ "$USE_HTTPS" = true ]]; then
            app_url="https://${DOMAIN}"
        else
            app_url="http://${DOMAIN}"
        fi
    else
        app_url="http://<server-ip>:${PORT}"
    fi
    
    echo
    echo "======================= SETUP COMPLETE ========================="
    echo
    echo "Your OWASP BLT instance has been successfully set up!"
    echo
    echo "Access your website at: ${app_url}"
    echo
    echo "Admin login:"
    echo "  URL: ${app_url}/admin/"
    echo "  Username: admin"
    echo "  Password: ${SUPERUSER_PASSWORD}"
    echo
    echo "Important notes:"
    echo "- For security, please change the admin password after first login"
    echo "- To restart the application: systemctl restart blt"
    echo "- View logs: docker-compose logs -f"
    echo
    echo "For more information, visit: https://github.com/OWASP-BLT/BLT"
    echo
    echo "================================================================"
}

# Main function to run everything
main() {
    log "Starting OWASP BLT setup on remote VPS..."
    
    # Parse command line arguments
    parse_args "$@"
    
    # Check for root privileges
    check_root
    
    # Install dependencies
    install_dependencies
    
    # Clone repository
    clone_repository
    
    # Configure environment
    setup_environment
    
    # Deploy with Docker
    deploy_with_docker
    
    # Configure for production use
    configure_production
    
    # Setup HTTPS if requested
    setup_https
    
    # Display instructions
    display_instructions
    
    log "Setup completed successfully!"
}

# Run the main function
main "$@"