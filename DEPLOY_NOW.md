# 🚀 READY TO DEPLOY - EC2: 44.195.35.212

## ✅ Your Files Are AWS-Ready!

All your files have been configured for your EC2 instance at **44.195.35.212**.

### What Was Changed:
- ✅ **app.js** → API_URL changed to `http://44.195.35.212/predict`
- ✅ **login.html** → API_URL changed to `http://44.195.35.212`
- ✅ **register.html** → API_URL changed to `http://44.195.35.212`
- ✅ **app.py** → CORS updated to allow your EC2 IP
- ✅ **Python 3.11** deployment script included

---

## 📦 Step 1: Upload Files to EC2

### Option A: Using SCP (Recommended)

**From your LOCAL computer**, open a terminal and run:

```bash
# Navigate to where you downloaded the files
cd ~/Downloads  # Or wherever you saved them

# Upload all files to EC2
scp -i labsuser.pem \
  app.js app.py index.html login.html register.html \
  style.css requirements.txt .env tomato_model.pt \
  deploy_aws_ready.sh \
  ubuntu@44.195.35.212:~/leaf-health-app/
```

### Option B: Upload One by One

If the above doesn't work, upload files individually:

```bash
scp -i labsuser.pem app.js ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem app.py ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem index.html ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem login.html ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem register.html ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem style.css ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem requirements.txt ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem .env ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem tomato_model.pt ubuntu@44.195.35.212:~/leaf-health-app/
scp -i labsuser.pem deploy_aws_ready.sh ubuntu@44.195.35.212:~/leaf-health-app/
```

---

## 🔧 Step 2: Connect to EC2

In your **AWS Learner Lab terminal** (or any terminal):

```bash
ssh -i ~/.ssh/labsuser.pem ubuntu@44.195.35.212
```

Type `yes` if asked about connecting.

---

## 🎯 Step 3: Create App Directory (If Needed)

```bash
mkdir -p ~/leaf-health-app
cd ~/leaf-health-app
```

---

## ⚡ Step 4: Deploy with ONE Command

After uploading files and connecting to EC2:

```bash
cd ~/leaf-health-app
chmod +x deploy_aws_ready.sh
./deploy_aws_ready.sh
```

**That's it!** The script will:
1. ✅ Install Python 3.11
2. ✅ Create virtual environment
3. ✅ Install all dependencies (PyTorch, FastAPI, etc.)
4. ✅ Verify your files are AWS-ready
5. ✅ Create systemd service
6. ✅ Configure Nginx
7. ✅ Start your application

Takes about 5-10 minutes total.

---

## 🌐 Step 5: Access Your App!

Open your browser and go to:

```
http://44.195.35.212
```

You should see your login page!

### Test the app:
1. Click "Register here"
2. Create a new account
3. Login
4. Upload a tomato leaf image
5. Click "Analyze"
6. See the AI prediction! 🎉

---

## 🔍 Troubleshooting

### Check if service is running:
```bash
sudo systemctl status leaf-health
```

### View logs:
```bash
# Real-time logs
sudo journalctl -u leaf-health -f

# Last 50 log lines
sudo journalctl -u leaf-health -n 50
```

### Check Nginx:
```bash
sudo systemctl status nginx
```

### Test the app locally:
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok","device":"cpu"}
```

### Restart everything:
```bash
sudo systemctl restart leaf-health
sudo systemctl restart nginx
```

### App won't start?
Check for errors:
```bash
sudo journalctl -u leaf-health -n 100 --no-pager
```

Most common issues:
- ❌ .env file missing or has wrong database URL
- ❌ tomato_model.pt file not uploaded
- ❌ Port 80 not open in security group

---

## 📋 Useful Commands

```bash
# Start service
sudo systemctl start leaf-health

# Stop service
sudo systemctl stop leaf-health

# Restart service
sudo systemctl restart leaf-health

# View logs (real-time)
sudo journalctl -u leaf-health -f

# Check if port 8000 is listening
sudo lsof -i :8000

# Check if port 80 is listening
sudo lsof -i :80

# Test health endpoint
curl http://localhost:8000/health
```

---

## 💰 Budget Management

**IMPORTANT:** Your EC2 instance costs money while running!

### Cost:
- **t3.medium**: ~$0.04/hour = ~$1/day
- If you run it 24/7 for a month: ~$30

### Stop Instance When Done:
1. Go to AWS Console
2. EC2 → Instances
3. Select your instance
4. Actions → Instance State → **Stop**

### Restart Later:
1. Actions → Instance State → **Start**
2. **Note:** Public IP will change!
3. You'll need to re-run the deployment with the new IP

---

## 🔐 Security Notes

Current setup (for learning):
- ✅ HTTP (not HTTPS)
- ✅ CORS allows all origins
- ✅ Basic authentication with JWT

For production, you'd want:
- HTTPS with SSL certificate
- Restricted CORS
- Rate limiting
- Firewall rules

---

## 📁 File Checklist

Make sure all these files are in `/home/ubuntu/leaf-health-app/`:

```
✅ app.py                    # FastAPI backend
✅ app.js                    # Frontend JavaScript
✅ index.html                # Main page
✅ login.html                # Login page
✅ register.html             # Registration page
✅ style.css                 # Styles
✅ requirements.txt          # Python dependencies
✅ .env                      # Environment variables
✅ tomato_model.pt           # PyTorch model (16MB)
✅ deploy_aws_ready.sh       # Deployment script
```

---

## ✅ Success Indicators

Your app is working if:

1. ✅ `sudo systemctl status leaf-health` shows "active (running)" in green
2. ✅ `curl http://localhost:8000/health` returns `{"status":"ok"}`
3. ✅ Browser can load `http://44.195.35.212`
4. ✅ Can register a new user
5. ✅ Can login
6. ✅ Can upload and analyze images
7. ✅ No errors in browser console (F12 → Console)

---

## 🆘 Still Having Issues?

### Database connection error?
Check your .env file:
```bash
cat .env
```

Make sure DATABASE_URL is correct (starts with `postgresql://`)

### Model not loading?
Check if file exists:
```bash
ls -lh tomato_model.pt
# Should show ~16MB file
```

### Can't access from browser?
1. Check security group in EC2 console
2. Make sure port 80 is open to 0.0.0.0/0
3. Try accessing: `http://44.195.35.212/health`

### Python errors?
Make sure you're using Python 3.11:
```bash
source ~/leaf-health-app/venv/bin/activate
python --version  # Should say 3.11.x
```

---

## 🎉 You're All Set!

Your Leaf Health Analyzer is ready to deploy on AWS!

**Quick Start:**
1. Upload files with SCP
2. SSH into EC2
3. Run `./deploy_aws_ready.sh`
4. Visit `http://44.195.35.212`

**Questions?** Check the logs:
```bash
sudo journalctl -u leaf-health -f
```

**Have fun with your AI-powered plant health analyzer!** 🌿🚀
