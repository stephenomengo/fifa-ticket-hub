# Deploying World Cup Tickets

## 1. Push to GitHub

1. Create a free account at https://github.com (if you don't have one).
2. Create a new repository (e.g. `worldcup-tickets`), public or private — don't initialize with a README (you already have one).
3. On your computer, inside the `worldcup_tickets` folder, run:

```bash
git init
git add .
git commit -m "Initial commit - World Cup ticketing site"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/worldcup-tickets.git
git push -u origin main
```

(Replace `YOUR_USERNAME` with your GitHub username. If `git` isn't installed, download it from https://git-scm.com/downloads.)

You may be asked to log in — use a GitHub Personal Access Token as the password (GitHub no longer accepts account passwords for git operations). Create one at https://github.com/settings/tokens.

## 2. Deploy to Render (free)

1. Go to https://render.com and sign up (you can sign up with GitHub).
2. Click **New +** → **Web Service**.
3. Connect your GitHub account and select the `worldcup-tickets` repo.
4. Render should auto-detect Python. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Choose the **Free** instance type.
6. Click **Create Web Service**.

After a few minutes, Render gives you a live URL like:
```
https://worldcup-tickets.onrender.com
```

That's your public link — share it with your teacher/classmates.

## Notes

- **Database resets:** The free tier uses ephemeral storage, so `worldcup.db` (and any bookings) will reset whenever the service restarts or goes idle. This is fine for demos but not for permanent data. For a school project this is usually acceptable — just mention it if asked.
- **Free tier sleep:** Free Render services "sleep" after inactivity and take ~30-60 seconds to wake up on the first request. This is normal.
- **Admin login** remains `admin` / `admin123` after deployment (the database re-seeds on first run).
- If you make code changes later, just `git add .`, `git commit -m "update"`, `git push` — Render auto-redeploys.

## Alternative: PythonAnywhere

If Render doesn't work for you, https://www.pythonanywhere.com also has a free tier for Flask apps and doesn't require gunicorn — their setup wizard handles WSGI configuration for you. Upload your files via their "Files" tab or connect to GitHub, then follow their Flask quickstart guide.
