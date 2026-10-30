# FoodWise - Publishing / Deployment Guide

FoodWise is a **Python (Flask) application**, so it cannot run on GitHub Pages
directly - it needs a Python host. This guide covers the three easiest free
options plus the static showcase site. Pick **Option A (Render)** if you just
want a shareable live URL in ~5 minutes.

---

## Option A - Render (recommended, free, no credit card)

Render deploys straight from your GitHub repository.

1. Go to <https://render.com> and choose **Sign up with GitHub**.
2. In the dashboard click **New + → Web Service**.
3. Pick your repository **abi-techhub/food-wise** (grant access if asked).
4. Fill in the form:
   - **Name**: `food-wise` (the URL becomes `https://food-wise-xxxx.onrender.com`)
   - **Language / Runtime**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4`
     (a `Procfile` with this command is already in the repo - Render can auto-detect it)
   - **Instance type**: Free
5. Under **Environment**, add:
   - `SECRET_KEY` = any long random string (required in production)
   - `SEED_DEMO` = `1` (optional but recommended: auto-creates the viva demo
     account `demo_user` / `Demo@123` with 11 items and 10 waste records on
     first boot, so the ML panel is trained the moment you open the site)
6. Click **Create Web Service** and wait for the build (2-4 minutes).
7. Your app is now **published** at your Render URL - share it in the viva.

**Free-tier notes**
- The service sleeps after ~15 minutes of inactivity; the first visitor waits
  ~30-60 seconds while it wakes up.
- SQLite lives on an ephemeral disk: data survives restarts but a **redeploy**
  starts a fresh database. That is fine for a demo; `SEED_DEMO=1` re-seeds it
  automatically.

## Option B - PythonAnywhere (classic student choice)

1. Create a free account at <https://www.pythonanywhere.com> (Beginner plan).
2. Open a **Bash console** and clone + install:
   ```bash
   git clone https://github.com/abi-techhub/food-wise.git
   cd food-wise
   mkvirtualenv foodwise --python=python3.12
   pip install -r requirements.txt
   python seed_demo.py     # demo data
   ```
3. Go to **Web → Add a new web app → Manual configuration → Python 3.10+**.
4. In the **Code** section:
   - Set **Source directory** to `/home/<your-username>/food-wise`
   - Edit the **WSGI configuration file** and replace the ` flask_app` line with:
     ```python
     import sys
     sys.path.insert(0, "/home/<your-username>/food-wise")
     from app import app as application
     ```
   - Set the **Virtualenv** to `~/.virtualenvs/foodwise`.
5. Click **Reload** - your site is live at `https://<your-username>.pythonanywhere.com`.
   (Set `SECRET_KEY` by adding it in the Web tab → Environment variables, or in code.)

## Option C - Railway

1. <https://railway.app> → **Sign in with GitHub** → **New Project → Deploy from GitHub repo**.
2. Railway detects the `Procfile` automatically; add the `SECRET_KEY`
   environment variable before the first deploy.
3. **Settings → Networking → Generate Domain** to get the public URL.

---

## GitHub Pages - static showcase site (no Python, screenshots only)

The `site/` folder is a ready-made public showcase (features, screenshots,
how-to-run). GitHub Pages can serve it in 3 clicks:

1. Open the repo on GitHub → **Settings → Pages**.
2. Under **Build and deployment**: Source = **Deploy from a branch**,
   Branch = **main**, Folder = **/site** → **Save**.
3. After ~1 minute the site is published at:
   `https://abi-techhub.github.io/food-wise/`

Remember: this only publishes the *showcase*. The live app itself needs
Option A, B or C above.

---

## Production checklist

| Item | Value / note |
| --- | --- |
| Start command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4` (in `Procfile`) |
| `SECRET_KEY` | Set a strong random value in the host's environment variables |
| `SEED_DEMO=1` | Optional - auto-seeds the demo account on first boot |
| Database | SQLite file in `database/`; ephemeral on free hosts - redeploys reset it |
| Debug mode | Never used under gunicorn (`app.run(debug=True)` only affects `python app.py` locally) |
| Scheduler | Runs inside the single web worker (12-hour expiry check) - fine for demo scale |
