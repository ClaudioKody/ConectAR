"""
Carga datos de prueba realistas para la demo del hackaton: profesores,
alumnos con perfiles de aprendizaje variados, tareas, avisos, mensajes,
pedidos de ayuda y contactos familiares.

Uso:
    python seed_demo.py            -> carga los datos (no duplica si ya están)
    python seed_demo.py --reset    -> borra TODOS los datos existentes y vuelve a cargar

Password para todas las cuentas de prueba: demo1234
"""
import sys

from werkzeug.security import generate_password_hash

from app import app
from extensions import execute, query

PASSWORD_HASH = generate_password_hash("demo1234")


def reset_all_data():
    tablas = [
        "check_ins", "help_requests", "student_notices", "family_contacts",
        "submissions", "messages", "announcements", "learning_profiles",
        "tasks", "accounts",
    ]
    for tabla in tablas:
        try:
            execute(f"DELETE FROM {tabla}")
        except Exception:
            pass  # la tabla check_ins no existe en este proyecto (era del otro), se ignora
    print("Datos anteriores borrados.")


def ya_sembrado():
    return bool(query("SELECT id FROM accounts WHERE email = 'ana@escuela.com'"))


def crear_cuenta(role, nombre, email):
    return execute(
        "INSERT INTO accounts (role, full_name, email, password_hash) VALUES (?, ?, ?, ?)",
        (role, nombre, email, PASSWORD_HASH),
    )


def crear_perfil(student_id, **campos):
    columnas = ", ".join(campos.keys())
    placeholders = ", ".join(["?"] * len(campos))
    execute(
        f"INSERT INTO learning_profiles (student_id, {columnas}) VALUES (?, {placeholders})",
        (student_id, *campos.values()),
    )


