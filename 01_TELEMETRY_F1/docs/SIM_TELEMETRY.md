# Telemetría de simuladores y setups de vehículo

Propuesta de arquitectura para integrar sim racing al proyecto. La idea
central: **cada sim tiene su adaptador; todos desembocan en el schema
canónico** (ver [DATA_TEMPLATE.md](DATA_TEMPLATE.md)). A partir de ahí,
dashboard, deltas y reportes funcionan igual que con datos reales de F1.

```
Assetto Corsa ──(ACTI → MoTeC CSV)──► adapters/assetto_corsa.py ─┐
Forza M/H ──────(Data Out UDP)──────► adapters/forza.py ─────────┼─► schema canónico ─► dashboard
FastF1 ─────────(API oficial)───────► download.py ───────────────┘        + setups.json
```

---

## 1. Assetto Corsa (recomendado para análisis serio)

AC es el sim con física más "analizable" y el ecosistema de telemetría más
maduro. Ruta recomendada:

1. **Instala ACTI** (Assetto Corsa Telemetry Interface). Graba tus sesiones
   en formato MoTeC (`.ld/.ldx`).
2. **Abre en MoTeC i2 Pro** (gratis para uso personal) — ya de por sí es una
   herramienta profesional que usan equipos reales.
3. **Exporta la vuelta como CSV**: File → Export Data → CSV (incluye el canal
   *Distance*).
4. Convierte:

```python
from f1core.adapters import assetto_corsa as ac
df = ac.from_motec_csv("spa_lap12.csv", source_label="AC_Baseline")
ac.save_canonical(df, "../data/sim", "ac_spa_baseline")
```

Si tus canales tienen otros nombres (idioma/versión), pasa tu propio
`column_map`. Para CSV de cualquier otra app de AC usa
`ac.from_generic_csv(path, column_map={...})`.

**Qué canales capturar** (además de los básicos): recorrido de suspensión
por rueda, temperaturas de neumático, G lat/long y ángulo de volante — son
los que conectan telemetría con setup.

## 2. Forza Motorsport / Forza Horizon

Forza tiene salida de telemetría **nativa** ("Data Out"): transmite un
paquete UDP binario a ~60 Hz. Sin mods.

1. En el juego: Ajustes → HUD → **Salida de datos** → ON, IP de tu PC
   (127.0.0.1 si es el mismo), puerto 5300.
2. Captura ANTES de rodar:

```python
from f1core.adapters import forza
raw = forza.capture_udp(port=5300, duration_s=300,
                        out_csv="../data/sim/raw_fm_spa.csv")
lap = forza.extract_lap(raw)               # vuelta más rápida detectada
df  = forza.to_canonical(lap, "FM_SetupA")
forza.save_canonical(df, "../data/sim", "fm_spa_setupA")
```

El parser detecta el juego por el tamaño del paquete: FM7 Dash (311 B),
FH4/FH5 (324 B), Forza Motorsport 2023 (331 B).

**Limitación de Horizon**: en mundo abierto no hay concepto de vuelta —
usa carreras con vueltas, o recorta manualmente por `DistanceTraveled`.
Para análisis comparable, **Motorsport > Horizon** (Horizon es arcade:
su física de suspensión/neumático es menos transferible).

## 3. Otros sims (futuro)

| Sim | Vía de captura | Esfuerzo |
|---|---|---|
| **ACC** | Shared memory (`pyaccsharedmemory`) o broadcast UDP | Medio |
| **iRacing** | SDK oficial (`pyirsdk`) — telemetría .ibt muy completa | Medio |
| **F1 2x (Codemasters/EA)** | UDP documentado oficialmente, muy rico | Bajo — buen candidato al siguiente adaptador |
| **rFactor 2 / LMU** | Plugin shared memory | Medio |

Todos siguen el mismo patrón: capturar → traducir columnas/unidades →
`save_canonical()`.

---

## 4. Setups de vehículo

**Por qué**: la telemetría dice *qué hace* el coche; el setup dice *cómo está
construido* ese comportamiento. Guardando ambos puedes responder preguntas de
ingeniería: *"¿qué le hizo a mi punto de frenada bajar 2 clicks el ala
trasera?"*

### Estructura

Un JSON por setup en `data/setups/`, siguiendo
[`data/template/setup_template.json`](../data/template/setup_template.json):

- `meta` (obligatoria): `setup_id`, `car`, `sim`, `track`, `date`, `notes`.
- `aero`: alerones, alturas.
- `suspension`: muelles, barras, amortiguadores, camber, toe.
- `tyres`: compuesto y presiones.
- `brakes`, `differential`, `gearing`, `fuel`.

Solo `meta` es obligatoria — cada sim expone parámetros distintos y un setup
parcial sigue siendo útil.

### Flujo de trabajo A/B

1. Guarda `spa_baseline.json`, rueda 3-5 vueltas, exporta la mejor con
   `source_label="Baseline"`.
2. **Cambia UN parámetro** (si cambias dos, no sabrás cuál causó el efecto),
   guarda `spa_wing_low.json`, rueda y exporta como `"WingLow"`.
3. Combina y analiza:

```python
from f1core.prepare import build_comparison
from f1core import load_setup, compare_setups

build_comparison(
    ["../data/sim/ac_spa_baseline.csv", "../data/sim/ac_spa_winglow.csv"],
    out_path="../data/sim/spa_setup_ab_comparison.csv",
)
diff = compare_setups(load_setup("../data/setups/spa_baseline.json"),
                      load_setup("../data/setups/spa_wing_low.json"))
```

4. En el dashboard: mini-sectores para ver dónde gana cada setup (menos ala =
   ganas en rectas / pierdes en el sector 2 revirado) y las trazas de
   suspensión/temperaturas para explicar el porqué mecánico.

El campo `setup_id` del `.meta.json` del dataset enlaza cada traza con su
setup — así el reporte puede incluir la tabla de diferencias mecánicas.
