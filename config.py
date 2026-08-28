"""
Configuración central: paths, constantes, schema de la base y contenido estático
(glosario, opciones de ayuda). Nada de lógica acá, solo datos.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "instance" / "conecto.sqlite3"
DEFAULT_UPLOAD_DIR = BASE_DIR / "instance" / "uploads"
ALLOWED_EXTENSIONS = {"pdf", "txt", "doc", "docx", "png", "jpg", "jpeg", "gif"}

SECRET_KEY = os.environ.get("CONECTO_SECRET", "cambiame-en-produccion")
UPLOAD_FOLDER = Path(os.environ.get("CONECTO_UPLOADS", DEFAULT_UPLOAD_DIR))
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# IA (Anthropic) - para adaptar el texto de las tareas segun el perfil del alumno.
# IA para adaptar el texto de las tareas segun el perfil del alumno.
# Por defecto usa Ollama (modelo local, gratis, sin key). Si en algún momento
# consiguen crédito de Anthropic, alcanza con volver a activar ANTHROPIC_API_KEY
# y adaptar services/ai_service.py — el resto del proyecto no se entera del cambio.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-4-6")

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
CREATE TABLE IF NOT EXISTS learning_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL UNIQUE REFERENCES accounts(id),
    instrucciones_escritas INTEGER NOT NULL DEFAULT 0,
    instrucciones_cortas INTEGER NOT NULL DEFAULT 0,
    dificultad_consignas_ambiguas INTEGER NOT NULL DEFAULT 0,
    necesita_anticipacion INTEGER NOT NULL DEFAULT 0,
    funciona_con_rutinas INTEGER NOT NULL DEFAULT 0,
    necesita_pasos_pequenos INTEGER NOT NULL DEFAULT 0,
    sensible_ruido INTEGER NOT NULL DEFAULT 0,
    necesita_pausas INTEGER NOT NULL DEFAULT 0,
    preferencia_visual INTEGER NOT NULL DEFAULT 0,
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

CAMPOS_PERFIL = [
    "instrucciones_escritas", "instrucciones_cortas", "dificultad_consignas_ambiguas",
    "necesita_anticipacion", "funciona_con_rutinas", "necesita_pasos_pequenos",
    "sensible_ruido", "necesita_pausas", "preferencia_visual",
]

ETIQUETAS_PERFIL = {
    "instrucciones_escritas": "Prefiere instrucciones escritas",
    "instrucciones_cortas": "Necesita instrucciones cortas",
    "dificultad_consignas_ambiguas": "Le cuesta interpretar consignas ambiguas",
    "necesita_anticipacion": "Necesita anticipación de cambios",
    "funciona_con_rutinas": "Funciona mejor con rutinas",
    "necesita_pasos_pequenos": "Necesita dividir actividades en pasos pequeños",
    "sensible_ruido": "Puede verse afectado por el ruido",
    "necesita_pausas": "Puede necesitar pausas",
    "preferencia_visual": "Prefiere estímulos visuales",
}
