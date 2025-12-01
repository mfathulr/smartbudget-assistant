# 🚀 Production Deployment Checklist

## ⚠️ CRITICAL SECURITY ISSUES TO FIX BEFORE PRODUCTION

### 🔴 **URGENT: Remove Sensitive Data from Repository**

Your `.env` file in the repository contains **REAL API KEYS and PASSWORDS**. This is a critical security vulnerability!

**Immediate Actions Required:**

1. **Remove `.env` from Git History**
```bash
# Remove .env from git tracking
git rm --cached backend/.env

# Remove from git history (if already committed)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/.env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (be careful!)
git push origin --force --all
```

2. **Revoke ALL Exposed Keys Immediately:**
   - ✅ **OpenAI API Key**: Go to https://platform.openai.com/api-keys and delete the exposed key
   - ✅ **Google API Key**: Go to https://console.cloud.google.com and regenerate
   - ✅ **Gmail App Password**: Revoke from Google Account settings
   - ✅ **PostgreSQL Password**: Change in Neon console
   - ✅ **reCAPTCHA Keys**: Regenerate from Google reCAPTCHA admin

3. **Generate New Keys After Revoking:**
   - Create new keys for all services
   - Store them ONLY in environment variables or secrets manager
   - Never commit them to git

---

## 📋 Pre-Deployment Checklist

### 🔐 Security

- [ ] **Remove real API keys from all files**
- [ ] **Create `.env.example` with placeholder values** ✅ (Created)
- [ ] **Verify `.gitignore` includes `.env`** ✅ (Already set)
- [ ] **Change `FLASK_SECRET_KEY` to strong random value**
- [ ] **Enable HTTPS in production**
- [ ] **Set secure cookie settings** (httponly, secure, samesite)
- [ ] **Add rate limiting on API endpoints**
- [ ] **Enable CORS properly for your domain**
- [ ] **Re-enable reCAPTCHA with valid production keys**
- [ ] **Add SQL injection protection validation**
- [ ] **Add XSS protection headers**

### 🗄️ Database

- [ ] **Verify PostgreSQL connection is secure (SSL enabled)** ✅
- [ ] **Create database backups strategy**
- [ ] **Set up automated backups in Neon**
- [ ] **Test database connection from production environment**
- [ ] **Remove local SQLite `finance.db` from repo** ✅ (In .gitignore)
- [ ] **Add database migration strategy**

### 📧 Email

- [ ] **Test email sending in production environment**
- [ ] **Verify SMTP credentials work**
- [ ] **Update `APP_URL` to production URL**
- [ ] **Set proper `SMTP_FROM` email address**
- [ ] **Test OTP email delivery**
- [ ] **Test password reset emails**

### 🌐 Frontend

- [ ] **Update API endpoints if using different domain**
- [ ] **Minify CSS/JS files for production**
- [ ] **Optimize images and assets**
- [ ] **Test all pages on mobile devices**
- [ ] **Test all auth flows (register, login, forgot, reset)**
- [ ] **Verify translations work (ID/EN)**
- [ ] **Test responsive design on various screen sizes**

### 📝 Code Quality

- [ ] **Remove all console.log() debug statements**
- [ ] **Remove commented code blocks**
- [ ] **Remove `backend/archive/` from production** ✅ (In .gitignore)
- [ ] **Remove `server.log` from production** ✅ (In .gitignore)
- [ ] **Update README.md with correct GitHub URL**
- [ ] **Update README.md with correct contact info**
- [ ] **Add proper error handling for all endpoints**

### 🚀 Deployment

- [ ] **Set environment variables in Render dashboard**
- [ ] **Test deployment on staging environment first**
- [ ] **Set up health check endpoint**
- [ ] **Configure proper logging**
- [ ] **Set up monitoring (Sentry, etc.)**
- [ ] **Configure auto-deploy from main branch**
- [ ] **Test all features after deployment**

### 📊 Monitoring

