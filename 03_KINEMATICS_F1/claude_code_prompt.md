# Prompt para Claude Code — continuar el módulo 03

Copia/pega esto en Claude Code (desde la raíz de F1_DATA) cuando quieras
retomar o extender el módulo. Ajusta la sección "Tarea de hoy".

---

Estoy trabajando en `03_KINEMATICS_F1`, el módulo de validación cinemática de
mi portafolio F1 (lee `CLAUDE.md` y `03_KINEMATICS_F1/README.md` primero).

Contexto del módulo:
- `src/quarter_car.py`: modelo quarter-car 2-DOF. Modo cuasi-estático
  (predice recorrido de suspensión desde Speed/LongAccel/LatAccel) y modo
  dinámico (RK4 sobre perfil de pista). Parámetros en `geometry.json` —
  ojo: si `"estimated": true`, la geometría sigue siendo placeholder.
- `src/validate_kinematics.py`: compara predicción vs canales SuspTravel_*
  de un CSV canónico (schema de `01_TELEMETRY_F1/src/f1core/schema.py`).
  Métricas: r (forma/física), gain (rigidez+MR), RMSE. Reporte HTML oscuro.
- `src/make_demo_data.py`: vuelta sintética SOLO para probar el pipeline
  (r≈0.99, gain≈1.15 esperados por construcción).
- El dashboard de `01_TELEMETRY_F1/src/dashboard.py` tiene una pestaña
  "🔧 Cinemática" que usa este módulo vía import perezoso con fallback.

Convenciones obligatorias (de CLAUDE.md):
- Código en inglés, documentación y docstrings en español explicando el
  PORQUÉ de cada análisis.
- Dash/Plotly con el tema `COLORS` del dashboard, nunca Streamlit.
- Toda fuente de datos nueva entra por un adaptador en `f1core/adapters/`
  que produce el schema canónico; la lógica de análisis no vive ahí.

Tarea de hoy:
[ELIGE UNA]
- He medido la geometría real en CATIA: ayúdame a actualizar geometry.json
  (te paso las medidas) y a re-interpretar los modos propios.
- Tengo mi primer export real de MoTeC i2 en [ruta]: conviértelo con el
  adaptador de AC, valida los nombres de canal (puede hacer falta
  column_map) y corre la validación completa.
- La validación dio r=[X], gain=[Y]: ayúdame a diagnosticar qué parámetro
  del modelo está mal y a iterarlo.
- Extiende el modelo a half-car (heave + roll acoplados) manteniendo la
  misma interfaz de validación.

Al terminar: verifica ejecutando los scripts, y actualiza README.md y la
sección "Estado y pendientes" de CLAUDE.md.
