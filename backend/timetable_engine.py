import random
from collections import defaultdict
from database import get_db

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

class TimetableGenerator:
    def __init__(self):
        self.db = get_db()
        self.config = dict(self.db.execute("SELECT * FROM config WHERE id=1").fetchone())
        self.working_days = [int(d) for d in self.config['working_days'].split(',')]
        self.schedule = {}
        self.teacher_schedule = defaultdict(set)
        self.class_schedule = defaultdict(set)
        self.room_schedule = defaultdict(set)
        self.errors = []

    def load_data(self):
        self.teachers = [dict(r) for r in self.db.execute("SELECT * FROM teachers").fetchall()]
        self.classes = [dict(r) for r in self.db.execute("SELECT * FROM classes").fetchall()]
        self.subjects = [dict(r) for r in self.db.execute("SELECT * FROM subjects").fetchall()]
        self.rooms = [dict(r) for r in self.db.execute("SELECT * FROM rooms").fetchall()]
        
        self.teacher_subjects = defaultdict(list)
        for row in self.db.execute("SELECT * FROM teacher_subjects").fetchall():
            self.teacher_subjects[row['teacher_id']].append(row['subject_id'])
        
        self.class_subjects = {}
        for row in self.db.execute("SELECT * FROM class_subjects").fetchall():
            self.class_subjects[(row['class_id'], row['subject_id'])] = row['periods_per_week']
        
        self.teacher_availability = defaultdict(set)
        for row in self.db.execute("SELECT * FROM teacher_availability WHERE is_available=1").fetchall():
            self.teacher_availability[row['teacher_id']].add((row['day_of_week'], row['period_number']))
        
        self.teacher_max_periods = {}
        for t in self.teachers:
            self.teacher_max_periods[t['id']] = t.get('max_periods_per_day', 6)

        # Per-class time slots
        self.class_time_slots = defaultdict(list)
        rows = self.db.execute(
            "SELECT * FROM class_time_slots ORDER BY class_id, period_number"
        ).fetchall()
        if rows:
            for r in rows:
                self.class_time_slots[r['class_id']].append(dict(r))
        else:
            # Fallback: generate default slots from config for each class
            periods = self.config['periods_per_day']
            start = self.config['start_time']
            duration = self.config['period_duration']
            lunch = self.config['lunch_period']
            lunch_dur = self.config['lunch_duration']
            h, m = map(int, start.split(':'))
            base = h * 60 + m
            gap = 5
            for cls in self.classes:
                slots = []
                for p in range(periods):
                    s_min = base + p * (duration + gap)
                    e_min = s_min + (lunch_dur if p == lunch else duration)
                    sh, sm = divmod(s_min, 60)
                    eh, em = divmod(e_min, 60)
                    slots.append({
                        'period_number': p,
                        'start_time': f"{sh:02d}:{sm:02d}",
                        'end_time': f"{eh:02d}:{em:02d}",
                        'is_break': 1 if p == lunch else 0
                    })
                self.class_time_slots[cls['id']] = slots

    def get_available_teachers(self, subject_id, day, period):
        available = []
        for teacher in self.teachers:
            tid = teacher['id']
            if subject_id not in self.teacher_subjects.get(tid, []):
                continue
            if day >= 0 and period >= 0:
                if (day, period) in self.teacher_schedule[tid]:
                    continue
                avail = self.teacher_availability.get(tid)
                if avail and (day, period) not in avail:
                    continue
            if day >= 0 and tid in self.teacher_max_periods:
                count = sum(1 for d, p in self.teacher_schedule[tid] if d == day)
                if count >= self.teacher_max_periods[tid]:
                    continue
            available.append(teacher)
        return available

    def get_available_room(self, day, period, needs_lab=False):
        for room in self.rooms:
            if needs_lab and room['type'] != 'lab':
                continue
            if not needs_lab and room['type'] == 'lab':
                continue
            rid = room['id']
            if (day, period) in self.room_schedule[rid]:
                continue
            return room
        for room in self.rooms:
            rid = room['id']
            if (day, period) not in self.room_schedule[rid]:
                return room
        return None

    def can_place(self, class_id, subject_id, teacher_id, day, period):
        if (class_id, day, period) in self.class_schedule:
            return False
        if (teacher_id, day, period) in self.teacher_schedule:
            return False
        return True

    def place_slot(self, class_id, subject_id, teacher_id, room_id, day, period):
        key = (class_id, day, period)
        self.schedule[key] = {
            'class_id': class_id,
            'subject_id': subject_id,
            'teacher_id': teacher_id,
            'room_id': room_id,
            'day': day,
            'period': period
        }
        self.class_schedule[class_id].add((day, period))
        self.teacher_schedule[teacher_id].add((day, period))
        if room_id:
            self.room_schedule[room_id].add((day, period))

    def generate(self):
        self.load_data()
        self.db.execute("DELETE FROM timetable")
        self.db.commit()
        self.errors = []
        
        if not self.classes:
            self.errors.append("No classes found. Please add at least 1 class first.")
            return False
        if not self.subjects:
            self.errors.append("No subjects found. Please add at least 1 subject first.")
            return False
        if not self.teachers:
            self.errors.append("No teachers found. Please add at least 1 teacher first.")
            return False
        
        teachers_with_subjects = [t for t in self.teachers if t['id'] in self.teacher_subjects]
        if not teachers_with_subjects:
            self.errors.append("No teacher-subject assignments found. Go to Teachers, edit each teacher, and assign subjects.")
            return False
        
        classes_with_subjects = [c for c in self.classes if any((c['id'], s['id']) in self.class_subjects for s in self.subjects)]
        if not classes_with_subjects:
            self.errors.append("No class-subject assignments found. Go to Classes, edit each class, and assign subjects with periods.")
            return False

        subjects_needing_teachers = []
        for subj in self.subjects:
            teachers_for_subj = [t for t in self.teachers if subj['id'] in self.teacher_subjects.get(t['id'], [])]
            if not teachers_for_subj:
                subj_name = subj['name']
                subjects_needing_teachers.append(subj_name)
        
        if subjects_needing_teachers:
            self.errors.append(f"These subjects have NO teacher assigned: {', '.join(subjects_needing_teachers)}. Go to Teachers → Edit → Assign these subjects to a teacher.")
            return False
        
        assignments = []
        for cls in self.classes:
            for subj in self.subjects:
                key = (cls['id'], subj['id'])
                if key not in self.class_subjects:
                    continue
                periods_needed = self.class_subjects[key]
                for _ in range(periods_needed):
                    assignments.append((cls['id'], subj['id']))

        # Deduplicate: ensure no (class_id, subject_id) pair exceeds its needed count
        assignment_count = {}
        filtered = []
        for cid, sid in assignments:
            k = (cid, sid)
            max_n = self.class_subjects.get(k, 0)
            assignment_count[k] = assignment_count.get(k, 0) + 1
            if assignment_count[k] <= max_n:
                filtered.append((cid, sid))
        assignments = filtered
        
        random.shuffle(assignments)
        max_retries = 30
        
        for attempt in range(max_retries):
            self.schedule.clear()
            self.teacher_schedule.clear()
            self.class_schedule.clear()
            self.room_schedule.clear()
            success = True
            
            for class_id, subject_id in assignments:
                placed = False
                teachers = self.get_available_teachers(subject_id, -1, -1)
                random.shuffle(teachers)
                
                subj_data = self.db.execute("SELECT * FROM subjects WHERE id=?", (subject_id,)).fetchone()
                needs_lab = subj_data['needs_lab'] if subj_data else False
                
                # Use per-class time slots
                slots = self.class_time_slots.get(class_id, [])
                available_periods = [s['period_number'] for s in slots if not s['is_break']]
                if not available_periods:
                    continue
                
                for day in self.working_days:
                    if placed:
                        break
                    periods = list(available_periods)
                    random.shuffle(periods)
                    for period in periods:
                        for teacher in teachers:
                            if self.can_place(class_id, subject_id, teacher['id'], day, period):
                                room = self.get_available_room(day, period, needs_lab)
                                room_id = room['id'] if room else None
                                self.place_slot(class_id, subject_id, teacher['id'], room_id, day, period)
                                placed = True
                                break
                        if placed:
                            break
                
                if not placed:
                    success = False
                    break
            
            if success:
                self.save_to_db()
                return True
        
        total_available = {}
        for cls in self.classes:
            slots = self.class_time_slots.get(cls['id'], [])
            total_available[cls['id']] = len([s for s in slots if not s['is_break']])
        total_slots = sum(total_available.values()) * len(self.working_days)
        total_needed = len(assignments)
        self.errors.append(f"Could not generate timetable after {max_retries} attempts.")
        self.errors.append(f"Needed: {total_needed} period assignments, Available capacity: {total_slots} (across all classes and days).")
        self.errors.append("Try: reduce periods_per_week for some subjects, add more working days, or add more time slots per class.")
        return False

    def save_to_db(self):
        for key, entry in self.schedule.items():
            self.db.execute(
                """INSERT INTO timetable (class_id, subject_id, teacher_id, room_id, day_of_week, period_number)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (entry['class_id'], entry['subject_id'], entry['teacher_id'],
                 entry.get('room_id'), entry['day'], entry['period'])
            )
        self.db.commit()

    def get_timetable_for_class(self, class_id):
        rows = self.db.execute(
            """SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color,
                      te.name as teacher_name, r.name as room_name
               FROM timetable t
               JOIN subjects s ON t.subject_id = s.id
               JOIN teachers te ON t.teacher_id = te.id
               LEFT JOIN rooms r ON t.room_id = r.id
               WHERE t.class_id = ?
               ORDER BY t.day_of_week, t.period_number""",
            (class_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_timetable_for_teacher(self, teacher_id):
        rows = self.db.execute(
            """SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color,
                      c.name as class_name, r.name as room_name
               FROM timetable t
               JOIN subjects s ON t.subject_id = s.id
               JOIN classes c ON t.class_id = c.id
               LEFT JOIN rooms r ON t.room_id = r.id
               WHERE t.teacher_id = ?
               ORDER BY t.day_of_week, t.period_number""",
            (teacher_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def swap_periods(self, class_id, day1, period1, day2, period2):
        slot1 = self.db.execute(
            "SELECT * FROM timetable WHERE class_id=? AND day_of_week=? AND period_number=?",
            (class_id, day1, period1)
        ).fetchone()
        slot2 = self.db.execute(
            "SELECT * FROM timetable WHERE class_id=? AND day_of_week=? AND period_number=?",
            (class_id, day2, period2)
        ).fetchone()
        
        if not slot1 and not slot2:
            return False, "Both slots are empty"
        
        if slot1:
            teacher1 = slot1['teacher_id']
            if slot2 and slot2['teacher_id'] == teacher1:
                return False, "Same teacher in both slots"
            
            # Prevent same subject appearing twice in the same day
            if slot2:
                subject1_count = self.db.execute(
                    "SELECT COUNT(*) as cnt FROM timetable WHERE class_id=? AND day_of_week=? AND subject_id=? AND id!=?",
                    (class_id, day2, slot1['subject_id'], slot2['id'])
                ).fetchone()['cnt']
                if subject1_count > 0:
                    s = self.db.execute("SELECT name FROM subjects WHERE id=?", (slot1['subject_id'],)).fetchone()
                    return False, f"{s['name']} already exists on {DAYS[day2]}. Cannot create duplicate."
                
                subject2_count = self.db.execute(
                    "SELECT COUNT(*) as cnt FROM timetable WHERE class_id=? AND day_of_week=? AND subject_id=? AND id!=?",
                    (class_id, day1, slot2['subject_id'], slot1['id'])
                ).fetchone()['cnt']
                if subject2_count > 0:
                    s = self.db.execute("SELECT name FROM subjects WHERE id=?", (slot2['subject_id'],)).fetchone()
                    return False, f"{s['name']} already exists on {DAYS[day1]}. Cannot create duplicate."
            else:
                subject1_count = self.db.execute(
                    "SELECT COUNT(*) as cnt FROM timetable WHERE class_id=? AND day_of_week=? AND subject_id=?",
                    (class_id, day2, slot1['subject_id'])
                ).fetchone()['cnt']
                if subject1_count > 0:
                    s = self.db.execute("SELECT name FROM subjects WHERE id=?", (slot1['subject_id'],)).fetchone()
                    return False, f"{s['name']} already exists on {DAYS[day2]}. Cannot create duplicate."
            
            if slot2:
                t2 = slot2['teacher_id']
                conflict1 = self.db.execute(
                    "SELECT COUNT(*) as cnt FROM timetable WHERE teacher_id=? AND day_of_week=? AND period_number=? AND id!=?",
                    (t2, day1, period1, slot2['id'])
                ).fetchone()['cnt']
                if conflict1 > 0:
                    return False, f"Teacher conflict on {DAYS[day1]} period {period1}"
            
            teacher2 = slot2['teacher_id'] if slot2 else None
            if slot2 and slot1:
                c1 = self.db.execute(
                    "SELECT COUNT(*) as cnt FROM timetable WHERE teacher_id=? AND day_of_week=? AND period_number=? AND id!=?",
                    (slot1['teacher_id'], day2, period2, slot1['id'])
                ).fetchone()['cnt']
                if c1 > 0:
                    return False, f"Teacher conflict on {DAYS[day2]} period {period2}"
            elif not slot1 and slot2:
                subject2_count = self.db.execute(
                    "SELECT COUNT(*) as cnt FROM timetable WHERE class_id=? AND day_of_week=? AND subject_id=?",
                    (class_id, day1, slot2['subject_id'])
                ).fetchone()['cnt']
                if subject2_count > 0:
                    s = self.db.execute("SELECT name FROM subjects WHERE id=?", (slot2['subject_id'],)).fetchone()
                    return False, f"{s['name']} already exists on {DAYS[day1]}. Cannot create duplicate."
        
        self.db.execute("BEGIN")
        try:
            if slot1 and slot2:
                self.db.execute(
                    "UPDATE timetable SET day_of_week=?, period_number=? WHERE id=?",
                    (day2, period2, slot1['id'])
                )
                self.db.execute(
                    "UPDATE timetable SET day_of_week=?, period_number=? WHERE id=?",
                    (day1, period1, slot2['id'])
                )
            elif slot1:
                self.db.execute(
                    "UPDATE timetable SET day_of_week=?, period_number=? WHERE id=?",
                    (day2, period2, slot1['id'])
                )
            elif slot2:
                self.db.execute(
                    "UPDATE timetable SET day_of_week=?, period_number=? WHERE id=?",
                    (day1, period1, slot2['id'])
                )
            self.db.commit()
            return True, "Swap successful"
        except Exception as e:
            self.db.rollback()
            return False, str(e)

    def find_substitute(self, teacher_id, day, period):
        original = self.db.execute(
            "SELECT subject_id, class_id FROM timetable WHERE teacher_id=? AND day_of_week=? AND period_number=?",
            (teacher_id, day, period)
        ).fetchone()
        if not original:
            return None
        
        for teacher in self.teachers:
            if teacher['id'] == teacher_id:
                continue
            if original['subject_id'] not in self.teacher_subjects.get(teacher['id'], []):
                continue
            if (day, period) in self.teacher_schedule.get(teacher['id'], set()):
                continue
            avail = self.teacher_availability.get(teacher['id'])
            if avail and (day, period) not in avail:
                continue
            return teacher
        return None
