# HR AI Platform Setup Guide

This repository contains the backend services for the HR AI platform built with FastAPI, SQLAlchemy, and LangGraph.

## Architecture Overview

```mermaid
graph TD
  A[User / Employee] -->|Web UI / API| B[React Frontend]
  B -->|REST / Auth| C[FastAPI Backend]
  C --> D[PostgreSQL Database]
  C --> E[AI Orchestrator / LangGraph]
  C --> F[SMTP Email Notifications]
  E -->|requests| G[HR Agents / Policy Agent / Payroll Agent]
  D -->|user, ticket, message data| C
  F -->|notifications| H[HR / Authority Email]
```

## Prerequisites

- Python 3.11+ or compatible Python 3 environment
- Node.js 18+ and npm
- PostgreSQL running locally or accessible remotely
- Git

## Backend Setup

1. Create and activate a virtual environment:

```bash
cd /home/vedp/my-project/IntentBot/hr-ai-platform
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

Copy the `.env` example or update the existing `.env` file:

```bash
cp .env .env.local
```

Update the values for:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- `SMTP_TO_HR` (notification recipient)

4. Start the backend server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be available at `http://localhost:8000`.

## Frontend Setup

1. Install frontend dependencies:

```bash
cd /home/vedp/my-project/IntentBot/frontend
npm install
```

2. Start the Vite development server:

```bash
npm run dev
```

Open the app in your browser at `http://localhost:5173`.

## Full Local Startup

The project includes a startup helper script at the repository root:

```bash
cd /home/vedp/my-project/IntentBot
./start.sh
```

This script launches the backend on port `8000` and the frontend on port `5173`.

## Database Notes

The backend expects a PostgreSQL database configured in `DATABASE_URL`:

```env
DATABASE_URL=postgresql://postgres:password@localhost/hr-bot
```

Make sure the database exists and the user has the correct permissions.

### Default Admin Seed

When the backend starts with a fresh database, it automatically creates a default admin account if one does not already exist.

- Username: `ceo@1`
- Password: `admin123`
- Role: `higher_authority`

> Change these credentials in `.env` before using the application in production.

## Important Notes

- Do not commit sensitive data such as `.env` files, secrets, or passwords.
- The repository `.gitignore` already excludes local virtual environments, node_modules, build artifacts, editor caches, and temporary files.
- In production, rotate `JWT_SECRET_KEY` and SMTP credentials before deployment.

## Useful Commands

- Backend linting / tests: add your own testing and linting commands as needed
- Frontend build: `npm run build`
- Backend reload: `uvicorn app.main:app --reload`

## Project Structure

- `hr-ai-platform/` – FastAPI backend, ORM models, API routes, AI orchestration
- `frontend/` – React + TypeScript UI, Vite application
- `start.sh` – helper script to run backend and frontend together
