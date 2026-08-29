"""
Adaptación de texto con IA, usando un modelo LOCAL vía Ollama — gratis,
sin API key, sin internet (una vez descargado el modelo).
"""
import requests

import config

SYSTEM_PROMPT = """Sos un asistente pedagógico experto. Reescribis el texto completo de una tarea escolar en lenguaje simple, concreto y sin ambigüedades, adaptado a las necesidades del alumno. Procesá todo el texto recibido sin omitir ninguna sección ni limitar la cantidad de pasos resultante. No agregues contenido nuevo ni cambies el significado de la actividad.

Reglas estrictas de formato:
Empezá tu respuesta DIRECTAMENTE con el paso 1. No escribas saludos, introducciones, ni frases como "Claro, aquí está". Solo el texto adaptado en pasos numerados. Nada más."""


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
            timeout=90,
        )
        respuesta.raise_for_status()
        return respuesta.json()["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        print("No se pudo conectar con Ollama. ¿Está corriendo? (ollama run llama3.1)")
        return texto_original
    except Exception as e:
        print(f"Error llamando a Ollama: {e}")
        return texto_original