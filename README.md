# PulseHR AI

An AI-native HR operations platform that helps employees raise concerns conversationally, routes requests to specialized agents, creates actionable records for HR teams, and gives administrators a structured workspace to manage tickets, policies, users, reports, and internal communication.

## Overview

PulseHR AI combines a modern React frontend with a FastAPI + LangGraph backend to support real HR workflows:

- employees can chat naturally about complaints, leave requests, payroll questions, and policy queries
- the backend classifies intent and routes each message to a specialized agent
- multi-turn complaint handling gathers missing details before escalation
- HR and higher-authority users get dashboards, ticket operations, analytics, conversation review, policy management, and messaging tools
- the system persists operational data in PostgreSQL and supports email-based escalation flows

This repository contains:

- `frontend/` — React + TypeScript frontend built with Vite
- `hr-ai-platform/` — FastAPI backend, LangGraph orchestration, SQLAlchemy models, and APIs

## Why This Project Exists

Traditional HR tools are usually form-heavy, fragmented, and hard to use in sensitive moments. PulseHR AI is designed to make HR support feel more conversational for employees while still producing structured, auditable workflows for HR operators.

The product is built around a simple idea:

- **users should be able to describe a problem in plain language**
- **the platform should understand intent, gather the right context, and take the next best operational step**
- **HR teams should receive organized data, not unstructured chat noise**

## Core Capabilities

### Employee Experience

- conversational chat interface for HR support
- complaint reporting with multi-turn follow-up questions
- leave balance and leave request assistance
- payroll query assistance
- policy question answering grounded in stored policy data
- ticket tracking for submitted issues
- post-resolution feedback collection
- dissatisfaction escalation when a low review automatically re-opens the ticket and alerts higher authority

### HR / Admin Experience

- ticket dashboard with severity, SLA, and status visibility
- detailed ticket workflows with comments and assignment
- user management for employees, HR admins, and senior authority
- conversation viewer for historical AI-user chats
- reporting dashboard with ticket, conversation, and agent analytics
- policy CRUD and seeding tools
- internal messaging between HR and higher authority
- agent activation / deactivation controls
- automatic re-escalation of poorly reviewed tickets to senior authority

## Product Surfaces

### Employee-facing

- login
- AI support chat
- my tickets

### HR-facing

- dashboard
- tickets list and ticket detail
- conversations viewer
- reports
- policy management
- users
- messages

### Higher-authority

- everything HR can access
- agent management
- broader user oversight

## Tech Stack

### Frontend

- React 19
- TypeScript
- Vite
- React Router
- Axios
- Tailwind CSS v4
- Recharts

### Backend

- FastAPI
- Python 3.11+
- LangGraph
- LangChain
- SQLAlchemy
- Pydantic / pydantic-settings
- psycopg2
- JWT authentication

### Infrastructure

- PostgreSQL
- Render for hosting
- SMTP for email notifications

### AI / Orchestration

- LLM-based intent routing
- specialized agents for complaint, leave, payroll, and policy workflows
- structured-output prompting
- stateful multi-turn orchestration through LangGraph

## Architecture

```mermaid
graph TD
  A[Employee / HR User] -->|Web App| B[React Frontend]
  B -->|REST API + JWT| C[FastAPI Backend]
  C --> D[LangGraph Orchestrator]
  C --> E[PostgreSQL]
  C --> F[SMTP Notifications]

  D --> G[Intent Router]
  G --> H[Complaint Agent]
  G --> I[Leave Agent]
  G --> J[Payroll Agent]
  G --> K[Policy Agent]
  G --> L[Default Agent]

  H --> E
  I --> E
  J --> E
  K --> E
  L --> E
```

## Agent Flow

### High-Level Routing

```mermaid
flowchart TD
    A[User sends message] --> B[POST /api/chat]
    B --> C[Load recent conversation context]
    C --> D[Intent classifier]

    D -->|employee_complaint| E[Complaint Agent]
    D -->|leave_request| F[Leave Agent]
    D -->|payroll_query| G[Payroll Agent]
    D -->|policy_question| H[Policy Agent]
    D -->|general_query| I[Default Agent]

    E --> J[Persist response and ticket updates]
    F --> J
    G --> J
    H --> J
    I --> J
    J --> K[Return structured chat response]
```

### Complaint Agent Flow

The complaint agent is the most operationally rich part of the system. It is designed to behave more like a trained HR intake assistant than a generic chatbot.

```mermaid
flowchart TD
    START((Start)) --> CL[Classify complaint type, emotion, severity]
    CL --> SC[Safety check]
    SC --> LH[Load complaint history + prior severity]
    LH --> PC[Policy check]
    PC --> CC{Information complete?}

    CC -->|No| FU[Ask one targeted follow-up]
    CC -->|Confirming| CF[Ask final confirmation]
    CC -->|Yes| GS[Generate professional summary]

    FU --> SM[Save memory]
    CF --> SM
    GS --> ES[Escalate / create ticket]
    ES --> ER[Enrich user response]
    ER --> SM
    SM --> END((End))
```

