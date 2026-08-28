"""
MODULO: Comunicación entre docente y alumno — avisos, mensajería,
pedidos de ayuda y contactos familiares.
"""
from flask import Blueprint, flash, redirect, request, url_for

import config
from extensions import execute, query
from security import current_user, login_required, role_required

communication_bp = Blueprint("communication", __name__)


@communication_bp.post("/teacher/announcements")
@role_required("teacher")
def create_announcement():
    student_id = request.form.get("student_id") or None
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if title and body:
        execute(
            "INSERT INTO announcements (teacher_id, student_id, title, body) VALUES (?, ?, ?, ?)",
            (current_user()["id"], student_id, title, body),
        )
        flash("Aviso publicado.", "success")
    return redirect(url_for("dashboard.dashboard"))


@communication_bp.post("/student/help")
@role_required("student")
def request_help():
    user = current_user()
    teacher_id = request.form.get("teacher_id")
    option_key = request.form.get("option", "")
    task_id = request.form.get("task_id") or None
    note = request.form.get("note", "").strip()
    teacher_rows = query("SELECT * FROM accounts WHERE id = ? AND role = 'teacher'", (teacher_id,))
    option = next((o for o in config.HELP_OPTIONS if o["key"] == option_key), None)
    if not teacher_rows or not option:
        flash("Elegí un profesor y el tipo de ayuda que necesitás.", "warning")
        return redirect(url_for("dashboard.dashboard"))
    teacher = teacher_rows[0]
    task_title = None
    if task_id:
        task_rows = query("SELECT title FROM tasks WHERE id = ?", (task_id,))
        task_title = task_rows[0]["title"] if task_rows else None
    execute(
        "INSERT INTO help_requests (student_id, teacher_id, task_id, option_label, note) VALUES (?, ?, ?, ?, ?)",
        (user["id"], teacher["id"], task_id, option["label"], note),
    )
    message_body = f"Pedido de ayuda: {option['label']}"
    if task_title:
        message_body += f" Tarea: {task_title}"
    if note:
        message_body += f"\nNota: {note}"
    execute(
        "INSERT INTO messages (sender_id, receiver_id, body) VALUES (?, ?, ?)",
        (user["id"], teacher["id"], message_body),
    )
    flash(f"Le avisamos a {teacher['full_name']} que necesitás ayuda.", "success")
    return redirect(url_for("dashboard.dashboard"))


@communication_bp.post("/teacher/help-requests/<int:request_id>/attend")
@role_required("teacher")
def attend_help_request(request_id: int):
    execute(
        "UPDATE help_requests SET status = 'atendido' WHERE id = ? AND teacher_id = ?",
        (request_id, current_user()["id"]),
    )
    return redirect(url_for("dashboard.dashboard"))


@communication_bp.post("/student/notices")
@role_required("student")
def create_student_notice():
    user = current_user()
    teacher_id = request.form.get("teacher_id") or None
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title or not body:
        flash("Escribí un título y un mensaje para el aviso.", "warning")
        return redirect(url_for("dashboard.dashboard"))
    execute(
        "INSERT INTO student_notices (student_id, teacher_id, title, body) VALUES (?, ?, ?, ?)",
        (user["id"], teacher_id, title, body),
    )
    flash("Aviso enviado a tu profesor/a.", "success")
    return redirect(url_for("dashboard.dashboard"))


@communication_bp.post("/teacher/notices/<int:notice_id>/dismiss")
@role_required("teacher")
def dismiss_student_notice(notice_id: int):
    execute(
        "UPDATE student_notices SET is_read = 1 WHERE id = ? AND (teacher_id = ? OR teacher_id IS NULL)",
        (notice_id, current_user()["id"]),
    )
    return redirect(url_for("dashboard.dashboard"))


@communication_bp.post("/student/family-contacts")
@role_required("student")
def create_family_contact():
    name = request.form.get("contact_name", "").strip()
    relationship = request.form.get("relationship", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    notes = request.form.get("notes", "").strip()
    if not name or (not phone and not email):
        flash("Completá el nombre y al menos un teléfono o un correo de contacto.", "warning")
    else:
        execute(
            "INSERT INTO family_contacts (student_id, contact_name, relationship, phone, email, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (current_user()["id"], name, relationship, phone, email, notes),
        )
        flash("Contacto familiar registrado. Tu profesor/a ya lo puede ver para coordinar una reunión.", "success")
    return redirect(url_for("dashboard.dashboard"))


@communication_bp.post("/messages")
@login_required
def send_message():
    receiver_id = request.form.get("receiver_id")
    body = request.form.get("body", "").strip()
    if receiver_id and body:
        execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (?, ?, ?)", (current_user()["id"], receiver_id, body))
        flash("Mensaje enviado.", "success")
    return redirect(url_for("dashboard.dashboard"))
