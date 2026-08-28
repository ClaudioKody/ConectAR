"""
MODULO: Composición del panel principal (agrega datos de todos los dominios
para armar la pantalla de inicio de docente y de alumno).
"""
import sqlite3

from flask import Blueprint, render_template

import config
from extensions import query
from security import current_user, login_required
from utils import (
    build_month_calendar,
    find_glossary_terms,
    message_thread,
    progress_summary,
    unread_from,
    unread_message_count,
    upcoming_events,
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user["role"] == "teacher":
        return _teacher_dashboard(user)
    return _student_dashboard(user)


def _teacher_dashboard(user):
    students = query("SELECT * FROM accounts WHERE role = 'student' ORDER BY full_name")
    tasks = query(
        "SELECT t.*, a.full_name AS student_name FROM tasks t LEFT JOIN accounts a ON a.id = t.student_id WHERE t.teacher_id = ? ORDER BY t.created_at DESC",
        (user["id"],),
    )
    announcements = query("SELECT * FROM announcements WHERE teacher_id = ? ORDER BY created_at DESC", (user["id"],))
    subjects = [s for s in user["subjects"].split(",") if s]
    family_contacts = query(
        "SELECT fc.*, a.full_name AS student_name FROM family_contacts fc JOIN accounts a ON a.id = fc.student_id ORDER BY fc.created_at DESC"
    )
    unread_total = unread_message_count(user["id"])
    student_threads = [
        {
            "student": student,
            "messages": message_thread(user["id"], student["id"]),
            "unread": unread_from(student["id"], user["id"]),
        }
        for student in students
    ]
    student_notices = query(
        "SELECT sn.*, a.full_name AS student_name FROM student_notices sn JOIN accounts a ON a.id = sn.student_id WHERE (sn.teacher_id = ? OR sn.teacher_id IS NULL) AND sn.is_read = 0 ORDER BY sn.created_at DESC",
        (user["id"],),
    )
    help_requests = query(
        "SELECT hr.*, a.full_name AS student_name, t.title AS task_title FROM help_requests hr JOIN accounts a ON a.id = hr.student_id LEFT JOIN tasks t ON hr.task_id = t.id WHERE hr.teacher_id = ? ORDER BY (hr.status = 'pendiente') DESC, hr.created_at DESC",
        (user["id"],),
    )
    pending_help_count = sum(1 for h in help_requests if h["status"] == "pendiente")
    student_progress = []
    for student in students:
        student_tasks = query(
            "SELECT * FROM tasks WHERE teacher_id = ? AND (student_id IS NULL OR student_id = ?)",
            (user["id"], student["id"]),
        )
        student_progress.append({"student": student, "progress": progress_summary(student_tasks)})
    upcoming = upcoming_events(tasks)
    recent_submissions = query(
        "SELECT sub.*, t.title AS task_title, t.subject AS subject, a.full_name AS student_name FROM submissions sub JOIN tasks t ON t.id = sub.task_id JOIN accounts a ON a.id = sub.student_id WHERE t.teacher_id = ? ORDER BY sub.submitted_at DESC LIMIT 8",
        (user["id"],),
    )
    calendar = build_month_calendar(tasks)
    # Perfiles de aprendizaje ya cargados, para mostrar un indicador junto a cada alumno
    profile_rows = query("SELECT student_id FROM learning_profiles")
    students_with_profile = {row["student_id"] for row in profile_rows}
    return render_template(
        "dashboard.html",
        user=user,
        students=students,
        tasks=tasks,
        announcements=announcements,
        subjects=subjects,
        family_contacts=family_contacts,
        student_threads=student_threads,
        unread_total=unread_total,
        student_notices=student_notices,
        help_requests=help_requests,
        pending_help_count=pending_help_count,
        student_progress=student_progress,
        upcoming=upcoming,
        recent_submissions=recent_submissions,
        calendar=calendar,
        students_with_profile=students_with_profile,
        mode="teacher",
    )


def _student_dashboard(user):
    tasks = query(
        "SELECT t.*, a.full_name AS teacher_name FROM tasks t JOIN accounts a ON a.id = t.teacher_id WHERE t.student_id IS NULL OR t.student_id = ? ORDER BY t.due_at IS NULL, t.due_at",
        (user["id"],),
    )
    teachers = query("SELECT * FROM accounts WHERE role = 'teacher' ORDER BY full_name")
    announcements = query(
        "SELECT an.*, a.full_name AS teacher_name FROM announcements an JOIN accounts a ON a.id = an.teacher_id WHERE an.student_id IS NULL OR an.student_id = ? ORDER BY an.created_at DESC",
        (user["id"],),
    )
    family_contacts = query("SELECT * FROM family_contacts WHERE student_id = ? ORDER BY created_at DESC", (user["id"],))
    unread_total = unread_message_count(user["id"])
    teacher_threads = [
        {
            "teacher": teacher,
            "messages": message_thread(user["id"], teacher["id"]),
            "unread": unread_from(teacher["id"], user["id"]),
        }
        for teacher in teachers
    ]
    subjects_map: dict[str, list[sqlite3.Row]] = {}
    for task in tasks:
        subjects_map.setdefault(task["subject"], []).append(task)
    my_classes = [{"subject": subject, "tasks": subject_tasks} for subject, subject_tasks in subjects_map.items()]
    pending_tasks = [t for t in tasks if not t["completed"]]
    combined_text = " ".join(f"{t['title']} {t['description']} {t['steps']}" for t in tasks)
    glossary_terms = find_glossary_terms(combined_text)
    progress = progress_summary(tasks)
    calendar = build_month_calendar(tasks)
    my_help_requests = query(
        "SELECT hr.*, a.full_name AS teacher_name, t.title AS task_title FROM help_requests hr JOIN accounts a ON a.id = hr.teacher_id LEFT JOIN tasks t ON hr.task_id = t.id WHERE hr.student_id = ? ORDER BY hr.created_at DESC LIMIT 6",
        (user["id"],),
    )
    return render_template(
        "dashboard.html",
        user=user,
        tasks=tasks,
        teachers=teachers,
        announcements=announcements,
        family_contacts=family_contacts,
        teacher_threads=teacher_threads,
        unread_total=unread_total,
        my_classes=my_classes,
        pending_tasks=pending_tasks,
        glossary_terms=glossary_terms,
        progress=progress,
        calendar=calendar,
        help_options=config.HELP_OPTIONS,
        my_help_requests=my_help_requests,
        mode="student",
    )
