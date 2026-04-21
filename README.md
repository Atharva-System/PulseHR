# HR AI Platform

This repository contains:

- `frontend/` — React + TypeScript frontend built with Vite
- `hr-ai-platform/` — FastAPI + SQLAlchemy + LangGraph backend

## Deploy On Render

This repo works well on Render with three pieces:

1. A Render Postgres database
2. A Render Web Service for the FastAPI backend
3. A Render Static Site for the Vite frontend

The frontend currently calls relative paths such as `/api/auth/login`, so the Static Site must include rewrite rules that forward `/api/*` to the backend service.

### 1. Create The Postgres Database

Create a new Render Postgres instance first.

- Choose the same region as the backend web service
- Copy the database's internal connection string
- Use that internal URL as the backend `DATABASE_URL`

Example:

```env
DATABASE_URL=postgresql://user:password@internal-host:5432/intentbot
```

## 2. Deploy The Backend

Create a new Render Web Service with these settings:

| Setting | Value |
| --- | --- |
| Service Type | `Web Service` |
| Runtime | `Python 3` |
| Root Directory | `hr-ai-platform` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port 10000` |
| Health Check Path | `/health` |

### Backend Environment Variables

Set these in the Render dashboard for the backend service:

| Variable | Required | Notes |
| --- | --- | --- |
| `DATABASE_URL` | Yes | Use the Render Postgres internal URL |
| `NVIDIA_API_KEY` | Yes | Required by the AI backend |
| `MODEL_NAME` | Yes | Example: `openai/gpt-oss-120b` |
| `LOG_LEVEL` | Recommended | Example: `INFO` |
| `JWT_SECRET_KEY` | Yes | Use a strong production secret |
| `JWT_ALGORITHM` | Optional | Default is `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | Default is `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Optional | Default is `7` |
| `SMTP_HOST` | If email is enabled | SMTP server host |
| `SMTP_PORT` | If email is enabled | Example: `587` |
| `SMTP_USER` | If email is enabled | SMTP username |
| `SMTP_PASSWORD` | If email is enabled | SMTP password or app password |
| `SMTP_FROM` | If email is enabled | Sender email |
| `SMTP_TO_HR` | Recommended | HR notification address |
| `SMTP_TO_AUTHORITY` | Recommended | Authority notification address |
| `ADMIN_USERNAME` | Optional | Seed admin username |
| `ADMIN_EMAIL` | Optional | Seed admin email |
| `ADMIN_FULL_NAME` | Optional | Seed admin full name |
| `ADMIN_PASSWORD` | Recommended | Seed admin password for a fresh DB |
| `ADMIN_ROLE` | Optional | Default is `higher_authority` |

### Backend Notes

- The backend already exposes `GET /health`
- On first boot with a fresh database, the app auto-creates the seed admin user if the admin env vars are set
- Keep secrets in Render environment variables, not in git-tracked `.env` files

## 3. Deploy The Frontend

Create a new Render Static Site with these settings:

| Setting | Value |
| --- | --- |
| Service Type | `Static Site` |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |

No frontend environment variables are required with the current codebase if you add the rewrite rules below.

### Frontend Rewrite Rules

In the frontend Static Site settings, add these rules in this order:

| Source | Destination | Action |
| --- | --- | --- |
| `/api/*` | `https://YOUR-BACKEND-SERVICE.onrender.com/api/*` | `Rewrite` |
| `/health` | `https://YOUR-BACKEND-SERVICE.onrender.com/health` | `Rewrite` |
| `/*` | `/index.html` | `Rewrite` |

Why these rules matter:

- `/api/*` forwards API requests from the frontend to the FastAPI backend
- `/health` matches the local Vite proxy behavior already used in development
- `/* -> /index.html` makes React Router work on refresh and direct deep links

## 4. Validate The Deployment

After both services are live:

1. Open the backend health URL:

```text
https://YOUR-BACKEND-SERVICE.onrender.com/health
```

2. Open the frontend site and try logging in
3. Confirm browser requests to `/api/...` succeed
4. Confirm the backend can connect to Postgres and create tables on startup

## 5. Recommended Production Cleanup

- Rotate any secrets that were ever stored in local `.env` files
- Replace the default admin password before real users sign in
- If you later restrict CORS, update `hr-ai-platform/app/middleware.py` to allow only your frontend domain instead of `*`
- Add custom domains after the `onrender.com` deployments are working

## Local Development

### Backend

```bash
cd hr-ai-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` and `/health` to `http://localhost:8000`.

### Start Both Together

```bash
./start.sh
```

## Project Structure

- `frontend/` — Vite frontend
- `hr-ai-platform/` — FastAPI backend
- `start.sh` — helper script for local development

## Render References

- Render Web Services: https://render.com/docs/web-services
- Render Static Sites: https://render.com/docs/static-sites
- Render Redirects and Rewrites: https://render.com/docs/redirects-rewrites
- Render Environment Variables: https://render.com/docs/configure-environment-variables
- Render Postgres: https://render.com/docs/databases
