# ✈️ PRE-DEPLOYMENT CHECKLIST

## Before You Start

### 1. EC2 Instance Ready?
- [ ] Instance is **Running** (not stopped/terminated)
- [ ] Instance type: **t3.medium** or larger (need 4GB RAM for PyTorch)
- [ ] Public IP: **44.195.35.212** (confirmed)
- [ ] Can SSH into instance: `ssh -i ~/.ssh/labsuser.pem ubuntu@44.195.35.212`

### 2. Security Group Configured?
- [ ] Port **22** (SSH) - Open to your IP
- [ ] Port **80** (HTTP) - Open to 0.0.0.0/0 (anywhere)
- [ ] Port **443** (HTTPS) - Open to 0.0.0.0/0 (optional)

### 3. Files Downloaded?
- [ ] app.js ✅ (configured for 44.195.35.212)
- [ ] app.py ✅ (CORS updated)
- [ ] index.html
- [ ] login.html ✅ (configured for 44.195.35.212)
- [ ] register.html ✅ (configured for 44.195.35.212)
- [ ] style.css
- [ ] requirements.txt
- [ ] .env (with your actual database URL!)
- [ ] tomato_model.pt (~16MB)
- [ ] deploy_aws_ready.sh

### 4. Database Ready?
- [ ] Neon PostgreSQL database created
- [ ] Database URL copied to .env file
- [ ] Tables created (users, analyses)

### 5. SSH Key Ready?
- [ ] Downloaded labsuser.pem from AWS Learner Lab
- [ ] File permissions set: `chmod 400 labsuser.pem`
- [ ] Can connect: `ssh -i labsuser.pem ubuntu@44.195.35.212`

---

## Deployment Steps

### Step 1: Upload Files (5 minutes)
```bash
# From your LOCAL computer
cd ~/Downloads  # Or wherever files are

scp -i labsuser.pem \
  app.js app.py index.html login.html register.html \
  style.css requirements.txt .env tomato_model.pt \
  deploy_aws_ready.sh \
  ubuntu@44.195.35.212:~/leaf-health-app/
```

### Step 2: Connect to EC2 (1 minute)
```bash
ssh -i ~/.ssh/labsuser.pem ubuntu@44.195.35.212
```

### Step 3: Deploy! (10 minutes)
```bash
cd ~/leaf-health-app
chmod +x deploy_aws_ready.sh
./deploy_aws_ready.sh
```

### Step 4: Test (2 minutes)
Open browser: `http://44.195.35.212`

---

## Quick Commands

### If SCP doesn't work:
```bash
# Create directory first
ssh -i labsuser.pem ubuntu@44.195.35.212 "mkdir -p ~/leaf-health-app"

# Then upload files one by one
scp -i labsuser.pem app.js ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem app.py ubuntu@44.195.35.212:~/leaf-health-app/
# ... etc
```

### Check connection:
```bash
# Can you reach the server?
ping 44.195.35.212

# Can you SSH?
ssh -i labsuser.pem ubuntu@44.195.35.212 "echo 'Connected!'"
```

### Verify files after upload:
```bash
ssh -i labsuser.pem ubuntu@44.195.35.212 "ls -lh ~/leaf-health-app/"
```

---

## Common Issues

### ❌ "Permission denied (publickey)"
**Fix:**
```bash
# Make sure key permissions are correct
chmod 400 labsuser.pem

# Use the full path to key
ssh -i /full/path/to/labsuser.pem ubuntu@44.195.35.212
```

### ❌ "Connection refused"
**Fix:**
- Check instance is **Running** in AWS Console
- Check security group allows SSH (port 22)
- Verify you're using correct IP: 44.195.35.212

### ❌ "scp: command not found"
**Windows users:** Install OpenSSH or use WinSCP instead

### ❌ "Model file too large"
**Fix:** Model file is 16MB - this is normal. Just be patient during upload.

---

## Testing Checklist

After deployment, test these:

### Basic Tests:
- [ ] Can access `http://44.195.35.212`
- [ ] Login page loads
- [ ] Can click "Register here"
- [ ] Registration form appears

### Full Test:
- [ ] Create new account (use real email)
- [ ] Login works
- [ ] Main page loads
- [ ] Can upload image
- [ ] "Analyze" button works
- [ ] Results appear

### Technical Tests:
```bash
# Service running?
sudo systemctl status leaf-health

# Nginx running?
sudo systemctl status nginx

# App responds?
curl http://localhost:8000/health

# Logs clean?
sudo journalctl -u leaf-health -n 20
```

---

## Budget Check

### Current Status:
- Instance: t3.medium
- Cost: ~$0.04/hour
- Daily cost: ~$1.00
- Monthly cost: ~$30

### Time Running:
Check AWS Learner Lab interface for budget used.

### When Done:
**STOP THE INSTANCE!**
```bash
# From AWS Console:
EC2 → Instances → Select → Actions → Stop
```

---

## Next Steps After Successful Deployment

1. **Test thoroughly** - Try all features
2. **Check logs** - `sudo journalctl -u leaf-health -f`
3. **Monitor performance** - `htop` or `top`
4. **Stop instance** when not using
5. **Document** any issues for next time

---

## Support

**Logs:**
```bash
# Service logs
sudo journalctl -u leaf-health -n 100

# Nginx logs
sudo tail -f /var/log/nginx/error.log

# System logs
dmesg | tail -50
```

**Status Check:**
```bash
# Is everything running?
sudo systemctl status leaf-health nginx

# Listening on correct ports?
sudo netstat -tuln | grep -E ':(80|8000) '
```

---

## ✅ Ready to Deploy?

If all boxes are checked above, you're ready!

**Run:**
```bash
./deploy_aws_ready.sh
```

**Then visit:**
```
http://44.195.35.212
```

**Good luck! 🚀**
