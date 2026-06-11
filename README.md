# FreeTimetableGen

AI-powered timetable generator for educational institutions.

## Features

- Automated timetable generation with constraint-based scheduling
- Drag-and-drop timetable editor with conflict detection
- Subject, teacher, class, and room management
- Export to Excel, CSV, and PDF
- Teacher availability and substitution management
- Role-based access (Admin, Teacher, Student)

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** Jinja2 templates + Alpine.js + custom CSS
- **Database:** SQLite (local) / PostgreSQL (production)
- **Icons:** Font Awesome

## Quick Start (Local)

```bash
pip install -r requirements.txt
python backend/app.py
```

Open http://localhost:8000

## Deploy on Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Akhilhacke/freetimetablegen)

### 1. Set up PostgreSQL

Get a free PostgreSQL database from [Neon](https://neon.tech) or [Supabase](https://supabase.com). Copy the connection string.

### 2. Deploy

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) and import the repository
3. Add environment variable:
   - `DATABASE_URL` — your PostgreSQL connection string
4. Click **Deploy**

The app auto-creates all tables on first run.

## Project Structure

```
backend/
  app.py              - FastAPI application & routes
  database.py         - Database schema & connection (SQLite + PostgreSQL)
  timetable_engine.py - Timetable generation & swap logic
templates/            - Jinja2 HTML templates
static/               - CSS, JS, fonts
api/index.py          - Vercel serverless entry point
vercel.json           - Vercel configuration
```
