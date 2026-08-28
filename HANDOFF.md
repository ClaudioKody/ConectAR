# Handoff — estado del proyecto y qué falta

Este documento es para el equipo, escrito por Leonel antes de dejar de
trabajar en el proyecto. Acá está todo lo que se hizo, cómo probarlo, y
qué queda pendiente.

## Qué está funcionando (probado de punta a punta)

- ✅ Login, registro y roles (profesor/alumno)
- ✅ Perfil de aprendizaje configurable por alumno (Comunicación / Organización / Sensibilidad)
- ✅ Crear tareas, con o sin archivo adjunto (PDF/TXT)
- ✅ **Adaptación de texto con IA** (Ollama local, gratis): al crear una tarea con
  adjunto para un alumno con perfil cargado, el texto se reescribe en pasos
  simples automáticamente. Probado en vivo, funciona.
- ✅ Mensajería, avisos, pedidos de ayuda, contactos familiares (esto ya lo
  tenía armado el proyecto original, no se tocó la lógica)
- ✅ Diseño visual nuevo: paleta calma (sin colores saturados, pensado para
  chicos con sensibilidad sensorial) + tipografía accesible
  (Atkinson Hyperlegible)
- ✅ Sonido de notificación opcional (apagado por defecto, se prende desde
  Configuración — igual que el toggle de lectura por voz que ya existía)
- ✅ 7 tests automatizados, todos pasando
- ✅ Script de datos de prueba (`seed_demo.py`) para no arrancar con la base vacía

## Cómo probar todo esto

Ver `README.md` — tiene el paso a paso completo de instalación y arranque.

## Qué falta / qué pulir

### Prioridad alta (antes de presentar)

- [ ] **Probar con archivos PDF reales de la escuela** donde vayan a hacer la
  demo, no solo con los de prueba. Textos reales pueden tener formato raro
  (columnas, tablas) que `pypdf` no siempre extrae bien.
- [ ] **Decidir quién hace la demo en vivo** y confirmar que ESA compu
  específica tenga Ollama instalado y probado (no hace falta que todo el
  equipo lo tenga — ver sección "Ollama" más abajo).
- [ ] Revisar que el prompt de IA (`services/ai_service.py`, variable
  `SYSTEM_PROMPT`) funcione bien con la materia/edad específica que vayan a
  mostrar en la demo. Ya se ajustó una vez porque el modelo agregaba saludos
  tipo "¡Claro! Acá está tu texto" — si vuelve a pasar con otro texto, hay
  una función `_limpiar_respuesta()` que lo recorta automáticamente, pero
  si el modelo cambia mucho el formato puede necesitar otro ajuste.

### Prioridad media (mejoraría la demo pero no es bloqueante)

- [ ] El perfil de aprendizaje no se muestra visualmente en la pantalla de
  detalle de tarea del alumno — solo se usa "por atrás" para generar la
  adaptación. Podría ser lindo mostrar un resumen tipo "esta tarea fue
  adaptada porque necesitás instrucciones cortas" en algún lado.
- [ ] El botón de "Cargar perfil" en el dashboard del profesor es funcional
  pero visualmente básico — el formulario (`templates/profile_form.html`)
  se puede pulir más.
- [ ] No hay indicador de "cargando..." mientras la IA procesa el texto
  (puede tardar 10-40 segundos con Ollama). Ahora mismo la página
  simplemente tarda en redirigir, sin feedback visual. Sería bueno agregar
  un mensaje tipo "Adaptando la actividad, esperá un momento..."

### Prioridad baja (si sobra tiempo)

- [ ] Pictogramas o apoyo visual adicional en las tareas (no se llegó a
  implementar, quedó fuera del scope por tiempo)
- [ ] El panel de check-ins/notificaciones no es tiempo real (no hay
  websockets) — se actualiza al recargar la página, no automáticamente

## Sobre Ollama (importante entenderlo bien)

- Ollama corre **local**, en la compu de quien lo instaló. No hace falta que
  todo el equipo lo instale — solo la persona que va a mostrar la demo en
  vivo necesita tenerlo corriendo en su máquina.
- Si alguien del equipo no tiene Ollama, la app funciona igual (solo que la
  adaptación de texto no hace nada extra — usa el texto original). No se
  rompe nada.
- El código que llama a la IA está **aislado en un solo archivo**
  (`services/ai_service.py`) a propósito. Si en algún momento consiguen
  crédito de una API paga (Anthropic u otra) y quieren mejor calidad de
  respuesta, alcanza con reescribir ese archivo — nada más del proyecto se
  entera del cambio. La función que hay que mantener se llama
  `adaptar_texto(texto_original, perfil_texto)` y tiene que devolver un string.

## Decisiones de diseño que quizás valga la pena conocer

- **Por qué SQLite y no MySQL**: para minimizar el setup en cada compu del
  equipo durante el hackathon (SQLite no necesita servidor, es un archivo).
  Si el proyecto sigue después del hackathon y necesita más de un usuario
  concurrente escribiendo a la vez, ahí sí conviene migrar a Postgres o
  MySQL.
- **Por qué blueprints y no todo en `app.py`**: el proyecto original tenía
  744 líneas en un solo archivo. Con 4 personas tocando el código en
  paralelo, eso generaba conflictos de merge constantes. Se separó por
  dominio (auth, dashboard, tareas, comunicación, perfil) para que cada
  persona pueda trabajar en su archivo sin pisar a los demás.
- **Por qué el fallback en todos lados** (IA, subida de archivos, etc.):
  para que nada rompa la demo en vivo. Si algo falla (sin Ollama, sin
  internet, archivo raro), la app degrada a un comportamiento más simple en
  vez de tirar un error en pantalla.

## Contacto

Cualquier duda sobre decisiones técnicas puntuales, este documento + los
comentarios en el código (`services/ai_service.py` y `routes/task_routes.py`
tienen bastante detalle) deberían cubrir la mayoría de las preguntas.
