"""
Funciones de apoyo sin estado de sesión: extracción de texto, glosario,
cálculos de progreso/calendario, subida de archivos, mensajería.
"""
from __future__ import annotations

import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import current_app, flash, request
from werkzeug.utils import secure_filename

import config
from extensions import execute, query

SENTENCE_SPLIT_RE = re.compile(r'(?<=[.?!])\s+')


def find_glossary_terms(text: str) -> list[dict[str, str]]:
    lowered = (text or "").lower()
    found = [{"term": term, "definition": definition} for term, definition in config.GLOSSARY.items() if term in lowered]
    return sorted(found, key=lambda item: item["term"])


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
    if extension not in config.ALLOWED_EXTENSIONS:
        flash("Ese tipo de archivo no está permitido. Usá PDF, TXT, DOC, DOCX o imágenes.", "warning")
        return None, None, ""
    upload_dir = current_app.config["UPLOAD_FOLDER"]
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