### What the Complaint Agent Collects

- what happened
- when it happened
- who was involved
- whether witnesses or evidence exist
- how the issue affected the employee

### Escalation Behavior

- `critical` → notify HR and authority, create ticket
- `high` → notify HR, create ticket
- `medium` → create ticket
- `low` → log / track appropriately

### Post-Resolution Feedback Escalation

PulseHR AI also closes the loop after ticket resolution:

- employees can submit feedback for resolved or closed tickets
- when a review is poor (`rating <= 2`), the system automatically re-opens the ticket
- the platform sends an escalation email to higher authority for manual review
- this ensures unresolved dissatisfaction is surfaced instead of being hidden behind a closed status

For a fuller reference, see [hr-ai-platform/AGENT_FLOW.md](/home/vedp/my-project/IntentBot/hr-ai-platform/AGENT_FLOW.md:1).

## Repository Structure

```text
.
├── frontend/                  # React + TypeScript client
│   ├── src/
│   │   ├── api/               # Axios client + API service wrappers
│   │   ├── components/        # Shared UI, layout, badges, skeletons
│   │   ├── contexts/          # Auth/session context
│   │   └── pages/             # Employee, HR, and admin screens
├── hr-ai-platform/            # FastAPI backend
│   ├── agents/                # Agent implementations and prompts
│   ├── api/                   # REST routes and schemas
│   ├── app/                   # App bootstrap, config, auth, middleware
│   ├── db/                    # SQLAlchemy models and DB connection
│   ├── memory/                # Memory store abstractions
│   ├── orchestrator/          # Shared orchestration state
│   ├── escalation/            # SLA / escalation logic
│   └── utils/                 # Logging and support utilities
└── start.sh                   # Local helper script
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm
- PostgreSQL

### Backend Setup

```bash
cd hr-ai-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### Run Both

```bash
./start.sh
```

## Configuration

### Backend Environment Variables

Important backend configuration values include:

- `DATABASE_URL`
- `NVIDIA_API_KEY`
- `MODEL_NAME`
- `JWT_SECRET_KEY`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_TO_HR`
- `SMTP_TO_AUTHORITY`
- `ADMIN_USERNAME`
- `ADMIN_EMAIL`
- `ADMIN_FULL_NAME`
- `ADMIN_PASSWORD`
- `ADMIN_ROLE`

### Frontend Environment Variables

The frontend can call the backend directly using:

```env
VITE_API_BASE_URL=https://your-backend-service.onrender.com
```

Example local file:

- [frontend/.env.example](/home/vedp/my-project/IntentBot/frontend/.env.example:1)

## Default Admin Seeding

On first startup against a fresh database, the backend can create an initial admin account using the configured admin environment variables.

Important behavior:

- seeding happens only when an active admin does not already exist
- changing the default values later does not overwrite an existing admin password
- production deployments should always replace development defaults

## API Surface

The backend exposes route groups such as:

- `/api/auth`
- `/api/chat`
- `/api/users`
- `/api/tickets`
- `/api/conversations`
- `/api/reports`
- `/api/notifications`
- `/api/agents`
- `/api/my`
- `/api/feedback`
- `/api/policies`
- `/api/messages`

Health endpoint:

- `/health`

## Deployment On Render

PulseHR AI fits cleanly into a 3-service Render setup:

1. Render Postgres
2. Render Web Service for the backend
3. Render Static Site for the frontend

### 1. Create the Database

Create a Render Postgres instance first and use its internal connection string for the backend `DATABASE_URL`.

Example:

```env
DATABASE_URL=postgresql://user:password@internal-host:5432/intentbot
```

### 2. Deploy the Backend

Create a Render Web Service with these settings:

| Setting | Value |
| --- | --- |
| Service Type | `Web Service` |
| Runtime | `Python 3` |
| Root Directory | `hr-ai-platform` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

Recommended backend env vars:

- `PYTHON_VERSION=3.11.11`
- `DATABASE_URL=<render-internal-postgres-url>`
- `NVIDIA_API_KEY=<your-key>`
- `MODEL_NAME=openai/gpt-oss-120b`
- `JWT_SECRET_KEY=<strong-secret>`
- SMTP and admin seed variables as needed

### 3. Deploy the Frontend

Create a Render Static Site with these settings:

| Setting | Value |
| --- | --- |
| Service Type | `Static Site` |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |

Set this env var in the frontend service:

```env
VITE_API_BASE_URL=https://YOUR-BACKEND-SERVICE.onrender.com
```
