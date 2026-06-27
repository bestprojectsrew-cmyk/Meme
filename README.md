# MemePulse AI — Web App (Phases 0-2)

This is your meme bot as a real website you open in a browser. No terminal, no
Python install, nothing technical required to *use* it day-to-day. There's a
one-time setup (about 20-30 minutes) to get it live, and I've written every
click below.

## What this app does

1. You click **"Generate new memes"**
2. It pulls today's trending topics (World Cup, viral news, whatever's hot)
3. AI writes Gen Z-style meme captions for those trends
4. It renders actual meme images
5. They show up in your dashboard for you to **Approve** or **Skip**
6. Once approved, you click **"Post to Instagram"** and it goes live

Every meme is reviewed by you before anything is ever posted. Nothing posts itself automatically — that's intentional, so you stay in control.

---

## Part A: Get it live on the internet (one-time, ~15 minutes)

We'll use **Railway** — a hosting service with a genuinely free tier, connected
to GitHub, where deployment is just clicking buttons (no commands).

### Step 1: Create a GitHub account (skip if you have one)
Go to https://github.com/signup and create a free account.

### Step 2: Create a new repository and upload this code
1. Go to https://github.com/new
2. Name it `memepulse-ai` (or anything you like)
3. Keep it **Public** or **Private**, either is fine
4. Click **Create repository**
5. On the next page, click **uploading an existing file**
6. Drag in *all* the files and folders from this project (unzip it first)
7. Click **Commit changes** at the bottom

### Step 3: Get a free Gemini API key (for the AI captions)
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with any Google account
3. Click **Create API Key** — free, no credit card
4. Copy the key somewhere safe, you'll paste it in Step 5

### Step 4: Deploy to Railway
1. Go to https://railway.app and sign up (you can use your GitHub account to sign in)
2. Click **New Project** → **Deploy from GitHub repo**
3. Pick the `memepulse-ai` repo you just created
4. Railway will detect it's a Python app and start building automatically

### Step 5: Add your API key to Railway
1. In your Railway project, click on the service (the box representing your app)
2. Go to the **Variables** tab
3. Click **New Variable**
4. Add: Name = `GEMINI_API_KEY`, Value = *(paste the key from Step 3)*
5. Click **Add**

Railway will automatically redeploy with the new variable.

### Step 6: Get your live link
1. In Railway, go to the **Settings** tab of your service
2. Under **Networking**, click **Generate Domain**
3. You'll get a link like `memepulse-ai-production.up.railway.app`
4. Open it in your browser — that's your app, live on the internet

**Bookmark this link.** This is your dashboard from now on, on any device.

---

## Part B: Connect Instagram (do this when you're ready to actually post)

This part has steps only you can do, since they involve your personal Instagram
account. Take your time with this part - Meta's setup is the fiddliest part of
the whole project, not because the rest of this app is incomplete, but because
this is genuinely how Meta requires every automated posting tool to connect.

### Step 1: Convert your Instagram to a Business or Creator account
1. Open Instagram app → your profile → menu (☰) → **Settings and privacy**
2. **Account type and tools** → **Switch to professional account**
3. Choose **Creator** or **Business** (either works for posting)

### Step 2: Link it to a Facebook Page
1. You need a Facebook Page (not a personal profile) — create one free at https://www.facebook.com/pages/create if you don't have one
2. In Instagram settings, under professional account setup, choose to connect/link a Facebook Page
3. Follow the prompts to link your new or existing Page

### Step 3: Create a Meta Developer App
1. Go to https://developers.facebook.com/apps and log in with the Facebook account linked to your Page
2. Click **Create App** → choose **Other** → **Business**
3. Give it a name (e.g. "MemePulse AI")
4. Once created, on the app dashboard, find **Instagram** in the products list and click **Set Up**

### Step 4: Get your Access Token and Account ID
This step is the most technical-feeling but it's still just clicking through Meta's interface:
1. In your app dashboard, go to **Tools** → **Graph API Explorer**
2. Select your app from the dropdown, and your Page
3. Request permissions: `instagram_basic`, `instagram_content_publishing`, `pages_show_list`
4. Generate an access token — copy it
5. To find your Instagram Business Account ID, query `me/accounts` then `{page-id}?fields=instagram_business_account` in the same Graph API Explorer — it'll return an ID number

*(If this step confuses you when you get there, bring me the exact screen you're on and I'll tell you exactly what to click.)*

### Step 5: Add these to Railway
Back in Railway → Variables tab, add:
- `IG_ACCESS_TOKEN` = the token from Step 4
- `IG_BUSINESS_ACCOUNT_ID` = the ID number from Step 4

Now the **"Post to Instagram"** button in your dashboard will actually work.

**Note on tokens expiring:** Meta's standard access tokens expire after about 60 days. When posting starts failing after a couple months, it's almost certainly this — come back and I'll walk you through refreshing it.

---

## Important honesty notes

- **I could not test the live Instagram posting or live Gemini calls myself** — my development environment has no internet access. I followed Meta's and Google's official documentation exactly, but you'll be the first real-world test. If something errors, copy the *exact* error text back to me.
- **The image rendering and dashboard design ARE fully tested** — I ran them myself and confirmed they work correctly.
- **Free tier limits**: Gemini's free tier and Railway's free tier both have usage caps. For a few memes a day, you'll likely stay within free limits. If you scale up a lot, you may eventually need a small paid tier on one or both.
- **Railway's free tier storage**: generated meme images and the database reset if the app redeploys or sleeps from inactivity. This is fine for review-and-post-same-day use; if you want permanent history of old memes, tell me and I'll add cloud storage (still free-tier-friendly) in a later phase.

## What's NOT built yet (next phases)
- Automatic scheduling ("post 3x a day without me clicking")
- Analytics on which memes performed well
- Multi-platform (TikTok, X, Threads)
- The "learning engine" that improves caption style over time

Tell me once Parts A and B are working and we'll move to whichever of these matters most to you.
