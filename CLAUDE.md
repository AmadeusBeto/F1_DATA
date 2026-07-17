# F1_DATA — Portafolio de proyectos F1

Portafolio de ingeniería + datos de Roberto. Objetivo: proyectos publicables
(portafolio y Buy Me a Coffee — ver `01_TELEMETRY_F1/bmac_post.md`).

## Convenciones (importante)

- **Documentación y explicaciones en español; código en inglés** (nombres de
  funciones, columnas, variables). Docstrings en español explicando el *porqué*
  de cada análisis — a Roberto le interesa entender, no solo ejecutar.
- Framework de dashboard: **Dash/Plotly** (no Streamlit). Tema oscuro definido
  en `COLORS` de `dashboard.py`.
- Extender los proyectos existentes en vez de crear carpetas nuevas, salvo que
  se pida lo contrario.
- Windows: cuidado con CRLF — los CSV de `data/` pueden aparecer como
  modificados en git solo por fin de línea.

## Estructura

- `01_TELEMETRY_F1/` — Plataforma de telemetría multi-fuente (F1 real + sims).
  - `src/f1core/` — núcleo: `schema.py` (formato canónico + validación),
    `download.py` (FastF1), `prepare.py` (alineación/deltas/estadísticas),
    `setups.py` (setups JSON), `adapters/` (assetto_corsa, forza).
  - `src/dashboard.py` — dashboard con 2 vistas: **Presentación** (mapa de
    dominancia con X/Y, tarjetas, conclusiones automáticas) y **Análisis**
    (trazas completas, mini-sectores, export de reporte HTML a `reports/`).
  - `docs/DATA_TEMPLATE.md` — spec del formato canónico. `docs/SIM_TELEMETRY.md`
    — captura desde Assetto Corsa (ACTI/MoTeC) y Forza (UDP Data Out) + setups.
- `02_SUSPENSION_F1/` — Diseño CAD (CATIA) de suspensión delantera F1 2026,
  FIA Technical Regulations Issue 8, Art. 10. Compliance en `COMPLIANCE.md`.
- `03_KINEMATICS_F1/` — Validación cinemática: quarter-car 2-DOF
  (`src/quarter_car.py`, parámetros en `geometry.json`) vs canales
  `SuspTravel_*` (`src/validate_kinematics.py` → métricas r/gain/RMSE +
  reporte HTML). El dashboard de 01 lo consume en la pestaña "🔧 Cinemática".

## Regla de arquitectura central

Toda fuente de datos nueva (otro sim, otra API) entra por un **adaptador** en
`f1core/adapters/` que traduce columnas/unidades al **schema canónico**
(6 columnas obligatorias: `LapDistanceNorm`, `Speed`, `Throttle`, `Brake`,
`Time_seconds`, `Source`; sidecar `<nombre>.meta.json`). Los adaptadores NO
contienen lógica de análisis — eso vive en `f1core/prepare.py` y funciona
igual para cualquier fuente.

## Comandos habituales

```bash
# Dashboard (http://127.0.0.1:8050)
cd 01_TELEMETRY_F1/src && python dashboard.py

# Descargar dataset F1 (aparece solo en el dropdown del dashboard)
python prepare_data_set.py --year 2024 --gp Monza --session Q --drivers LEC NOR
python prepare_data_set.py --list-events 2025   # calendario / nombres de GP

# Validar un dataset propio
python -c "import sys; sys.path.insert(0,'.'); from f1core import load_dataset; load_dataset('ruta.csv')"
```

## Estado y pendientes

- El dataset `abu_dhabi_2021_comparison.csv` original no tiene X/Y; hay que
  regenerarlo una vez para habilitar el mapa de dominancia:
  `python prepare_data_set.py --year 2021 --gp "Abu Dhabi" --session Q --drivers HAM VER`
- Módulo `03` creado (2026-07-15): pipeline completo probado con demo
  sintética (`make_demo_data.py`, r≈0.99/gain≈1.15 esperados). Pendiente:
  (a) `geometry.json` tiene valores ESTIMADOS — medir el CAD de 02 cuando
  Roberto termine el diseño mecánico (sobre todo `motion_ratio`);
  (b) validar con captura real de AC (ACTI → MoTeC i2);
  (c) rellenar `[PENDIENTE]` en `03_KINEMATICS_F1/bmac_post.md` antes de
  publicar. Siguiente en roadmap: adaptador UDP para F1 24/25 de EA.
- Adaptador AC probado solo con CSV sintéticos; validar con un export real de
  MoTeC i2 (los nombres de canal pueden variar → `column_map`).
