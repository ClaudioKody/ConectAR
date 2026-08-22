from __future__ import annotations
import os
import re
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "instance" / "conecto.sqlite3"
DEFAULT_UPLOAD_DIR = BASE_DIR / "instance" / "uploads"
ALLOWED_EXTENSIONS = {"pdf", "txt", "doc", "docx", "png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("CONECTO_SECRET", "cambiame-en-produccion")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = Path(os.environ.get("CONECTO_UPLOADS", DEFAULT_UPLOAD_DIR))

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK (role IN ('student', 'teacher')),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    subjects TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL REFERENCES accounts(id),
    student_id INTEGER REFERENCES accounts(id),
    subject TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    steps TEXT NOT NULL DEFAULT '',
    file_path TEXT,
    file_name TEXT,
    due_at TEXT,
    completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL REFERENCES accounts(id),
    student_id INTEGER REFERENCES accounts(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    important INTEGER NOT NULL DEFAULT 1,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL REFERENCES accounts(id),
    receiver_id INTEGER NOT NULL REFERENCES accounts(id),
    body TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS family_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES accounts(id),
    contact_name TEXT NOT NULL,
    relationship TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    student_id INTEGER NOT NULL REFERENCES accounts(id),
    file_path TEXT,
    file_name TEXT,
    note TEXT NOT NULL DEFAULT '',
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS help_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES accounts(id),
    teacher_id INTEGER NOT NULL REFERENCES accounts(id),
    task_id INTEGER REFERENCES tasks(id),
    option_label TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pendiente',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS student_notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES accounts(id),
    teacher_id INTEGER REFERENCES accounts(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

HELP_OPTIONS = [
    {"key": "explain", "label": "Explicame la tarea paso a paso"},
    {"key": "repeat", "label": "Necesito que me expliquen nuevamente"},
    {"key": "difficulty", "label": "Estoy teniendo dificultades"},
    {"key": "time", "label": "Necesito más tiempo"},
    {"key": "talk", "label": "Quiero hablar con mi profesor"},
]

GLOSSARY = {
    "fracción": "Un número que representa una parte de un todo, como 1/2.",
    "numerador": "El número de arriba en una fracción. Indica cuántas partes tomamos.",
    "denominador": "El número de abajo en una fracción. Indica en cuántas partes se divide el todo.",
    "ecuación": "Una igualdad matemática con un valor desconocido para calcular.",
    "perímetro": "La medida del contorno de una figura, sumando todos sus lados.",
    "área": "El espacio que ocupa una figura, medida en unidades cuadradas.",
    "múltiplo": "Un número que resulta de multiplicar otro número por un entero.",
    "divisor": "Un número que divide a otro de forma exacta, sin dejar resto.",
    "sinónimo": "Una palabra que significa lo mismo que otra.",
    "antónimo": "Una palabra que significa lo contrario de otra.",
    "sustantivo": "Una palabra que nombra personas, animales, lugares o cosas.",
    "adjetivo": "Una palabra que describe cómo es un sustantivo.",
    "párrafo": "Un grupo de oraciones que hablan de la misma idea.",
    "hipótesis": "Una idea que se propone para explicar algo y que después se comprueba.",
    "fotosíntesis": "El proceso con el que las plantas transforman la luz del sol en alimento.",
    "ecosistema": "El conjunto de seres vivos y el ambiente donde viven juntos.",
    "célula": "La unidad más pequeña que forma a los seres vivos.",
    "revolución": "Un cambio grande e importante en la forma de vivir o de gobernar.",
    "independencia": "El momento en que un lugar deja de depender de otro y se gobierna solo.",
    "civilización": "Un grupo grande de personas que comparte cultura, normas y forma de vida.",
    "coordenadas": "Números que indican la posición exacta de un punto en un mapa o gráfico.",
    "latitud": "La distancia de un lugar al ecuador, medida de norte a sur.",
    "longitud": "La distancia de un lugar al meridiano de Greenwich, medida de este a oeste.",
    "vocabulario": "El conjunto de palabras que conocemos y usamos.",
    "resumen": "Un texto corto que cuenta las ideas más importantes de otro texto más largo.",
    "consigna": "La indicación que dice qué hay que hacer en una actividad o tarea.",
}

def find_glossary_terms(text: str) -> list[dict[str, str]]:
    lowered = (text or "").lower()
    found = [{"term": term, "definition": definition} for term, definition in GLOSSARY.items() if term in lowered]
    return sorted(found, key=lambda item: item["term"])

def _ensure_columns(db: sqlite3.Connection) -> None:
    def existing_columns(table: str) -> set[str]:
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
    
    task_columns = existing_columns("tasks")
    if "steps" not in task_columns:
        db.execute("ALTER TABLE tasks ADD COLUMN steps TEXT NOT NULL DEFAULT ''")
    if "file_path" not in task_columns:
        db.execute("ALTER TABLE tasks ADD COLUMN file_path TEXT")
    if "file_name" not in task_columns:
        db.execute("ALTER TABLE tasks ADD COLUMN file_name TEXT")
        
    message_columns = existing_columns("messages")
    if "is_read" not in message_columns:
        db.execute("ALTER TABLE messages ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0")
        
    account_columns = existing_columns("accounts")
    if "last_login" not in account_columns:
        db.execute("ALTER TABLE accounts ADD COLUMN last_login TEXT")
    db.commit()

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(os.environ.get("CONECTO_DB", DEFAULT_DB_PATH))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.executescript(SCHEMA)
        _ensure_columns(g.db)
    return g.db

@app.teardown_appcontext
def close_db(_error: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return get_db().execute(sql, params).fetchall()

def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    db = get_db()
    cursor = db.execute(sql, params)
    db.commit()
    return int(cursor.lastrowid)

def current_user() -> sqlite3.Row | None:
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
            return redirect(url_for("home"))
        return view(*args, **kwargs)
    return wrapped

def role_required(role: str):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None or user["role"] != role:
                flash("No tenés permiso para acceder a esta sección.", "warning")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "today_label": datetime.now().strftime("%d/%m/%Y")}

SENTENCE_SPLIT_RE = re.compile(r'(?<=[.?!])\s+')

def split_into_steps(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    lines = [line.strip("\t.-") for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines[:12]
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return sentences[:12] if sentences else [text]

def extract_pdf_text(path: Path, max_chars: int = 4000) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        parts = [(page.extract_text() or "") for page in reader.pages[:8]]
        return "\n".join(parts).strip()[:max_chars]
    except Exception:
        return ""

def extract_txt_text(path: Path, max_chars: int = 4000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip()[:max_chars]
    except OSError:
        return ""

def unread_message_count(user_id: int) -> int:
    row = query("SELECT COUNT(*) AS c FROM messages WHERE receiver_id = ? AND is_read = 0", (user_id,))
    return row[0]["c"]

def message_thread(user_id: int, other_id: int, limit: int = 50) -> list[sqlite3.Row]:
    rows = query(
        """SELECT * FROM messages
           WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
           ORDER BY created_at DESC LIMIT ?""",
        (user_id, other_id, other_id, user_id, limit),
    )
    execute("UPDATE messages SET is_read = 1 WHERE receiver_id = ? AND sender_id = ?", (user_id, other_id))
    return list(reversed(rows))

def unread_from(sender_id: int, receiver_id: int) -> int:
    row = query(
        "SELECT COUNT(*) AS c FROM messages WHERE sender_id = ? AND receiver_id = ? AND is_read = 0",
        (sender_id, receiver_id),
    )
    return row[0]["c"]

def mark_all_read(receiver_id: int) -> None:
    execute("UPDATE messages SET is_read = 1 WHERE receiver_id = ? AND is_read = 0", (receiver_id,))

def touch_last_login(user_id: int) -> None:
    execute("UPDATE accounts SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))

def progress_summary(tasks: list[sqlite3.Row]) -> dict[str, int]:
    total = len(tasks)
    completed = sum(1 for t in tasks if t["completed"])
    percent = round((completed / total) * 100) if total else 0
    return {"total": total, "completed": completed, "pending": total - completed, "percent": percent}

def upcoming_events(tasks: list[sqlite3.Row], limit: int = 6) -> list[sqlite3.Row]:
    dated = [t for t in tasks if t["due_at"] and not t["completed"]]
    dated.sort(key=lambda t: t["due_at"])
    return dated[:limit]

def build_month_calendar(tasks: list[sqlite3.Row]) -> dict[str, Any]:
    import calendar as calendar_module
    today = datetime.now()
    events_by_day: dict[int, list[str]] = {}
    for task in tasks:
        if not task["due_at"]:
            continue
        try:
            due = datetime.strptime(task["due_at"][:10], "%Y-%m-%d")
        except ValueError:
            continue
        if due.year == today.year and due.month == today.month:
            events_by_day.setdefault(due.day, []).append(task["title"])
    cal = calendar_module.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(today.year, today.month)
    month_name = calendar_module.month_name[today.month].capitalize()
    return {
        "month_label": f"{month_name} {today.year}",
        "weekday_labels": ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"],
        "weeks": weeks,
        "today": today.day,
        "events_by_day": events_by_day,
    }

def save_upload(field_name: str) -> tuple[str | None, str | None, str]:
    uploaded = request.files.get(field_name)
    if not uploaded or not uploaded.filename:
        return None, None, ""
    safe_name = secure_filename(uploaded.filename)
    extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        flash("Ese tipo de archivo no está permitido. Usá PDF, TXT, DOC, DOCX o imágenes.", "warning")
        return None, None, ""
    upload_dir = app.config["UPLOAD_FOLDER"]
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    destination = upload_dir / stored_name
    uploaded.save(destination)
    extracted_text = ""
    if extension == "pdf":
        extracted_text = extract_pdf_text(destination)
    elif extension == "txt":
        extracted_text = extract_txt_text(destination)
    return stored_name, safe_name, extracted_text

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        role = request.form.get("role", "student")
        action = request.form.get("action", "login")
        if action == "register":
            return register(role)
        return login(role)
    return render_template("index.html")

def login(role: str):
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = query("SELECT * FROM accounts WHERE email = ? AND role = ?", (email, role))
    if not user or not check_password_hash(user[0]["password_hash"], password):
        flash("No encontramos una cuenta con esos datos. Podés registrarte primero.", "warning")
        return render_template("index.html", selected_role=role, show_register=True, email=email)
    session.clear()
    session["user_id"] = user[0]["id"]
    touch_last_login(user[0]["id"])
    return redirect(url_for("dashboard"))

def register(role: str):
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
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user["role"] == "teacher":
        return teacher_dashboard(user)
    return student_dashboard(user)

def teacher_dashboard(user):
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
        mode="teacher",
    )

def student_dashboard(user):
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
        help_options=HELP_OPTIONS,
        my_help_requests=my_help_requests,
        mode="student",
    )

@app.post("/teacher/subjects")
@role_required("teacher")
def save_subjects():
    subjects = [s.strip() for s in request.form.get("subjects", "").split(",") if s.strip()]
    execute("UPDATE accounts SET subjects = ? WHERE id = ?", (",".join(dict.fromkeys(subjects)), current_user()["id"]))
    flash("Materias guardadas.", "success")
    return redirect(url_for("dashboard"))

@app.post("/teacher/tasks")
@role_required("teacher")
def create_task():
    subject = request.form.get("subject", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    manual_steps = request.form.get("steps", "").strip()
    student_id = request.form.get("student_id") or None
    if not subject or not title:
        flash("La materia y el título son obligatorios.", "warning")
        return redirect(url_for("dashboard"))
    had_file = bool(request.files.get("attachment") and request.files["attachment"].filename)
    stored_name, original_name, extracted_text = save_upload("attachment")
    if had_file and stored_name is None:
        return redirect(url_for("dashboard"))
    steps_source = manual_steps or extracted_text or description
    steps_value = "\n".join(split_into_steps(steps_source))
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
            request.form.get("due_at") or None,
        ),
    )
    flash("Tarea creada y sincronizada con el alumno.", "success")
    return redirect(url_for("dashboard"))

@app.route("/uploads/<path:stored_name>")
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
        return send_from_directory(app.config["UPLOAD_FOLDER"], stored_name, download_name=task["file_name"])
    
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
        return send_from_directory(app.config["UPLOAD_FOLDER"], stored_name, download_name=submission["file_name"])
    abort(404)

@app.post("/teacher/announcements")
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
    return redirect(url_for("dashboard"))

@app.post("/student/tasks/<int:task_id>/complete")
@role_required("student")
def complete_task(task_id: int):
    execute(
        "UPDATE tasks SET completed = 1 WHERE id = ? AND (student_id = ? OR student_id IS NULL)",
        (task_id, current_user()["id"]),
    )
    return redirect(url_for("dashboard"))

@app.post("/student/tasks/<int:task_id>/submit")
@role_required("student")
def submit_task(task_id: int):
    user = current_user()
    rows = query(
        "SELECT * FROM tasks WHERE id = ? AND (student_id = ? OR student_id IS NULL)",
        (task_id, user["id"]),
    )
    if not rows:
        abort(404)
    note = request.form.get("note", "").strip()
    had_file = bool(request.files.get("attachment") and request.files["attachment"].filename)
    stored_name, original_name, _ = save_upload("attachment")
    if had_file and stored_name is None:
        return redirect(url_for("dashboard"))
    if not stored_name and not note:
        flash("Agregá un archivo o un comentario para entregar la tarea.", "warning")
        return redirect(url_for("dashboard"))
    execute(
        "INSERT INTO submissions (task_id, student_id, file_path, file_name, note) VALUES (?, ?, ?, ?, ?)",
        (task_id, user["id"], stored_name, original_name, note),
    )
    execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
    flash("¡Entrega subida! Tu profesor/a ya la puede ver.", "success")
    return redirect(url_for("dashboard"))

@app.post("/student/help")
@role_required("student")
def request_help():
    user = current_user()
    teacher_id = request.form.get("teacher_id")
    option_key = request.form.get("option", "")
    task_id = request.form.get("task_id") or None
    note = request.form.get("note", "").strip()
    teacher_rows = query("SELECT * FROM accounts WHERE id = ? AND role = 'teacher'", (teacher_id,))
    option = next((o for o in HELP_OPTIONS if o["key"] == option_key), None)
    if not teacher_rows or not option:
        flash("Elegí un profesor y el tipo de ayuda que necesitás.", "warning")
        return redirect(url_for("dashboard"))
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
    return redirect(url_for("dashboard"))

@app.post("/teacher/help-requests/<int:request_id>/attend")
@role_required("teacher")
def attend_help_request(request_id: int):
    execute(
        "UPDATE help_requests SET status = 'atendido' WHERE id = ? AND teacher_id = ?",
        (request_id, current_user()["id"]),
    )
    return redirect(url_for("dashboard"))

@app.post("/student/notices")
@role_required("student")
def create_student_notice():
    user = current_user()
    teacher_id = request.form.get("teacher_id") or None
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title or not body:
        flash("Escribí un título y un mensaje para el aviso.", "warning")
        return redirect(url_for("dashboard"))
    execute(
        "INSERT INTO student_notices (student_id, teacher_id, title, body) VALUES (?, ?, ?, ?)",
        (user["id"], teacher_id, title, body),
    )
    flash("Aviso enviado a tu profesor/a.", "success")
    return redirect(url_for("dashboard"))

@app.post("/teacher/notices/<int:notice_id>/dismiss")
@role_required("teacher")
def dismiss_student_notice(notice_id: int):
    execute(
        "UPDATE student_notices SET is_read = 1 WHERE id = ? AND (teacher_id = ? OR teacher_id IS NULL)",
        (notice_id, current_user()["id"]),
    )
    return redirect(url_for("dashboard"))

@app.post("/student/family-contacts")
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
    return redirect(url_for("dashboard"))

@app.post("/messages")
@login_required
def send_message():
    receiver_id = request.form.get("receiver_id")
    body = request.form.get("body", "").strip()
    if receiver_id and body:
        execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (?, ?, ?)", (current_user()["id"], receiver_id, body))
        flash("Mensaje enviado.", "success")
    return redirect(url_for("dashboard"))

@app.route('/delete_student/<int:student_id>', methods=['POST'])
@role_required("teacher")
def delete_student(student_id):
    db = get_db()
    db.execute("DELETE FROM accounts WHERE id = ? AND role = 'student'", (student_id,))
    db.commit()
    return redirect(url_for('dashboard') + '#students')

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))