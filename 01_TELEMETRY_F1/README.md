# 🏎️ F1 Telemetry Lab

Plataforma de análisis de telemetría multi-fuente: datos oficiales de F1
(FastF1), simuladores (Assetto Corsa, Forza) y CSV propios — todo bajo un
mismo formato de datos y un mismo dashboard.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Dash](https://img.shields.io/badge/dashboard-Dash%2FPlotly-red)
![Data](https://img.shields.io/badge/data-FastF1%20%7C%20AC%20%7C%20Forza-green)

---

## Estructura del proyecto

```
01_TELEMETRY_F1/
├── data/
│   ├── template/                 ← Templates: telemetría CSV y setup JSON
│   ├── setups/                   ← Configuraciones de vehículo (JSON)
│   ├── sim/                      ← Telemetría de simuladores (canónica)
│   ├── cache/                    ← Caché de FastF1 (auto, ignorada en git)
│   └── *_comparison.csv          ← Datasets listos para el dashboard
├── docs/
│   ├── DATA_TEMPLATE.md          ← Especificación del formato canónico
│   └── SIM_TELEMETRY.md          ← Cómo meter telemetría de AC / Forza + setups
├── notebooks/                    ← Exploración y validación
├── reports/                      ← Reportes HTML exportados desde el dashboard
└── src/
    ├── dashboard.py              ← Dashboard (vistas Presentación / Análisis)
    ├── prepare_data_set.py       ← CLI de descarga y preparación
    └── f1core/                   ← Núcleo reutilizable
        ├── schema.py             ← Formato canónico, validación, carga
        ├── download.py           ← Descarga FastF1
        ├── prepare.py            ← Alineación, deltas, estadísticas
        ├── setups.py             ← Carga y comparación de setups
        └── adapters/
            ├── assetto_corsa.py  ← MoTeC/ACTI CSV → canónico
            └── forza.py          ← UDP "Data Out" → canónico
```

---

## Instalación

```bash
python -m venv f1_env

# Windows
.\f1_env\Scripts\activate
# Linux / macOS
source f1_env/bin/activate

pip install -r requirements.txt
```

---

## Uso del dashboard

```bash
cd 01_TELEMETRY_F1/src
python dashboard.py
```

Abre **http://127.0.0.1:8050**. El dropdown superior lista automáticamente
todos los datasets compatibles que encuentre en `data/`.

### Las dos vistas

| Vista | Para qué | Qué contiene |
|---|---|---|
| **🎙 Presentación** | Mostrar resultados a otras personas | Tarjetas de resumen, **mapa de dominancia** (el trazado de la pista coloreado según quién es más rápido en cada punto), un gráfico protagonista (velocidad / delta / pedales) y **conclusiones automáticas** en lenguaje natural |
| **🔬 Análisis** | Trabajar los datos y generar reportes | Todas las trazas (velocidad, pedales, RPM, marchas), delta con **referencia seleccionable**, **mini-sectores** (3–20), tabla de estadísticas y botones de **exportación** |

### Exportar reportes (vista Análisis)

- **Reporte HTML**: documento autocontenido con tablas y gráficos interactivos.
  Se descarga y además se guarda una copia en `reports/`.
- **Resumen CSV**: tabla de estadísticas por traza, lista para Excel.

---

## Descargar nuevos datasets de F1

```bash
cd src

# Ver el calendario de un año (nombres exactos de GP)
python prepare_data_set.py --list-events 2025

# Descargar cualquier sesión y pilotos
python prepare_data_set.py --year 2024 --gp Monza --session Q --drivers LEC NOR
python prepare_data_set.py --year 2025 --gp "Sao Paulo" --session R --drivers VER NOR PIA
```

Sesiones: `FP1` `FP2` `FP3` `Q` `SQ` (sprint qualy) `S` (sprint) `R` (carrera).
El resultado aparece automáticamente en el dropdown del dashboard.

También puedes usar las funciones desde Python / notebooks:

```python
from f1core.download import download_comparison
from f1core.prepare import build_comparison, summary_stats

# Descarga completa
download_comparison(2024, "Monza", "Q", drivers=["LEC", "NOR"])

# Mezclar fuentes: tu vuelta en un sim vs la vuelta real
build_comparison(
    ["../data/monza_2024_lec.csv", "../data/sim/ac_monza_myLap.csv"],
    labels=["LEC (real)", "Yo (AC)"],
    out_path="../data/real_vs_sim_monza_comparison.csv",
)
```

---

## Preparar un dataset propio (cualquier fuente)

1. Copia `data/template/telemetry_template.csv` y estudia sus columnas.
2. Rellena al menos las **6 columnas obligatorias** (ver
   [`docs/DATA_TEMPLATE.md`](docs/DATA_TEMPLATE.md)).
3. Valida:

```python
from f1core import load_dataset
df = load_dataset("mi_dataset.csv")   # imprime errores/avisos si los hay
```

4. Guárdalo en `data/` → aparecerá en el dashboard.

---

## Telemetría de simuladores y setups

Guía completa en [`docs/SIM_TELEMETRY.md`](docs/SIM_TELEMETRY.md):
captura desde **Assetto Corsa** (ACTI/MoTeC) y **Forza** (Data Out UDP),
y el formato JSON de **setups de vehículo** para correlacionar cambios
mecánicos con cambios de comportamiento en pista.

```python
# Forza: capturar, extraer vuelta y convertir
from f1core.adapters import forza
raw = forza.capture_udp(port=5300, duration_s=300, out_csv="../data/sim/raw_session.csv")
lap = forza.extract_lap(raw)                      # vuelta más rápida
df  = forza.to_canonical(lap, "FM_SetupA")
forza.save_canonical(df, "../data/sim", "fm_spa_setupA")

# Assetto Corsa: desde export de MoTeC i2
from f1core.adapters import assetto_corsa as ac
df = ac.from_motec_csv("export_spa.csv", source_label="AC_SetupB")
ac.save_canonical(df, "../data/sim", "ac_spa_setupB")

# Comparar setups
from f1core import load_setup, compare_setups
diff = compare_setups(load_setup("../data/setups/a.json"),
                      load_setup("../data/setups/b.json"))
```

---

## ¿Qué se analiza y por qué?

- **Alineación por distancia (no por tiempo)**: dos vueltas se comparan punto
  a punto de la pista; comparar por tiempo mezcla lugares distintos.
- **Delta acumulado**: el resultado (quién gana y cuánto). Su **pendiente**
  dice dónde: pendiente positiva = tramo donde la referencia es más rápida.
- **Mini-sectores**: cuantifican en qué zona (curva lenta, recta, sector
  revirado) se construye la diferencia.
- **% a fondo / % frenando / % coasting**: huellas del estilo de pilotaje y
  de la confianza en el coche. El coasting suele ser tiempo perdido.

---

## Caso de estudio incluido

**Abu Dhabi 2021 · Clasificación — Hamilton vs Verstappen** (la pole de la
final más polémica de la era híbrida). Dataset: `abu_dhabi_2021_comparison.csv`.
