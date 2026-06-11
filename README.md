# FreeTimetableGen

AI-powered timetable generator for educational institutions. Built with FastAPI + Alpine.js.

## Features

- **Automated generation** — constraint-based scheduling with teacher availability, room types, and subject period limits
- **Drag-and-drop editor** — swap periods interactively with real-time conflict detection
- **Entity management** — subjects, teachers, classes, rooms, teacher-subject assignments
- **Export** — Excel, CSV, PDF (via `fpdf2`), and Print
- **Substitutions** — manage substitute teachers for absent staff
- **Role-based access** — Admin, Teacher, Student
- **Light theme** — clean UI with indigo accent

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** Jinja2 templates + Alpine.js + custom CSS
- **Database:** SQLite (local development) / PostgreSQL (production via `psycopg2`)
- **Icons:** Font Awesome

## Quick Start (Local)

```bash
pip install -r requirements.txt
python backend/app.py
```

Open http://localhost:8000

## Deploy on Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Akhilhacke/freetimetablegen)

### Prerequisites

Get a free PostgreSQL database from [Neon](https://neon.tech), [Supabase](https://supabase.com), or [Aiven](https://aiven.io). Copy the connection string (starts with `postgresql://...`).

### Steps

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) and import the repository
3. Add **environment variable** in Vercel dashboard (Settings → Environment Variables):
   - `DATABASE_URL` — your PostgreSQL connection string
4. Click **Deploy**

> **Note:** Without `DATABASE_URL`, the app falls back to SQLite which is ephemeral on serverless — data will not persist across cold starts. Always set up PostgreSQL for production.

## Project Structure

```
backend/
  app.py              - FastAPI application & routes
  database.py         - Dual-dialect schema (SQLite + PostgreSQL)
  timetable_engine.py - Generation, swap, and conflict detection
templates/            - Jinja2 HTML templates (landing, dashboard, etc.)
static/               - CSS, JS, fonts
api/index.py          - Vercel serverless entry point
vercel.json           - Vercel build & route configuration
```

## Environment Variables

| Variable       | Required | Description                              |
|---------------|----------|------------------------------------------|
| `DATABASE_URL` | No*      | PostgreSQL connection string for Vercel  |

\* Required for persistent storage on Vercel. Falls back to SQLite otherwise.
