"""
Script standalone para probar SOLO la parte de IA, sin necesitar levantar
Flask, la base de datos, ni el resto de la app.

Uso:
    python demo_ai.py

Requiere tener ANTHROPIC_API_KEY completada en el archivo .env
(copiá .env.example a .env primero si todavía no lo hiciste).
"""
from services.ai_service import adaptar_texto
import config

# --- Texto de ejemplo: como si fuera lo extraído de un PDF de tarea ---
TEXTO_EJEMPLO = """
Los alumnos deberán trabajar en grupos de cuatro integrantes durante 30 minutos
para resolver una serie de problemas relacionados con fracciones equivalentes,
y posteriormente exponer oralmente sus conclusiones ante el resto del curso,
fundamentando el procedimiento utilizado para llegar al resultado.
"""

# --- Perfil de ejemplo: como si fuera el perfil de un alumno cargado en la app ---
PERFIL_EJEMPLO = [
    "Necesita instrucciones cortas",
    "Le cuesta interpretar consignas ambiguas",
    "Necesita anticipación de cambios",
    "Necesita dividir actividades en pasos pequeños",
]


def main():
    print("=" * 70)
    print("TEXTO ORIGINAL")
    print("=" * 70)
    print(TEXTO_EJEMPLO.strip())

    print()
    print("=" * 70)
    print("PERFIL DEL ALUMNO")
    print("=" * 70)
    for item in PERFIL_EJEMPLO:
        print(f"- {item}")

    print()
    print("=" * 70)
    print("TEXTO ADAPTADO POR LA IA (Ollama, local)")
    print("=" * 70)
    print("Si esto tarda mucho la primera vez, es normal — el modelo carga en memoria.")
    print()
    resultado = adaptar_texto(TEXTO_EJEMPLO, PERFIL_EJEMPLO)
    print(resultado)
    print("=" * 70)


if __name__ == "__main__":
    main()
