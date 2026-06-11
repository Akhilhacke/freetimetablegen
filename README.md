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
- **Database:** SQLite
- **Icons:** Font Awesome

## Quick Start

```bash
pip install -r requirements.txt
python backend/app.py
```

Open http://localhost:8000

## Project Structure

```
backend/
  app.py              - FastAPI application & routes
  database.py         - SQLite schema & connection
  timetable_engine.py - Timetable generation & swap logic
templates/            - Jinja2 HTML templates
static/               - CSS, JS, fonts
```
