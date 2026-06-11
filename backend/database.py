import sqlite3
import os
import json
import secrets
import hashlib
from datetime import datetime, date
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ttgen.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','teacher','student')),
        full_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        color TEXT DEFAULT '#3b82f6',
        periods_per_week INTEGER NOT NULL DEFAULT 5,
        needs_lab INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('classroom','lab','hall')),
        capacity INTEGER DEFAULT 40,
        equipment TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        employee_id TEXT UNIQUE,
        specialization TEXT DEFAULT '',
        max_periods_per_day INTEGER DEFAULT 6,
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS teacher_subjects (
        teacher_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        PRIMARY KEY (teacher_id, subject_id),
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS teacher_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 5),
        period_number INTEGER NOT NULL CHECK(period_number BETWEEN 0 AND 9),
        is_available INTEGER DEFAULT 1,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
        UNIQUE(teacher_id, day_of_week, period_number)
    );

    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        grade TEXT NOT NULL,
        section TEXT NOT NULL,
        strength INTEGER DEFAULT 40,
        room_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS class_subjects (
        class_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        periods_per_week INTEGER DEFAULT 5,
        PRIMARY KEY (class_id, subject_id),
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY CHECK(id = 1),
        school_name TEXT DEFAULT 'My School',
        periods_per_day INTEGER DEFAULT 8,
        period_duration INTEGER DEFAULT 45,
        start_time TEXT DEFAULT '08:00',
        working_days TEXT DEFAULT '0,1,2,3,4,5',
        lunch_period INTEGER DEFAULT 4,
        lunch_duration INTEGER DEFAULT 30
    );

    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        room_id INTEGER,
        day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 5),
        period_number INTEGER NOT NULL CHECK(period_number BETWEEN 0 AND 9),
        is_break INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL,
        UNIQUE(class_id, day_of_week, period_number),
        UNIQUE(teacher_id, day_of_week, period_number)
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS class_time_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER NOT NULL,
        period_number INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        is_break INTEGER DEFAULT 0,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        UNIQUE(class_id, period_number)
    );

    CREATE TABLE IF NOT EXISTS substitutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_teacher_id INTEGER NOT NULL,
        substitute_teacher_id INTEGER,
        class_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        period_number INTEGER NOT NULL,
        date TEXT,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (original_teacher_id) REFERENCES teachers(id),
        FOREIGN KEY (substitute_teacher_id) REFERENCES teachers(id),
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM config")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO config (id) VALUES (1)")
    
    conn.commit()
    conn.close()

def migrate_db():
    """Add new tables/columns for existing databases."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            period_number INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_break INTEGER DEFAULT 0,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
            UNIQUE(class_id, period_number)
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"

def verify_password(password, stored):
    salt, h = stored.split(':')
    return hashlib.sha256((salt + password).encode()).hexdigest() == h

def create_session(user_id):
    conn = get_db()
    token = secrets.token_hex(32)
    conn.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, datetime('now', '+7 days'))",
        (user_id, token)
    )
    conn.commit()
    conn.close()
    return token

def get_user_from_token(token):
    if not token:
        return None
    conn = get_db()
    row = conn.execute(
        "SELECT u.* FROM users u JOIN sessions s ON u.id = s.user_id WHERE s.token = ? AND s.expires_at > datetime('now')",
        (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

if __name__ == '__main__':
    init_db()
    print("Database initialized!")
