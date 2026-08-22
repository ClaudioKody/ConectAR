# Conecto+ — versión Python

Esta carpeta contiene una migración paralela de Conecto+ que no requiere Node.js. Usa Flask, Jinja2, SQLite y JavaScript del navegador para conservar los paneles visuales y los flujos principales de alumno y profesor.

## Requisitos

Se necesita Python 3.10 o superior. La versión original de React/Node permanece en el directorio padre como respaldo y no se modifica con esta migración.

## Instalación

Desde esta carpeta, crear y activar el entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

En Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Ejecución

```bash
export CONECTO_SECRET='cambiá-esta-clave'
python app.py
```

En Windows PowerShell:

```powershell
$env:CONECTO_SECRET='cambiá-esta-clave'
python app.py
```

Abrir `http://127.0.0.1:5000`. La base de datos SQLite se crea automáticamente en `instance/conecto.sqlite3`.

## Flujos incluidos

La pantalla inicial permite elegir alumno o profesor antes de mostrar las credenciales. Ambos roles pueden registrarse con nombre, correo y contraseña.

El profesor puede:
- Registrar sus materias.
- Crear una tarea nueva desde el botón "Nueva tarea" de Inicio (se abre en una ventana emergente, sin salir de la sección Inicio), dirigida a un alumno puntual o a todo el curso, eligiendo entre las materias que ya registró.
- Adjuntar un archivo a la tarea (PDF, TXT, Word o imagen). Si es PDF o TXT, Conecto+ extrae el texto automáticamente y lo separa en pasos cortos y numerados para el alumno; el profesor también puede escribir los pasos a mano.
- Publicar avisos importantes.
- Escribirle directamente a cada alumno registrado desde "Comunicación", con el historial de mensajes y un aviso de mensajes nuevos sin leer.
- Ver los contactos familiares que cada alumno registró, en "Reunión con familiares", con un botón para copiar el teléfono o correo y coordinar por privado.

El alumno puede:
- Ver sus tareas como una lista de pasos simple y clara (en vez de un párrafo largo), con un botón para escuchar la tarea en voz alta y un enlace al archivo adjunto adaptado.
- Recibir avisos importantes.
- Escribirle a cualquier profesor registrado y ver las respuestas en el mismo hilo de conversación.
- Registrar un contacto familiar (nombre, relación, teléfono o correo) para que el profesor pueda coordinar una reunión.

## Notas sobre la simplificación de archivos

La adaptación automática de contenido funciona extrayendo el texto de archivos PDF y TXT y separándolo en oraciones/pasos cortos. Es una simplificación estructural (paso a paso), no una reescritura del lenguaje con inteligencia artificial: si en el futuro se quiere resumir o reformular el texto con un modelo de lenguaje (por ejemplo, para acortar oraciones complejas), se puede conectar la función `split_into_steps` de `app.py` a un servicio externo de IA usando una API key propia.

Esta edición Python no es una conversión binaria del frontend React: la interfaz fue reescrita con plantillas Jinja2 y CSS vanilla.
