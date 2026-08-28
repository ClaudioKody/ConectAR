"""
MODULO: Autenticación, sesión y administración básica de cuentas.
"""
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import execute, query
from security import role_required
from utils import touch_last_login

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        role = request.form.get("role", "student")
        action = request.form.get("action", "login")
        if action == "register":
            return _register(role)
        return _login(role)
    return render_template("index.html")


def _login(role: str):
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = query("SELECT * FROM accounts WHERE email = ? AND role = ?", (email, role))
    if not user or not check_password_hash(user[0]["password_hash"], password):
        flash("No encontramos una cuenta con esos datos. Podés registrarte primero.", "warning")
        return render_template("index.html", selected_role=role, show_register=True, email=email)
    session.clear()
    session["user_id"] = user[0]["id"]
    touch_last_login(user[0]["id"])
    return redirect(url_for("dashboard.dashboard"))


def _register(role: str):
    name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if len(name) < 2 or "@" not in email or len(password) < 8:
        flash("Completá nombre, correo válido y una contraseña de al menos 8 caracteres.", "warning")
        return render_template("index.html", selected_role=role, show_register=True)
    try:
        user_id = execute(
            "INSERT INTO accounts (role, full_name, email, password_hash) VALUES (?, ?, ?, ?)",
            (role, name, email, generate_password_hash(password)),
        )
    except sqlite3.IntegrityError:
        flash("Ese correo ya está registrado. Probá iniciar sesión.", "warning")
        return render_template("index.html", selected_role=role, show_register=True, email=email)
    session.clear()
    session["user_id"] = user_id
    touch_last_login(user_id)
    flash("Tu cuenta fue creada correctamente.", "success")
    return redirect(url_for("dashboard.dashboard"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.home"))


@auth_bp.route("/delete_student/<int:student_id>", methods=["POST"])
@role_required("teacher")
def delete_student(student_id):
    execute("DELETE FROM accounts WHERE id = ? AND role = 'student'", (student_id,))
    return redirect(url_for("dashboard.dashboard") + "#students")
