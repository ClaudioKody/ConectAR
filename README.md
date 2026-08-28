# Conecto+ — Aprendemos juntos

Plataforma web para que docentes se comuniquen y adapten actividades para
alumnos con dificultades de aprendizaje. Hecha en Flask + Jinja2 + SQLite,
con un módulo de perfil de aprendizaje y adaptación de contenido con IA.

## Cómo iniciar la app (paso a paso)

### 1. Instalar dependencias (una sola vez)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Instalar y configurar Ollama (para que la IA funcione)

La adaptación de texto usa un modelo de IA que corre **local y gratis**
con [Ollama](https://ollama.com/download) — no requiere ninguna API key ni
tarjeta de crédito. Sin Ollama corriendo, la app funciona igual, solo que
no reescribe el texto (usa el texto original tal cual).

```bash
# 1. Instalar Ollama desde https://ollama.com/download (según tu sistema operativo)
# 2. Una vez instalado, descargar el modelo (una sola vez, ~4.7GB):
ollama pull llama3.1
```

Ollama queda corriendo solo en segundo plano después de instalarlo (ícono
en la bandeja del sistema). No hace falta hacer nada más para que la app lo
detecte.

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

No hace falta tocar nada más del `.env` para que ande con Ollama (los
valores por defecto ya apuntan a `http://localhost:11434`).

### 4. Cargar datos de prueba (opcional, recomendado para demos)

```bash
python seed_demo.py
```

Esto carga 3 alumnos con perfiles de aprendizaje distintos, tareas, avisos,
mensajes y pedidos de ayuda ya armados. Cuentas de prueba (password para
todas: `demo1234`):

| Rol | Email |
|---|---|
| Profesora | `ana@escuela.com` |
| Alumno | `tomas@alumno.com` |
| Alumna | `martina@alumno.com` |
| Alumno | `joaquin@alumno.com` |

Si en algún momento quieren reiniciar los datos de prueba desde cero:
`python seed_demo.py --reset`

### 5. Levantar el servidor

```bash
python app.py
```

Abrir `http://127.0.0.1:5000` en el navegador. La base SQLite se crea sola
en `instance/conecto.sqlite3` la primera vez que corre.

## Probar solo la parte de IA (sin levantar toda la app)

```bash
python demo_ai.py
```

Corre la función de adaptación de texto sola, con un ejemplo fijo, sin
necesitar login ni base de datos. Útil para probar cambios en el prompt
rápido. La primera consulta a Ollama puede tardar 10-40 segundos (carga
el modelo en memoria); las siguientes son más rápidas.

## Tests automatizados

```bash
python -m pytest tests/ -v
```

7 tests, no dependen de Ollama (siempre tienen que pasar, esté Ollama
corriendo o no).

## Estructura del proyecto

```
conecto/
├── app.py                    # Arma la app y registra los blueprints
├── config.py                  # Paths, constantes, schema de la DB, glosario, perfil
├── extensions.py               # Conexión a SQLite (get_db, query, execute)
├── security.py                  # current_user, login_required, role_required
├── utils.py                      # Extracción de PDF/TXT, glosario, progreso, calendario
├── seed_demo.py                   # Carga datos de prueba para demos
├── demo_ai.py                      # Prueba la IA sola, sin levantar toda la app
├── services/
│   └── ai_service.py                # Adaptación de texto con Ollama según perfil
├── routes/
│   ├── auth_routes.py                # Login, registro, logout
│   ├── dashboard_routes.py           # Panel de profesor y alumno
│   ├── task_routes.py                 # Tareas, adjuntos, entregas (+ hook de IA)
│   ├── communication_routes.py        # Mensajes, avisos, ayuda, contactos
│   └── profile_routes.py              # Perfil de aprendizaje
├── static/style.css                    # Sistema de diseño (paleta calma, tipografía accesible)
├── templates/                           # Un archivo por pantalla
└── tests/test_app.py                     # 7 tests, siguen pasando
```

## Qué hace la IA (y qué no)

Cuando el profesor crea una tarea con un archivo PDF/TXT adjunto, dirigida a
un alumno con perfil de aprendizaje cargado, el texto extraído se manda a
Ollama (modelo local) para reescribirlo en lenguaje simple según las
necesidades de ese alumno, ANTES de dividirlo en pasos. Si Ollama no está
corriendo, o falla por cualquier motivo, se usa el texto extraído tal cual
(sin adaptar) — nunca se rompe el flujo de creación de tareas.

Ver `HANDOFF.md` para el detalle de qué falta y cómo seguir si en algún
momento quieren volver a una API paga (Anthropic u otra) en vez de Ollama.

Commit de ramasg