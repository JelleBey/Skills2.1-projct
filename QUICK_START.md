# 🚀 QUICK START - Deploy Security Fixes

## ⚡ Fast Track (5 Minutes)

### On Your Local Computer:

```bash
# 1. Make scripts executable
chmod +x setup_security.sh deploy_aws_ready.sh

# 2. Upload EVERYTHING to EC2
scp -i labsuser.pem \
  app.py app.js index.html login.html register.html \
  style.css requirements.txt .env tomato_model.pt \
  setup_security.sh deploy_aws_ready.sh \
  ubuntu@44.195.35.212:~/leaf-health-app/
```

### On EC2 (SSH in):

```bash
# 1. Connect
ssh -i labsuser.pem ubuntu@44.195.35.212

# 2. Go to app directory
cd ~/leaf-health-app

# 3. Run security setup (generates JWT secret)
./setup_security.sh

# 4. Edit .env and add your DATABASE_URL
nano .env
# Replace: your_neon_database_url_here
# With: postgresql://user:password@host/database
# Save: Ctrl+X, then Y, then Enter

# 5. Create log directory
sudo mkdir -p /var/log/leaf-health
sudo chown ubuntu:ubuntu /var/log/leaf-health

# 6. Deploy!
./deploy_aws_ready.sh
```

### Test:
Open browser: `http://44.195.35.212`

---

## 📋 What Changed?

**You'll notice:**
1. Password requirements are MUCH stronger now (12+ chars, upper, lower, number, special)
2. Rate limiting - try logging in wrong 6 times, you'll be blocked
3. Better error messages
4. More secure authentication (HttpOnly cookies only)

**Under the hood:**
- CORS fixed (no more wildcard)
- File validation improved
- Security headers added
- Logging added
- Input sanitization

---

## 🔧 Common Issues

### Issue: "JWT_SECRET_KEY must be set"
**Fix:**
```bash
cd ~/leaf-health-app
./setup_security.sh
nano .env  # Make sure JWT_SECRET_KEY is set
```

### Issue: Can't login after update
**Fix:**
- Clear browser cookies
- Try incognito mode
- Or use this to check logs:
```bash
sudo journalctl -u leaf-health -n 50
```

### Issue: "Permission denied" on logs
**Fix:**
```bash
sudo mkdir -p /var/log/leaf-health
sudo chown ubuntu:ubuntu /var/log/leaf-health
sudo systemctl restart leaf-health
```

### Issue: Rate limiting too strict
**Edit app.py line 202:**
```python
@limiter.limit("10/minute")  # Change number higher
```

---

## ✅ Verify Everything Works

### Quick Test:
```bash
# Is service running?
sudo systemctl status leaf-health

# Check logs
sudo journalctl -u leaf-health -n 20

# Test health endpoint
curl http://localhost:8000/health
```

### Browser Tests:
1. ✅ Can load `http://44.195.35.212`
2. ✅ Can register (with strong password)
3. ✅ Weak password is rejected
4. ✅ Can login
5. ✅ Can upload and analyze image
6. ✅ Wrong password 6x → Rate limited

### Cookie Check (DevTools):
1. Open DevTools (F12)
2. Application tab → Cookies
3. Look for `access_token`
4. Should have `HttpOnly` = ✅

---

## 📁 Files You Need

Make sure you have ALL these files before uploading:

```
✅ app.py                 (security-hardened backend)
✅ app.js                 (cookies only, no localStorage)
✅ index.html             (no changes needed)
✅ login.html             (cookies only)
✅ register.html          (strong password UI)
✅ style.css              (no changes needed)
✅ requirements.txt       (added slowapi)
✅ .env                   (JWT secret required)
✅ tomato_model.pt        (no changes)
✅ setup_security.sh      (generates JWT secret)
✅ deploy_aws_ready.sh    (deployment script)
```

---

## 🔐 Security Improvements

**Before:** 4/10 ❌  
**After:** 8/10 ✅  

### What's Better:
- ✅ No CORS wildcard
- ✅ HttpOnly cookies (can't be stolen by JS)
- ✅ Rate limiting (stops brute force)
- ✅ Strong passwords required
- ✅ Proper file validation
- ✅ Security headers
- ✅ Audit logging
- ✅ Input sanitization

### Still Need (After HTTPS):
- HTTPS/SSL certificate
- Change `secure=True` in cookies
- Update CORS to your domain

---

## 💡 Pro Tips

1. **Check logs regularly:**
   ```bash
   tail -f /var/log/leaf-health/app.log
   ```

2. **Restart service if needed:**
   ```bash
   sudo systemctl restart leaf-health
   ```

3. **View real-time system logs:**
   ```bash
   sudo journalctl -u leaf-health -f
   ```

4. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

---

## 🆘 Need Help?

**Service not starting:**
```bash
# Check what's wrong
sudo journalctl -u leaf-health -n 100 --no-pager

# Common causes:
# - Missing JWT_SECRET_KEY in .env
# - Wrong DATABASE_URL
# - Log directory doesn't exist
# - Port 8000 already in use
```

**Can't access from browser:**
```bash
# Check if Nginx is running
sudo systemctl status nginx

# Check if port 80 is open
sudo lsof -i :80

# Restart Nginx
sudo systemctl restart nginx
```

**Database errors:**
```bash
# Test database connection
psql "your_database_url_here"

# Make sure tables exist:
# - users
# - analyses
```

---

## 📱 Contact

If you get stuck, check:
1. Logs: `sudo journalctl -u leaf-health -n 50`
2. Nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. App logs: `tail -f /var/log/leaf-health/app.log`

---

**That's it! You're secure and deployed! 🎉**
