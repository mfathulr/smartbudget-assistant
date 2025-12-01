# 🚀 Quick Deployment Commands

## Step 1: Push to GitHub

```bash
# Initialize git (if not done yet)
git init

# Add all files
git add .

# Commit
git commit -m "Deploy: Financial Advisor v1.0 to Render"

# Add remote (replace with your GitHub repo URL)
git remote add origin https://github.com/YOUR_USERNAME/financial-advisor.git

# Push to main branch
git branch -M main
git push -u origin main
```

## Step 2: Deploy on Render

1. Go to https://dashboard.render.com
2. Click "New +" → "Blueprint"
3. Connect GitHub repository: `financial-advisor`
4. Click "Apply"
5. Add environment variables:
   - `OPENAI_API_KEY`
   - `GOOGLE_API_KEY`
6. Wait for deployment (~5-10 minutes)

## Step 3: Test Live App

```
URL: https://financial-advisor-xxxx.onrender.com
```

Test:
- ✅ Register user
- ✅ Login
- ✅ Chat with AI
- ✅ Add transaction

---

## Future Updates

When you make changes:

```bash
# Make your changes
git add .
git commit -m "Update: description of changes"
git push origin main

# Render will auto-deploy!
```

---

## Emergency Rollback

If something breaks:

```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Or rollback in Render dashboard:
# Service → Events → Select previous deploy → Rollback
```

---

## Monitor Application

**Render Dashboard:**
- Logs: Check for errors
- Metrics: CPU, Memory usage
- Events: Deployment history

**Direct Access:**
```bash
# View logs
https://dashboard.render.com/web/YOUR_SERVICE_ID/logs

# View metrics
https://dashboard.render.com/web/YOUR_SERVICE_ID/metrics
```

---

## Need Help?

See detailed guide: `DEPLOYMENT.md`
