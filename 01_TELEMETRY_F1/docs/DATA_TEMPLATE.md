# Especificación del formato canónico de datos

Todo dataset del proyecto — venga de FastF1, Assetto Corsa, Forza o un CSV
hecho a mano — debe cumplir este formato. Es lo que permite que el dashboard,
los reportes y las funciones de análisis funcionen con cualquier fuente.

Template de ejemplo: [`data/template/telemetry_template.csv`](../data/template/telemetry_template.csv)
Generarlo por código: `f1core.schema.create_template("ruta.csv")`

---

## Formato general

- **CSV en formato "long"**: una fila por muestra de telemetría.
- Varias trazas (pilotos, vueltas, setups) se apilan verticalmente y se
  distinguen por la columna `Source`.
- Recomendado: ~1000 muestras por traza (usa `f1core.prepare.align_laps`).

## Columnas obligatorias (6)

| Columna | Unidad | Descripción |
|---|---|---|
| `LapDistanceNorm` | 0 → 1 | Distancia recorrida en la vuelta, normalizada. **La llave de alineación**: permite comparar vueltas punto a punto de pista |
| `Speed` | km/h | Velocidad |
| `Throttle` | % (0–100) | Posición del acelerador |
| `Brake` | 0/1 o % (0–100) | Freno. FastF1 solo da on/off; los sims dan presión en % |
| `Time_seconds` | s | Tiempo desde el inicio de la vuelta (creciente) |
| `Source` | texto | Etiqueta de la traza: `HAM`, `AC_SetupA`, `Yo_FM`... |

## Columnas opcionales (el dashboard las usa si existen)

| Columna | Unidad | Notas |
|---|---|---|
| `Distance` | m | Distancia absoluta |
| `RPM` | rev/min | Se grafica en vista Análisis |
| `Gear` | entero | Se grafica en vista Análisis. Se interpola por "vecino más cercano" |
| `DRS` | código | Solo F1 |
| `SteerAngle` | ° o % | + = derecha |
| `LongAccel`, `LatAccel` | g | Aceleraciones |
| `X`, `Y` | m | Posición en pista — habilitan el **mapa de dominancia** de la vista Presentación (los datasets de FastF1 las incluyen automáticamente; Forza también) |
| `SuspTravel_FL/FR/RL/RR` | mm | Recorrido de suspensión (sims) |
| `TyreTempC_FL/FR/RL/RR` | °C | Temperatura de neumáticos (sims) |
| `FuelLevel` | kg o L | Combustible restante |

## Metadatos (sidecar JSON)

Junto a cada CSV puede existir `<nombre>.meta.json` con lo que el CSV no
puede expresar:

```json
{
  "title": "Monza 2024 · Clasificación",
  "source_type": "fastf1",          // fastf1 | assetto_corsa | forza | custom
  "year": 2024,
  "event": "Monza",
  "session": "Q",
  "sources": ["LEC", "NOR"],
  "lap_times_s": {"LEC": 79.327, "NOR": 79.436},
  "n_points": 1000,
  "setup_id": null                  // enlaza con data/setups/<id>.json
}
```

El `title` es lo que muestra el dropdown del dashboard.

## Reglas de validación

`f1core.schema.validate_dataset(df)` comprueba:

1. Presencia de las 6 columnas obligatorias.
2. Rangos físicos: `LapDistanceNorm` ∈ [0,1], `Speed` ∈ [0,420],
   `Throttle`/`Brake` ∈ [0,100].
3. `Time_seconds` creciente dentro de cada `Source`.
4. Mínimo razonable de muestras por traza (aviso si <50).

Errores bloquean la carga; los avisos no.

## Checklist para preparar un dataset nuevo

1. Exporta/captura los datos de tu fuente.
2. Renombra columnas y convierte unidades al schema (o usa un adaptador de
   `f1core.adapters`).
3. Si no tienes `Distance`, intégrala: `dist = cumsum(speed_ms * dt)`.
4. Normaliza: `LapDistanceNorm = Distance / Distance.max()`.
5. Re-muestrea y apila trazas con `align_laps()` o `build_comparison()`.
6. Valida con `load_dataset()`.
7. Guarda CSV + `.meta.json` en `data/` → listo en el dashboard.