- [ ] **Set up error tracking (Sentry, Rollbar)**
- [ ] **Configure uptime monitoring**
- [ ] **Set up log aggregation**
- [ ] **Monitor API rate limits (OpenAI, Gemini)**
- [ ] **Set up alerts for critical errors**

---

## 🔧 Configuration Files to Update

### 1. `render.yaml`
```yaml
services:
  - type: web
    name: smartbudget-assistant
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --chdir backend main:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: OPENAI_API_KEY
        sync: false
      - key: GOOGLE_API_KEY
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: FLASK_SECRET_KEY
        sync: false
      - key: SMTP_HOST
        sync: false
      - key: SMTP_PORT
        value: 587
      - key: SMTP_USER
        sync: false
      - key: SMTP_PASSWORD
        sync: false
      - key: SMTP_FROM
        sync: false
      - key: APP_URL
        value: https://your-app.onrender.com
```

### 2. `backend/main.py` - Add Production Settings
```python
# At the top of file
import os
from flask import Flask

app = Flask(__name__, static_folder='../public', static_url_path='')

# Production settings
if os.environ.get('RENDER'):
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
```

### 3. Add `requirements.txt` at root level
```txt
# Copy from backend/requirements.txt and add:
gunicorn==21.2.0
psycopg2-binary==2.9.9
```

---

## 🚨 BEFORE FIRST PUSH TO GITHUB

1. **Double-check `.env` is in `.gitignore`** ✅
2. **Verify no sensitive data in any file**
3. **Replace all placeholder text in README**
4. **Test the application locally one more time**
5. **Create `.env.example` with safe values** ✅

---

## 📝 Recommended File Structure Improvements

### Current Issues:
1. ✅ `.env` exposed (CRITICAL - fix immediately)
2. ⚠️ `finance.db` files in multiple locations
3. ⚠️ `server.log` should not be committed
4. ✅ Archive folder properly ignored

### Recommended Structure:
```
FinancialAdvisor/
├── .env.example          ✅ Created
├── .gitignore            ✅ Good
├── README.md             ⚠️ Update URLs and contact
├── requirements.txt      ✅ Add at root for Render
├── render.yaml           ⚠️ Update with proper config
├── backend/
│   ├── .env             🔴 NEVER COMMIT
│   ├── main.py          ⚠️ Add production settings
│   └── ...
└── public/
    ├── uploads/avatars/
    │   └── .gitkeep     ✅ Created
    └── ...
```

---

## ✅ Quick Start Commands

```bash
# 1. Clean sensitive data
git rm --cached backend/.env
rm backend/.env  # Delete local copy

# 2. Create new .env from example
cp .env.example backend/.env
# Edit backend/.env with NEW secure keys

# 3. Update .gitignore (already good)

# 4. Commit changes
git add .
git commit -m "chore: prepare for production deployment

- Remove sensitive data from repository
- Add .env.example with safe placeholders
- Add production checklist
- Update security configurations"

# 5. Push to GitHub
git push origin main
```

---

## 🎯 Priority Order

### **CRITICAL (Do BEFORE pushing to GitHub):**
1. ✅ Remove `.env` from git
2. ✅ Revoke all exposed API keys
3. ✅ Generate new keys
4. ✅ Create `.env.example`

### **HIGH (Do BEFORE production deployment):**
1. Update README.md URLs
2. Add production security settings
3. Enable reCAPTCHA with valid keys
4. Test all features thoroughly

### **MEDIUM (Do DURING deployment):**
1. Set environment variables in Render
2. Configure monitoring
3. Set up backups

### **LOW (Do AFTER deployment):**
1. Optimize assets
2. Add analytics
3. Set up CI/CD

---

## 📞 Need Help?

If you need assistance with any of these steps, please consult:
- Render Documentation: https://render.com/docs
- Flask Security Best Practices
- OWASP Security Guidelines

---

**⚠️ DO NOT DEPLOY TO PRODUCTION UNTIL CRITICAL SECURITY ISSUES ARE FIXED! ⚠️**
