"""
Helpers de sesión y permisos, usados por todos los blueprints.
"""
from datetime import datetime
from functools import wraps

from flask import flash, redirect, session, url_for

from extensions import query


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    rows = query("SELECT * FROM accounts WHERE id = ?", (user_id,))
    return rows[0] if rows else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Iniciá sesión para continuar.", "warning")
            return redirect(url_for("auth.home"))
        return view(*args, **kwargs)
    return wrapped


def role_required(role: str):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None or user["role"] != role:
                flash("No tenés permiso para acceder a esta sección.", "warning")
                return redirect(url_for("dashboard.dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def register_context_processor(app):
    @app.context_processor
    def inject_globals():
        return {"current_user": current_user(), "today_label": datetime.now().strftime("%d/%m/%Y")}
