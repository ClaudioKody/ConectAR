"""
Adaptación de texto con IA, usando un modelo LOCAL vía Ollama — gratis,
sin API key, sin internet (una vez descargado el modelo).

Requisitos previos (una sola vez, en la máquina que corre la demo):
    1. Instalar Ollama: https://ollama.com/download
    2. Descargar el modelo:  ollama pull llama3.1
    3. Dejar Ollama corriendo (queda solo en la bandeja del sistema tras instalarlo)

Si Ollama no está corriendo, o el modelo no está descargado, o cualquier
otra cosa falla: se devuelve el texto original sin adaptar. Nunca se rompe
el flujo de creación de tareas por esto.
"""
import re

import requests

import config

SYSTEM_PROMPT = """Sos un asistente pedagógico. Reescribís el texto de una tarea \
escolar en lenguaje simple, concreto y sin ambigüedades, adaptado a las \
necesidades del alumno que se te indican. No agregues contenido nuevo ni \
cambies el significado de la actividad.

Reglas estrictas de formato:
- Empezá tu respuesta DIRECTAMENTE con el paso 1. No escribas saludos, \
introducciones, ni frases como "Claro, aquí está" o "Aquí te dejo el texto".
- No agregues comentarios sobre lo que hiciste, ni cierres tipo "Espero que te sirva".
- Solo el texto adaptado, en pasos numerados. Nada más.

Ejemplo de formato correcto:
1. Primer paso en lenguaje simple.
2. Segundo paso en lenguaje simple.

Ejemplo de formato INCORRECTO (nunca hagas esto):
¡Claro! Aquí tenés el texto adaptado:
1. Primer paso..."""

# Los modelos locales chicos a veces ignoran la instrucción de "sin saludos"
# de arriba. Como red de seguridad, se recorta cualquier texto que venga
# antes del primer paso numerado (ej: "¡Claro! Acá está tu texto:\n1. ...").
_PRIMER_PASO_RE = re.compile(r"(?:\*\*)?\d+[.)]\s")


def _limpiar_respuesta(texto: str) -> str:
    match = _PRIMER_PASO_RE.search(texto)
    if match and match.start() > 0:
        return texto[match.start():].strip()
    return texto.strip()


def adaptar_texto(texto_original: str, perfil_texto: list[str]) -> str:
    """
    texto_original: texto crudo extraído del PDF/TXT (o la descripción de la tarea)
    perfil_texto: lista de strings con las necesidades activas del alumno
    """
    if not texto_original.strip():
        return texto_original

    if perfil_texto:
        contexto = "Necesidades del alumno:\n- " + "\n- ".join(perfil_texto)
    else:
        contexto = "No hay perfil cargado: adaptá el texto de forma general para comprensión simple."

    try:
        respuesta = requests.post(
            f"{config.OLLAMA_HOST}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{contexto}\n\nTexto de la tarea:\n{texto_original}"},
                ],
                "stream": False,
            },
            timeout=90,  # los modelos locales pueden tardar más que una API en la nube
        )
        respuesta.raise_for_status()
        return _limpiar_respuesta(respuesta.json()["message"]["content"])
    except requests.exceptions.ConnectionError:
        print("No se pudo conectar con Ollama. ¿Está corriendo? (ollama run llama3.1)")
        return texto_original
    except Exception as e:
        print(f"Error llamando a Ollama: {e}")
        return texto_original
