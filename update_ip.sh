#!/bin/bash
# Quick script to update IP address in .env file
# Run this after your EC2 IP changes

set -e

echo "========================================"
echo "🔄 EC2 IP Update Helper"
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in current directory"
    echo "   Make sure you're in ~/leaf-health-app/"
    exit 1
fi

echo "Current ALLOWED_ORIGINS setting:"
grep "ALLOWED_ORIGINS" .env || echo "(not set)"
echo ""

# Option 1: Auto-detect IP
echo "Option 1: Auto-detect EC2 public IP"
DETECTED_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "")
if [ -n "$DETECTED_IP" ]; then
    echo "   Detected IP: $DETECTED_IP"
    read -p "   Use this IP? (y/n): " use_detected
    if [ "$use_detected" = "y" ] || [ "$use_detected" = "Y" ]; then
        NEW_IP="$DETECTED_IP"
    fi
fi

# Option 2: Manual entry
if [ -z "$NEW_IP" ]; then
    echo ""
    echo "Option 2: Enter IP manually"
    read -p "   Enter your new EC2 public IP: " NEW_IP
fi

# Validate IP format (basic check)
if ! echo "$NEW_IP" | grep -qE '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'; then
    echo "❌ Error: Invalid IP format"
    exit 1
fi

echo ""
echo "Updating .env file..."

# Backup .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"

# Update the ALLOWED_ORIGINS line
if grep -q "ALLOWED_ORIGINS=" .env; then
    sed -i "s|ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=http://$NEW_IP|" .env
    echo "✅ Updated ALLOWED_ORIGINS"
else
    echo "ALLOWED_ORIGINS=http://$NEW_IP" >> .env
    echo "✅ Added ALLOWED_ORIGINS"
fi

echo ""
echo "New .env setting:"
grep "ALLOWED_ORIGINS" .env
echo ""

# Ask to restart service
read -p "Restart leaf-health service now? (y/n): " restart
if [ "$restart" = "y" ] || [ "$restart" = "Y" ]; then
    echo ""
    echo "Restarting service..."
    sudo systemctl restart leaf-health
    sleep 2
    
    if sudo systemctl is-active --quiet leaf-health; then
        echo "✅ Service restarted successfully"
    else
        echo "❌ Service failed to start"
        echo "   Check logs: sudo journalctl -u leaf-health -n 50"
        exit 1
    fi
fi

echo ""
echo "========================================"
echo "✅ IP Update Complete!"
echo "========================================"
echo ""
echo "Your app is now accessible at:"
echo "   http://$NEW_IP"
echo ""
echo "Test it:"
echo "   curl http://localhost:8000/health"
echo "   curl http://$NEW_IP/health"
echo ""
