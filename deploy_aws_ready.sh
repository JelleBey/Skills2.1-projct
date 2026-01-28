#!/bin/bash
# DEPLOYMENT SCRIPT FOR AWS EC2: 44.195.35.212
# Leaf Health Analyzer - Ready to Deploy!

set -e

echo "=========================================="
echo "🚀 Deploying Leaf Health Analyzer"
echo "📍 EC2 Instance: 44.195.35.212"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ] || [ ! -f "tomato_model.pt" ]; then
    echo "❌ Error: Please run this script from ~/leaf-health-app directory"
    echo "   Make sure all files are uploaded first!"
    exit 1
fi

# Verify files are configured for AWS
if ! grep -q "44.195.35.212" app.js; then
    echo "⚠️  Warning: app.js may not be configured for AWS"
    echo "   Please make sure you uploaded the AWS-ready files!"
fi

echo "✅ Files detected. Starting deployment..."
echo ""

# Step 1: Update system
echo "[1/9] Updating system..."
sudo apt update -qq && sudo apt upgrade -y -qq
echo "   ✅ System updated"

# Step 2: Install Python 3.11
echo "[2/9] Installing Python 3.11..."
sudo apt install -y -qq software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1
sudo apt update -qq
sudo apt install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip nginx

PYTHON_VERSION=$(python3.11 --version)
echo "   ✅ $PYTHON_VERSION installed"

# Step 3: Create virtual environment
echo "[3/9] Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
echo "   ✅ Virtual environment ready"

# Step 4: Install dependencies
echo "[4/9] Installing Python dependencies..."
echo "   This may take 3-5 minutes for PyTorch..."
pip install -q -r requirements.txt
echo "   ✅ Dependencies installed"

# Step 5: Verify configuration
echo "[5/9] Verifying AWS configuration..."
if grep -q "44.195.35.212" app.js && grep -q "44.195.35.212" login.html && grep -q "44.195.35.212" register.html; then
    echo "   ✅ All files configured for AWS"
else
    echo "   ⚠️  Warning: Some files may not be AWS-ready"
fi

# Step 6: Check .env file
echo "[6/9] Checking environment variables..."
if [ ! -f ".env" ]; then
    echo "   ❌ ERROR: .env file not found!"
    echo "   Please create .env file with your database URL"
    exit 1
fi

if grep -q "your_database_url_here" .env; then
    echo "   ⚠️  Warning: .env contains placeholder database URL"
    echo "   Please update .env with your actual Neon database URL"
    read -p "   Press Enter to continue or Ctrl+C to cancel..."
fi
echo "   ✅ .env file found"

# Step 7: Create systemd service
echo "[7/9] Creating systemd service..."
sudo tee /etc/systemd/system/leaf-health.service > /dev/null <<'EOF'
[Unit]
Description=Leaf Health Analyzer FastAPI Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/leaf-health-app
Environment="PATH=/home/ubuntu/leaf-health-app/venv/bin"
EnvironmentFile=/home/ubuntu/leaf-health-app/.env
ExecStart=/home/ubuntu/leaf-health-app/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable leaf-health
sudo systemctl start leaf-health
sleep 2
echo "   ✅ Service created and started"

# Step 8: Configure Nginx
echo "[8/9] Configuring Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/leaf-health > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 10M;
    root /home/ubuntu/leaf-health-app;

    # Serve static files
    location /static/ {
        alias /home/ubuntu/leaf-health-app/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Serve HTML files directly
    location ~ \.(html)$ {
        try_files $uri $uri/ =404;
    }

    # API and other requests go to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/leaf-health /etc/nginx/sites-enabled/
sudo nginx -t > /dev/null 2>&1 && echo "   ✅ Nginx configuration valid"
sudo systemctl restart nginx
echo "   ✅ Nginx configured and restarted"

# Step 9: Final verification
echo "[9/9] Running final checks..."
sleep 3

# Check FastAPI service
if sudo systemctl is-active --quiet leaf-health; then
    echo "   ✅ FastAPI service is running"
else
    echo "   ❌ FastAPI service failed!"
    echo "   Run: sudo journalctl -u leaf-health -n 50"
    exit 1
fi

# Check Nginx
if sudo systemctl is-active --quiet nginx; then
    echo "   ✅ Nginx is running"
else
    echo "   ❌ Nginx failed!"
    exit 1
fi

# Test if app responds
sleep 2
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Application responding to requests"
else
    echo "   ⚠️  Application may still be starting up..."
fi

echo ""
echo "=========================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Your Leaf Health Analyzer is now live at:"
echo ""
echo "   🌐 http://44.195.35.212"
echo ""
echo "Test it:"
echo "   - Register a new account"
echo "   - Login"
echo "   - Upload a tomato leaf image"
echo "   - Get AI analysis!"
echo ""
echo "Useful Commands:"
echo "   View logs:      sudo journalctl -u leaf-health -f"
echo "   Restart app:    sudo systemctl restart leaf-health"
echo "   Check status:   sudo systemctl status leaf-health"
echo "   Stop instance:  (AWS Console) EC2 → Stop Instance"
echo ""
echo "💡 Remember: Stop your EC2 instance when not using it!"
echo "   This saves your AWS Learner Lab budget."
echo ""
