import os
import tempfile

import pytest

from app import app


@pytest.fixture
def client():
    db_file = tempfile.NamedTemporaryFile(delete=False)
    db_file.close()
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    os.environ["CONECTO_DB"] = db_file.name
    with app.test_client() as test_client:
        yield test_client
    os.unlink(db_file.name)
    os.environ.pop("CONECTO_DB", None)


def register(client, role, name, email):
    return client.post(
        "/",
        data={
            "role": role,
            "action": "register",
            "full_name": name,
            "email": email,
            "password": "password123",
        },
        follow_redirects=True,
    )


def test_student_registration_and_dashboard(client):
    response = register(client, "student", "Priscila Toledano", "priscila@example.com")
    assert response.status_code == 200
    assert b"Hola, Priscila" in response.data
    assert b"Tu rutina se va a completar" in response.data


def test_teacher_registration_and_subjects(client):
    response = register(client, "teacher", "Ana Profesora", "ana@example.com")
    assert b"Hola, Ana" in response.data
    response = client.post("/teacher/subjects", data={"subjects": "Matemáticas, Lengua"}, follow_redirects=True)
    assert b"Materias guardadas" in response.data
    assert "Matemáticas".encode("utf-8") in response.data


def test_teacher_task_appears_for_student(client):
    register(client, "teacher", "Ana Profesora", "ana@example.com")
    client.post("/teacher/tasks", data={"subject": "Lengua", "title": "Leer un cuento", "description": "Leer diez minutos"})
    client.get("/logout")
    register(client, "student", "Priscila Toledano", "priscila@example.com")
    response = client.get("/dashboard")
    assert b"Leer un cuento" in response.data
    assert "Lengua".encode("utf-8") in response.data


def test_teacher_announcement_appears_for_student(client):
    register(client, "teacher", "Ana Profesora", "ana@example.com")
    client.post("/teacher/announcements", data={"title": "Aviso importante", "body": "Recordá revisar Aula"})
    client.get("/logout")
    register(client, "student", "Priscila Toledano", "priscila@example.com")
    response = client.get("/dashboard")
    assert b"Aviso importante" in response.data


def test_messages_flow_both_directions(client):
    register(client, "teacher", "Ana Profesora", "ana@example.com")
    client.get("/logout")
    register(client, "student", "Priscila Toledano", "priscila@example.com")

    from app import query

    teacher_id = query("SELECT id FROM accounts WHERE role='teacher'")[0]["id"]
    student_id = query("SELECT id FROM accounts WHERE role='student'")[0]["id"]

    client.post("/messages", data={"receiver_id": teacher_id, "body": "Hola profe, tengo una duda"}, follow_redirects=True)
    client.get("/logout")

    client.post("/", data={"role": "teacher", "action": "login", "email": "ana@example.com", "password": "password123"})
    response = client.get("/dashboard")
    assert b"Hola profe, tengo una duda" in response.data

    client.post("/messages", data={"receiver_id": student_id, "body": "Hola Priscila, te ayudo"}, follow_redirects=True)
    client.get("/logout")

    client.post("/", data={"role": "student", "action": "login", "email": "priscila@example.com", "password": "password123"})
    response = client.get("/dashboard")
    assert b"Hola Priscila, te ayudo" in response.data


def test_task_with_manual_steps_shows_checklist_to_student(client):
    register(client, "teacher", "Ana Profesora", "ana@example.com")
    client.post(
        "/teacher/tasks",
        data={
            "subject": "Matemáticas",
            "title": "Sumas",
            "description": "Sumar números",
            "steps": "Abrir el cuaderno\nEscribir la fecha\nResolver tres sumas",
        },
    )
    client.get("/logout")
    register(client, "student", "Priscila Toledano", "priscila@example.com")
    response = client.get("/dashboard")
    assert b"Abrir el cuaderno" in response.data
    assert b"Resolver tres sumas" in response.data


def test_family_contact_visible_to_teacher(client):
    register(client, "teacher", "Ana Profesora", "ana@example.com")
    client.get("/logout")
    register(client, "student", "Priscila Toledano", "priscila@example.com")
    client.post(
        "/student/family-contacts",
        data={"contact_name": "Marta Toledano", "relationship": "Madre", "phone": "1122334455"},
        follow_redirects=True,
    )
    client.get("/logout")

    client.post("/", data={"role": "teacher", "action": "login", "email": "ana@example.com", "password": "password123"})
    response = client.get("/dashboard")
    assert "Marta Toledano".encode("utf-8") in response.data
