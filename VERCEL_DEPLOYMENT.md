# 🚀 Vercel Deployment Guide — DEMS

This guide walks you through deploying the Digital Evidence Management System (DEMS) to Vercel **step by step**.

---

> ## ⚠️ Important — Read Before Deploying
>
> **Vercel is a serverless platform.** This means:
> - Evidence files stored on Vercel use **ephemeral `/tmp` storage** — files are deleted between function cold starts.
> - This app is suitable for **demo/testing** on Vercel.
> - For a **production forensics deployment**, use a persistent server (Railway, Render, VPS) with cloud file storage (AWS S3).
>
> For MongoDB, you **must** use [MongoDB Atlas](https://www.mongodb.com/atlas) (free tier available) — Vercel cannot connect to `localhost`.

---

## 📋 Prerequisites

Before you start, make sure you have:

- ✅ A [GitHub](https://github.com) account (repo already pushed)
- ✅ A [Vercel](https://vercel.com) account (sign up free at vercel.com)
- ✅ A [MongoDB Atlas](https://www.mongodb.com/atlas) account (free M0 cluster)

---

## Step 1 — Set Up MongoDB Atlas (Free Cloud Database)

### 1.1 — Create a Free Account
1. Go to **https://www.mongodb.com/atlas**
2. Click **"Try Free"** → sign up with Google or email

### 1.2 — Create a Free Cluster
1. After login, click **"Build a Database"**
2. Choose **M0 (FREE)** tier
3. Pick any cloud provider and region (e.g., AWS, Mumbai/Singapore)
4. Click **"Create"**

### 1.3 — Create a Database User
1. In the left sidebar, go to **Security → Database Access**
2. Click **"Add New Database User"**
3. Set username: `dems_user`
4. Set a strong password (e.g., `MySecurePass123!`) — **save this**
5. Set role to **"Read and Write to Any Database"**
6. Click **"Add User"**

### 1.4 — Whitelist All IPs (for Vercel)
1. Go to **Security → Network Access**
2. Click **"Add IP Address"**
3. Click **"Allow Access from Anywhere"** → this adds `0.0.0.0/0`
4. Click **"Confirm"**

> Vercel serverless functions use dynamic IPs, so you must allow all IPs.

### 1.5 — Get Your Connection String
1. Go to **Database → Connect**
2. Click **"Connect your application"**
3. Choose **Python** driver, version **3.12 or later**
4. Copy the connection string. It looks like:
   ```
   mongodb+srv://dems_user:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. Replace `<password>` with your actual password from Step 1.3
6. **Save this URI** — you'll need it in Step 3

---

## Step 2 — Prepare Your GitHub Repository

Your code is already on GitHub at: `https://github.com/ashu123-hub/Digital-Evidence`

The Vercel deployment files (`api/index.py` and `vercel.json`) are already included in the repo. No changes needed here.

---

## Step 3 — Deploy on Vercel

### 3.1 — Import Your GitHub Repository
1. Go to **https://vercel.com**
2. Click **"Add New Project"**
3. Click **"Continue with GitHub"** — authorize Vercel to access your repos
4. Find **"Digital-Evidence"** in the list and click **"Import"**

### 3.2 — Configure the Project
On the configuration screen:

| Setting | Value |
|---|---|
| **Framework Preset** | `Other` |
| **Root Directory** | `.` (leave as default) |
| **Build Command** | *(leave empty)* |
| **Output Directory** | *(leave empty)* |
| **Install Command** | `pip install -r requirements.txt` |

### 3.3 — Add Environment Variables
Click **"Environment Variables"** and add these one by one:

| Name | Value |
|---|---|
| `MONGO_URI` | Your MongoDB Atlas URI from Step 1.5 |
| `SECRET_KEY` | Any long random string, e.g. `dems-super-secret-key-2026-forensics` |
| `AES_KEY` | Exactly 32 characters, e.g. `DEMS_AES256_KEY_32BYTES_SECURE!!` |

> **⚠️ AES_KEY must be exactly 32 characters.** Count carefully. The default is already 32 chars.

### 3.4 — Deploy
Click **"Deploy"**. Vercel will:
1. Install Python dependencies
2. Build your app
3. Deploy as a serverless function

Wait 1–2 minutes. You'll see a success screen with your live URL like:
```
https://digital-evidence-xxxx.vercel.app
```

---

## Step 4 — Verify the Deployment

1. Open your Vercel URL in a browser
2. You should see the **DEMS login page**
3. Log in with:
   - Email: `admin@dems.gov`
   - Password: `Admin@123`

> On first login, the app will seed the default users and sample cases into MongoDB Atlas automatically.

---

## Step 5 — Custom Domain (Optional)

1. In your Vercel project dashboard, go to **Settings → Domains**
2. Click **"Add Domain"**
3. Enter your domain name (e.g., `dems.youragency.gov`)
4. Follow Vercel's DNS configuration instructions for your domain registrar

---

## 🔄 Automatic Deployments (CI/CD)

Once connected, **every `git push` to `main` automatically triggers a new deployment** on Vercel.

```bash
# Make a change, then:
git add -A
git commit -m "Your update"
git push origin main
# Vercel auto-deploys within ~1 minute
```

---

## 🐛 Troubleshooting

### "Application Error" on first visit
- Check **Vercel Dashboard → Your Project → Deployments → View Logs**
- Most common cause: wrong `MONGO_URI`

### "MongoServerError: Authentication failed"
- Double-check your MongoDB Atlas password in the URI
- Make sure you replaced `<password>` with the actual password

### Files uploaded but not found later
- This is expected on Vercel — file storage is ephemeral
- For persistent evidence storage, use Railway or a VPS

### Environment variables not working
- In Vercel dashboard → Settings → Environment Variables
- Make sure variables are set for **Production**, **Preview**, and **Development**
- Redeploy after changing variables

---

## 📊 Vercel Limits (Free Tier)

| Limit | Free Tier |
|---|---|
| Serverless Functions | 100 GB-hours/month |
| Bandwidth | 100 GB/month |
| Function execution timeout | 10 seconds |
| `/tmp` storage | 512 MB (ephemeral) |
| Deployments | Unlimited |

---

## 🔒 Production Recommendations

For a real forensics deployment, consider:

1. **Use Railway or Render** — supports persistent disk + MongoDB + custom domains
2. **Use AWS S3** for encrypted evidence storage (modify `crypto_utils.py` to upload to S3)
3. **Use MongoDB Atlas** regardless of where you host
4. **Set strong `SECRET_KEY` and `AES_KEY`** in environment variables
5. **Enable HTTPS** — Vercel and Railway do this automatically

---

## 📞 Support

If you run into issues, check the **Vercel build logs** in your project dashboard under:
`Vercel Dashboard → Project → Deployments → Click on a deployment → View Function Logs`