def main():
    with app.app_context():
        if "--reset" in sys.argv:
            reset_all_data()
        elif ya_sembrado():
            print("Ya hay datos de prueba cargados. Usá --reset si querés reiniciar.")
            return

        # --- Docentes ---
        ana_id = crear_cuenta("teacher", "Profe Ana", "ana@escuela.com")
        execute("UPDATE accounts SET subjects = ? WHERE id = ?", ("Matemática,Lengua,Ciencias Naturales", ana_id))

        # --- Alumnos ---
        tomas_id = crear_cuenta("student", "Tomás G.", "tomas@alumno.com")
        martina_id = crear_cuenta("student", "Martina P.", "martina@alumno.com")
        joaquin_id = crear_cuenta("student", "Joaquín R.", "joaquin@alumno.com")

        # --- Perfiles de aprendizaje (variados, para mostrar que no es un molde único) ---
        crear_perfil(
            tomas_id,
            instrucciones_cortas=1, dificultad_consignas_ambiguas=1,
            necesita_anticipacion=1, funciona_con_rutinas=1, necesita_pasos_pequenos=1,
            necesita_pausas=1, preferencia_visual=1,
        )
        crear_perfil(
            martina_id,
            instrucciones_escritas=1, dificultad_consignas_ambiguas=1,
            necesita_anticipacion=1, preferencia_visual=1,
        )
        crear_perfil(
            joaquin_id,
            instrucciones_cortas=1, funciona_con_rutinas=1,
            sensible_ruido=1, necesita_pausas=1,
        )

        # --- Tareas (con texto ya escrito "en estilo adaptado", para que la demo
        #     se vea completa aunque todavía no esté cargado el crédito de la IA) ---
        tarea1_id = execute(
            "INSERT INTO tasks (teacher_id, student_id, subject, title, description, steps, due_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ana_id, tomas_id, "Matemática", "Fracciones equivalentes",
                "Actividad grupal para trabajar fracciones equivalentes.",
                "Formar un grupo de 4 compañeros\n"
                "Escuchar la consigna leída en voz alta\n"
                "Resolver 3 ejercicios de fracciones en la hoja\n"
                "Compartir la respuesta con el grupo (se puede escribir o decir en voz alta)\n"
                "Avisar 5 minutos antes de que termine la actividad",
                "2026-08-28",
            ),
        )
        execute(
            "INSERT INTO tasks (teacher_id, student_id, subject, title, description, steps, due_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ana_id, martina_id, "Lengua", "Comprensión de texto: cuento tradicional",
                "Leer el cuento y responder por escrito.",
                "Leer el cuento en silencio (hoja adjunta)\n"
                "Responder 3 preguntas cortas por escrito\n"
                "No hace falta exponer oral, se entrega por escrito",
                "2026-08-27",
            ),
        )
        execute(
            "INSERT INTO tasks (teacher_id, student_id, subject, title, description, steps, due_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ana_id, None, "Ciencias Naturales", "El ciclo del agua",
                "Tarea para todo el curso: dibujar el ciclo del agua con etiquetas.",
                "Mirar el video corto explicativo\n"
                "Dibujar el ciclo del agua en una hoja\n"
                "Escribir el nombre de cada etapa (evaporación, condensación, precipitación)",
                "2026-09-02",
            ),
        )
        tarea4_id = execute(
            "INSERT INTO tasks (teacher_id, student_id, subject, title, description, steps, due_at, completed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            (
                ana_id, joaquin_id, "Matemática", "Multiplicaciones con 2 cifras",
                "Práctica de multiplicación.",
                "Resolver 5 multiplicaciones de a una por vez\n"
                "Marcar cada ejercicio resuelto antes de pasar al siguiente",
                "2026-08-20",
            ),
        )

        # --- Avisos ---
        execute(
            "INSERT INTO announcements (teacher_id, student_id, title, body) VALUES (?, NULL, ?, ?)",
            (ana_id, "Recordatorio: excursión al zoológico", "El jueves que viene salimos a las 9hs. Traer vianda y gorra."),
        )
        execute(
            "INSERT INTO announcements (teacher_id, student_id, title, body) VALUES (?, ?, ?, ?)",
            (ana_id, martina_id, "Reunión con la familia", "Quedamos en coordinar una reunión la semana próxima para hablar del progreso."),
        )

        # --- Mensajes (una conversación breve) ---
        execute(
            "INSERT INTO messages (sender_id, receiver_id, body) VALUES (?, ?, ?)",
            (tomas_id, ana_id, "Hola profe, ¿la tarea de fracciones va para el jueves?"),
        )
        execute(
            "INSERT INTO messages (sender_id, receiver_id, body) VALUES (?, ?, ?)",
            (ana_id, tomas_id, "Sí Tomás, el jueves. Cualquier duda me escribís."),
        )

        # --- Pedidos de ayuda ---
        execute(
            "INSERT INTO help_requests (student_id, teacher_id, task_id, option_label, note, status) VALUES (?, ?, ?, ?, ?, 'pendiente')",
            (joaquin_id, ana_id, tarea1_id, "Necesito más tiempo", "No llegué a terminar el ejercicio 3."),
        )
        execute(
            "INSERT INTO help_requests (student_id, teacher_id, task_id, option_label, note, status) VALUES (?, ?, ?, ?, ?, 'atendido')",
            (martina_id, ana_id, None, "Estoy teniendo dificultades", "No entendí bien la segunda pregunta."),
        )

        # --- Contactos familiares ---
        execute(
            "INSERT INTO family_contacts (student_id, contact_name, relationship, phone, email) VALUES (?, ?, ?, ?, ?)",
            (tomas_id, "Laura G.", "Madre", "11-5555-1234", "laura.g@mail.com"),
        )
        execute(
            "INSERT INTO family_contacts (student_id, contact_name, relationship, phone, email) VALUES (?, ?, ?, ?, ?)",
            (joaquin_id, "Marcelo R.", "Padre", "11-5555-9876", "marcelo.r@mail.com"),
        )

        print("Datos de prueba cargados correctamente.")
        print()
        print("Cuentas de prueba (password para todas: demo1234):")
        print("  Profesora -> ana@escuela.com")
        print("  Alumno    -> tomas@alumno.com   (perfil: rutinas, pausas, visual)")
        print("  Alumna    -> martina@alumno.com (perfil: instrucciones escritas, anticipación)")
        print("  Alumno    -> joaquin@alumno.com (perfil: rutinas, sensible al ruido)")


if __name__ == "__main__":
    main()
