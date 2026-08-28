"""
MODULO NUEVO: Perfil de aprendizaje (Comunicación / Organización / Sensibilidad).
No es un diagnóstico médico: es una guía educativa que carga el docente.

Se usa desde routes/task_routes.py (_perfil_texto_de_alumno) para darle
contexto a la IA al adaptar el contenido de una tarea.
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

import config
from extensions import execute, query
from security import role_required

profile_bp = Blueprint("profiles", __name__)


@profile_bp.route("/teacher/students/<int:student_id>/profile", methods=["GET", "POST"])
@role_required("teacher")
def edit_profile(student_id):
    student_rows = query("SELECT * FROM accounts WHERE id = ? AND role = 'student'", (student_id,))
    if not student_rows:
        abort(404)
    student = student_rows[0]

    if request.method == "POST":
        datos = {campo: (1 if request.form.get(campo) == "on" else 0) for campo in config.CAMPOS_PERFIL}
        existing = query("SELECT id FROM learning_profiles WHERE student_id = ?", (student_id,))
        columnas = ", ".join(config.CAMPOS_PERFIL)
        if existing:
            set_clause = ", ".join(f"{campo} = ?" for campo in config.CAMPOS_PERFIL)
            execute(
                f"UPDATE learning_profiles SET {set_clause} WHERE student_id = ?",
                (*[datos[c] for c in config.CAMPOS_PERFIL], student_id),
            )
        else:
            placeholders = ", ".join(["?"] * len(config.CAMPOS_PERFIL))
            execute(
                f"INSERT INTO learning_profiles (student_id, {columnas}) VALUES (?, {placeholders})",
                (student_id, *[datos[c] for c in config.CAMPOS_PERFIL]),
            )
        flash(f"Perfil de aprendizaje de {student['full_name']} guardado.", "success")
        return redirect(url_for("dashboard.dashboard") + "#students")

    rows = query("SELECT * FROM learning_profiles WHERE student_id = ?", (student_id,))
    perfil = rows[0] if rows else None
    return render_template(
        "profile_form.html",
        student=student,
        perfil=perfil,
        campos=config.CAMPOS_PERFIL,
        etiquetas=config.ETIQUETAS_PERFIL,
    )
