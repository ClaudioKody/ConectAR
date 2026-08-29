"""
MODULO: Tareas, adjuntos y entregas.

La adaptación con IA (services/ai_service.py) se aplica automáticamente al
crear una tarea SI:
  - hay un archivo adjunto (PDF/TXT) del que se pudo extraer texto, Y
  - la tarea está dirigida a un alumno puntual que tiene un perfil de
    aprendizaje cargado (routes/profile_routes.py)
Si no se cumple alguna condición, o si falla la API, se usa el flujo
original (split_into_steps sobre el texto extraído o la descripción).
"""
from pathlib import Path
from flask import Blueprint, abort, flash, redirect, request, send_from_directory, url_for, current_app

from extensions import execute, query
from security import current_user, login_required, role_required
from services.ai_service import adaptar_texto
from utils import save_upload, split_into_steps

task_bp = Blueprint("tasks", __name__)


@task_bp.post("/teacher/subjects")
@role_required("teacher")
def save_subjects():
    subjects = [s.strip() for s in request.form.get("subjects", "").split(",") if s.strip()]
    execute("UPDATE accounts SET subjects = ? WHERE id = ?", (",".join(dict.fromkeys(subjects)), current_user()["id"]))
    flash("Materias guardadas.", "success")
    return redirect(url_for("dashboard.dashboard"))


def _perfil_texto_de_alumno(student_id):
    """Devuelve la lista de necesidades activas del alumno, o [] si no tiene perfil cargado."""
    if not student_id:
        return []
    import config
    rows = query("SELECT * FROM learning_profiles WHERE student_id = ?", (student_id,))
    if not rows:
        return []
    perfil = rows[0]
    return [config.ETIQUETAS_PERFIL[campo] for campo in config.CAMPOS_PERFIL if perfil[campo]]


@task_bp.post("/teacher/tasks")
@role_required("teacher")
def create_task():
    subject = request.form.get("subject", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    manual_steps = request.form.get("steps", "").strip()
    
    student_id_raw = request.form.get("student_id", "").strip()
    student_id = int(student_id_raw) if student_id_raw.isdigit() else None

    if not subject or not title:
        flash("La materia y el título son obligatorios.", "warning")
        return redirect(url_for("dashboard.dashboard"))

    had_file = bool(request.files.get("attachment") and request.files["attachment"].filename)
    stored_name, original_name, extracted_text = save_upload("attachment")

    if had_file and stored_name is None:
        return redirect(url_for("dashboard.dashboard"))

    steps_source = manual_steps or extracted_text or description

    if not manual_steps and extracted_text:
        try:
            perfil_texto = _perfil_texto_de_alumno(student_id)
            if perfil_texto:
                steps_source = adaptar_texto(extracted_text, perfil_texto)
        except Exception:
            steps_source = extracted_text or description

    steps_value = "\n".join(split_into_steps(steps_source))
    due_at = request.form.get("due_at", "").strip() or None

    execute(
        "INSERT INTO tasks (teacher_id, student_id, subject, title, description, steps, file_path, file_name, due_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            current_user()["id"],
            student_id,
            subject,
            title,
            description,
            steps_value,
            stored_name,
            original_name,
            due_at,
        ),
    )
    flash("Tarea creada y sincronizada con el alumno.", "success")
    return redirect(url_for("dashboard.dashboard"))


@task_bp.route("/uploads/<path:stored_name>")
@login_required
def uploaded_file(stored_name: str):
    user = current_user()
    task_rows = query("SELECT * FROM tasks WHERE file_path = ?", (stored_name,))
    if task_rows:
        task = task_rows[0]
        allowed = (user["role"] == "teacher" and task["teacher_id"] == user["id"]) or (
            user["role"] == "student" and (task["student_id"] is None or task["student_id"] == user["id"])
        )
        if not allowed:
            abort(403)
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], stored_name, download_name=task["file_name"])

    submission_rows = query(
        "SELECT s.*, t.teacher_id AS teacher_id FROM submissions s JOIN tasks t ON t.id = s.task_id WHERE s.file_path = ?",
        (stored_name,),
    )
    if submission_rows:
        submission = submission_rows[0]
        allowed = (user["role"] == "teacher" and submission["teacher_id"] == user["id"]) or (
            user["role"] == "student" and submission["student_id"] == user["id"]
        )
        if not allowed:
            abort(403)
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], stored_name, download_name=submission["file_name"])
    abort(404)


@task_bp.post("/student/tasks/<int:task_id>/complete")
@role_required("student")
def complete_task(task_id: int):
    user = current_user()
    rows = query("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if rows:
        task = rows[0]
        if task["student_id"] is not None:
            execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        else:
            execute(
                "INSERT INTO submissions (task_id, student_id, note) VALUES (?, ?, ?)",
                (task_id, user["id"], "Marcada como completada"),
            )
    return redirect(url_for("dashboard.dashboard"))


@task_bp.post("/student/tasks/<int:task_id>/submit")
@role_required("student")
def submit_task(task_id: int):
    user = current_user()
    rows = query(
        "SELECT * FROM tasks WHERE id = ? AND (student_id = ? OR student_id IS NULL)",
        (task_id, user["id"]),
    )
    if not rows:
        abort(404)
    task = rows[0]
    note = request.form.get("note", "").strip()
    had_file = bool(request.files.get("attachment") and request.files["attachment"].filename)
    stored_name, original_name, _ = save_upload("attachment")
    if had_file and stored_name is None:
        return redirect(url_for("dashboard.dashboard"))
    if not stored_name and not note:
        flash("Agregá un archivo o un comentario para entregar la tarea.", "warning")
        return redirect(url_for("dashboard.dashboard"))
    execute(
        "INSERT INTO submissions (task_id, student_id, file_path, file_name, note) VALUES (?, ?, ?, ?, ?)",
        (task_id, user["id"], stored_name, original_name, note),
    )
    # Solo marcamos 'completed = 1' en la tabla 'tasks' si es una tarea individual dirigida a un solo alumno
    if task["student_id"] is not None:
        execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        
    flash("¡Entrega subida! Tu profesor/a ya la puede ver.", "success")
    return redirect(url_for("dashboard.dashboard"))