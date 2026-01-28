#!/bin/bash
# Leaf Health Analyzer - AWS Deploy Script

set -e

echo "=========================================="
echo "🚀 Deploying Leaf Health Analyzer"
echo "=========================================="
echo ""

# ✅ SET YOUR REAL PROJECT PATH HERE
PROJECT_DIR="/home/ubuntu/Skills2.1-projct"

APP_USER="ubuntu"
SERVICE_NAME="leaf-health"
APP_HOST="0.0.0.0"
APP_PORT="8000"

echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Basic checks
if [ ! -d "$PROJECT_DIR" ]; then
  echo "❌ Error: PROJECT_DIR does not exist: $PROJECT_DIR"
  exit 1
fi

if [ ! -f "$PROJECT_DIR/app.py" ]; then
  echo "❌ Error: app.py not found in $PROJECT_DIR"
  exit 1
fi

if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
  echo "❌ Error: requirements.txt not found in $PROJECT_DIR"
  exit 1
fi

# Step 1: Update system
echo "[1/9] Updating system..."
sudo apt update -qq && sudo apt upgrade -y -qq
echo "   ✅ System updated"

# Step 2: Install Python + Nginx
echo "[2/9] Installing Python 3.11 + Nginx..."
sudo apt install -y -qq software-properties-common nginx
sudo add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1 || true
sudo apt update -qq
sudo apt install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip
echo "   ✅ Installed Python 3.11 and Nginx"

# Step 3: Create virtual environment
echo "[3/9] Creating venv..."
cd "$PROJECT_DIR"
python3.11 -m venv venv
source "$PROJECT_DIR/venv/bin/activate"
pip install -q --upgrade pip
echo "   ✅ venv ready"

# Step 4: Install dependencies
echo "[4/9] Installing dependencies..."
pip install -q -r "$PROJECT_DIR/requirements.txt"
echo "   ✅ Dependencies installed"

# Step 5: Check .env (required by your original script logic)
echo "[5/9] Checking .env..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "❌ ERROR: .env not found in $PROJECT_DIR"
  echo "   Create /home/ubuntu/Skills2.1-projct/.env"
  exit 1
fi
echo "   ✅ .env found"

# Step 6: Create systemd service
echo "[6/9] Creating systemd service..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<EOF
[Unit]
Description=Leaf Health Analyzer (Uvicorn/FastAPI)
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/venv/bin"
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/venv/bin/uvicorn app:app --host ${APP_HOST} --port ${APP_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"
echo "   ✅ systemd service started"

# Step 7: Configure Nginx reverse proxy
echo "[7/9] Configuring Nginx..."
sudo tee "/etc/nginx/sites-available/${SERVICE_NAME}" > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf "/etc/nginx/sites-available/${SERVICE_NAME}" "/etc/nginx/sites-enabled/${SERVICE_NAME}"

sudo nginx -t
sudo systemctl restart nginx
echo "   ✅ Nginx configured and restarted"

# Step 8: Show service status
echo "[8/9] Service status..."
sudo systemctl --no-pager --full status "${SERVICE_NAME}" || true

# Step 9: Final info
echo "[9/9] Done."
echo "✅ App should be reachable on: http://<your-ec2-public-ip>/"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "  sudo journalctl -u ${SERVICE_NAME} -n 200 --no-pager"
echo "  sudo nginx -t"
