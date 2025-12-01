# 🚀 Deployment Guide - Financial Advisor to Render

## Prerequisites

- ✅ GitHub account
- ✅ Render account (sign up at https://render.com)
- ✅ OpenAI API Key
- ✅ Google Gemini API Key

---

## Step 1: Prepare GitHub Repository

### 1.1 Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `financial-advisor` (atau nama yang Anda inginkan)
3. Description: "AI-Powered Financial Management Assistant"
4. Public or Private (pilih sesuai kebutuhan)
5. **DO NOT** initialize with README (kita sudah punya)
6. Click "Create repository"

### 1.2 Push Code to GitHub

Buka terminal di folder project:

```bash
# Initialize git (jika belum)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Financial Advisor v1.0"

# Add remote repository (ganti dengan URL repo Anda)
git remote add origin https://github.com/YOUR_USERNAME/financial-advisor.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 1.3 Verify Files

Pastikan file-file ini ada di GitHub:
- ✅ `render.yaml`
- ✅ `startup.sh`
- ✅ `requirements.txt`
- ✅ `.gitignore`
- ✅ Folder `backend/` dengan semua files
- ✅ Folder `public/` dengan semua files

---

## Step 2: Setup Render

### 2.1 Connect GitHub to Render

1. Login ke https://dashboard.render.com
2. Klik **"New +"** button
3. Pilih **"Blueprint"**
4. Klik **"Connect account"** untuk connect GitHub
5. Authorize Render untuk akses GitHub repository Anda
6. Pilih repository **"financial-advisor"** (atau nama repo Anda)
7. Klik **"Connect"**

### 2.2 Configure Blueprint

Render akan detect `render.yaml` automatically:

1. **Branch**: main (atau branch yang Anda gunakan)
2. **Blueprint Name**: financial-advisor
3. Review services yang akan dibuat:
   - ✅ Web Service: `financial-advisor`
   - ✅ PostgreSQL Database: `financial-advisor-db`

### 2.3 Add Environment Variables

Sebelum deploy, set environment variables:

1. Di dashboard Render, pilih service **"financial-advisor"**
2. Go to **"Environment"** tab
3. Add environment variables:

```
OPENAI_API_KEY = sk-... (your OpenAI API key)
GOOGLE_API_KEY = AI... (your Google Gemini API key)
```

**Note**: 
- `FLASK_SECRET_KEY` akan auto-generated
- `DATABASE_URL` akan auto-generated dari PostgreSQL database
- `PORT` sudah diset di render.yaml

### 2.4 Deploy

1. Klik **"Apply"** atau **"Create Blueprint Instance"**
2. Render akan:
   - Create PostgreSQL database
   - Build web service
   - Install dependencies
   - Initialize database
   - Start application
3. Wait 5-10 minutes untuk first deployment

---

## Step 3: Verify Deployment

### 3.1 Check Build Logs

1. Di Render dashboard, pilih service **"financial-advisor"**
2. Go to **"Logs"** tab
3. Verify no errors:

```
🚀 Starting Financial Advisor...
📦 Initializing database...
✅ Database initialized
👤 Creating admin user...
✅ Starting Flask server with Gunicorn...
```

### 3.2 Get Your App URL

1. Di service dashboard, lihat di atas:
   ```
   https://financial-advisor-xxxx.onrender.com
   ```
2. Copy URL ini

### 3.3 Test Application

1. Open URL di browser
2. Should redirect to login page
3. Test features:
   - ✅ Register new user
   - ✅ Login
   - ✅ Chat with AI
   - ✅ Add transaction
   - ✅ Create savings goal

---

## Step 4: Database Management

### 4.1 Access Database

Di Render dashboard:

1. Go to **"Databases"** tab
2. Select **"financial-advisor-db"**
3. You can see:
   - Connection string
   - Database credentials
   - Connection info

### 4.2 Connect via psql (Optional)

```bash
# Connect to database
psql <connection-string>

# Check tables
\dt

# Check users
SELECT * FROM users;

# Check transactions
SELECT * FROM transactions LIMIT 10;
```

### 4.3 Create Admin User

Admin user dibuat otomatis saat startup. Default credentials:

```
Username: admin
Email: admin@financialadvisor.com
Password: admin123
```

**⚠️ IMPORTANT**: Change admin password setelah first login!

---

## Step 5: Custom Domain (Optional)

### 5.1 Setup Custom Domain

1. Di service dashboard, go to **"Settings"** tab
2. Scroll to **"Custom Domain"**
3. Click **"Add Custom Domain"**
4. Enter your domain: `financialadvisor.yourdomain.com`
5. Follow DNS configuration instructions

### 5.2 Configure DNS

Add CNAME record di DNS provider:

```
Type: CNAME
Name: financialadvisor
Value: financial-advisor-xxxx.onrender.com
TTL: 3600
```

### 5.3 Wait for SSL

Render akan automatically provision SSL certificate (5-10 minutes).

---

## Step 6: Monitoring & Maintenance

### 6.1 Monitor Application

**Render Dashboard:**
- Check **"Metrics"** tab untuk CPU, Memory usage
- Check **"Logs"** tab untuk errors
- Check **"Events"** tab untuk deployment history

### 6.2 Auto-Deploy on Push

Render automatically redeploys saat Anda push ke GitHub:

```bash
# Make changes locally
git add .
git commit -m "Update features"
git push origin main

# Render will auto-detect and redeploy
```

### 6.3 Manual Deploy

Jika perlu manual deploy:

1. Go to service dashboard
2. Click **"Manual Deploy"** button
3. Select branch
4. Click **"Deploy"**

---

## Troubleshooting

### Issue 1: Build Failed

**Check logs untuk:**
- Missing dependencies → Update `requirements.txt`
- Python version mismatch → Check `render.yaml`
- Import errors → Check file structure

**Solution:**
```bash
# Test locally first
pip install -r requirements.txt
python backend/main.py
```

### Issue 2: Database Connection Error

**Check:**
- `DATABASE_URL` environment variable set correctly
- Database service running
- Connection string format correct

**Solution:**
1. Go to Database dashboard
2. Copy connection string
3. Update environment variable manually if needed

### Issue 3: Application Crashes

**Check logs untuk:**
- Missing API keys (OPENAI_API_KEY, GOOGLE_API_KEY)
- Port binding issues
- Database migration errors

**Solution:**
```bash
# Check environment variables in Render dashboard
# Verify all required env vars are set
```

### Issue 4: Static Files Not Loading

**Check:**
- File paths correct in HTML
- `/static/` route working
- Files exist in GitHub repository

**Solution:**
```bash
# Verify file structure
ls public/static/
# Should show: app.js, styles.css, etc.
```

---

## Performance Optimization

### Free Tier Limitations

**Render Free Plan:**
- ✅ 750 hours/month
- ✅ Auto-sleep after 15 min inactivity
- ✅ Cold start ~30 seconds
- ⚠️ Limited CPU/RAM

### Keep App Awake (Optional)

Use external service to ping your app every 14 minutes:
- https://uptimerobot.com (Free)
- https://cron-job.org (Free)

**Ping endpoint:**
```
GET https://your-app.onrender.com/
Every 14 minutes
```

### Upgrade to Paid Plan

For production use:
- **Starter Plan**: $7/month
  - No sleep
  - Better performance
  - Custom domain included
  - More CPU/RAM

---

## Security Checklist

- [ ] Change admin password immediately after first login
- [ ] Add strong `FLASK_SECRET_KEY` (auto-generated by Render)
- [ ] Use environment variables for all secrets (never commit to Git)
- [ ] Enable HTTPS (automatic with Render)
- [ ] Keep API keys secure
- [ ] Regular security updates: `pip install --upgrade package_name`

---

## Maintenance Tasks

### Weekly
- [ ] Check logs for errors
- [ ] Monitor database size
- [ ] Check app performance

### Monthly
- [ ] Update dependencies: `pip list --outdated`
- [ ] Review user feedback
- [ ] Backup database

### Quarterly
- [ ] Security audit
- [ ] Performance optimization
- [ ] Feature updates

---

## Backup & Recovery

### Database Backup

**Option 1: Manual Backup**
```bash
# Export database
pg_dump <connection-string> > backup.sql

# Import database
psql <connection-string> < backup.sql
```

**Option 2: Render Backup (Paid Plans)**
- Automatic daily backups
- Point-in-time recovery
- Available on paid plans

---

## Support & Resources

### Render Documentation
- https://render.com/docs
- https://render.com/docs/deploy-flask

### Community
- Render Community: https://community.render.com
- GitHub Issues: Your repository issues page

### Contact
- Render Support: support@render.com (paid plans)
- Community Forum: Free support

---

## 🎉 Deployment Checklist

Before going live:

- [ ] ✅ Code pushed to GitHub
- [ ] ✅ Render service created and deployed
- [ ] ✅ Database initialized
- [ ] ✅ Environment variables set (API keys)
- [ ] ✅ Admin user created
- [ ] ✅ Application accessible via URL
- [ ] ✅ All features tested and working
- [ ] ✅ Change admin password
- [ ] ✅ Monitor logs for errors
- [ ] ✅ Setup monitoring/alerts (optional)

---

## Next Steps After Deployment

1. **Share with users** - Get feedback
2. **Monitor usage** - Check analytics
3. **Fix bugs** - Address issues quickly
4. **Add features** - Follow ROADMAP.md
5. **Scale** - Upgrade plan when needed

---

**Congratulations! Your Financial Advisor app is now live! 🚀**

Last Updated: December 1, 2025
Version: 1.0 Production
