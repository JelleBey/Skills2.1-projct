#!/bin/bash
# Security Setup Script
# Generates secure JWT secret and helps configure .env

set -e

echo "========================================"
echo "🔒 Security Configuration Setup"
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
# Environment Variables for Leaf Health Analyzer
# SECURITY: Keep this file secure and never commit to git!

# Database Configuration
DATABASE_URL=your_neon_database_url_here

# JWT Configuration (REQUIRED FOR SECURITY)
JWT_SECRET_KEY=PLACEHOLDER
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
EOF
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "Generating secure JWT secret key..."
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

echo "✅ Generated secure JWT secret"
echo ""
echo "Your secure JWT secret key:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$JWT_SECRET"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Update .env file
if grep -q "JWT_SECRET_KEY=PLACEHOLDER" .env || grep -q "JWT_SECRET_KEY=CHANGE_THIS" .env; then
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" .env
    echo "✅ Updated .env file with secure JWT secret"
else
    echo "⚠️  JWT_SECRET_KEY already set in .env"
    echo "   If you want to replace it, edit .env manually"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Update DATABASE_URL in .env file:"
echo "   nano .env"
echo ""
echo "2. Your DATABASE_URL should look like:"
echo "   postgresql://user:password@host/database"
echo ""
echo "3. Make sure your database has these tables:"
echo "   - users (id, email, password_hash, first_name, last_name)"
echo "   - analyses (id, user_id, predicted_class, confidence, analyzed_at)"
echo ""
echo "4. Create log directory for the app:"
echo "   sudo mkdir -p /var/log/leaf-health"
echo "   sudo chown ubuntu:ubuntu /var/log/leaf-health"
echo ""
echo "5. Run the deployment script:"
echo "   ./deploy_aws_ready.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Security Checklist:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ JWT secret generated"
echo "⬜ DATABASE_URL configured"
echo "⬜ Log directory created"
echo "⬜ HTTPS/SSL configured (do after deployment)"
echo "⬜ Firewall rules configured"
echo "⬜ Regular backups scheduled"
echo ""
echo "⚠️  IMPORTANT: Never commit .env to version control!"
echo "   Add .env to your .gitignore file"
echo ""
