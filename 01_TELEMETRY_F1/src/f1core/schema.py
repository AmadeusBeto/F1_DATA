"""
Schema canónico de telemetría.

¿Por qué un schema?
    Cada fuente (FastF1, Assetto Corsa, Forza, CSV manual) entrega columnas y
    unidades distintas. Definir UN formato interno significa que el dashboard,
    los reportes y los análisis funcionan igual sin importar de dónde vengan
    los datos. Todo adaptador debe terminar produciendo este formato.

Formato: "long" — una fila por muestra, una columna `Source` que identifica
al piloto / vuelta / configuración. Varias fuentes se apilan verticalmente.
"""

from __future__ import annotations

import json
import os
from glob import glob

import pandas as pd

# ---------------------------------------------------------------------------
# Definición del schema
# ---------------------------------------------------------------------------

#: Columnas obligatorias: sin ellas el dashboard no puede funcionar.
REQUIRED_COLUMNS: dict[str, str] = {
    "LapDistanceNorm": "Distancia recorrida en la vuelta, normalizada 0 → 1",
    "Speed":           "Velocidad en km/h",
    "Throttle":        "Acelerador en % (0–100)",
    "Brake":           "Freno: 0/1 (F1) o % (0–100) en simuladores",
    "Time_seconds":    "Tiempo transcurrido desde el inicio de la vuelta (s)",
    "Source":          "Etiqueta de la traza: piloto ('HAM'), o 'AC_SetupA'",
}

#: Columnas opcionales reconocidas: el dashboard las usa si existen.
OPTIONAL_COLUMNS: dict[str, str] = {
    "Distance":         "Distancia absoluta en metros",
    "RPM":              "Régimen del motor (rev/min)",
    "Gear":             "Marcha engranada (entero)",
    "DRS":              "Estado del DRS (código FastF1)",
    "SteerAngle":       "Ángulo de volante (grados, + = derecha)",
    "LongAccel":        "Aceleración longitudinal (g)",
    "LatAccel":         "Aceleración lateral (g)",
    "X":                "Posición X en pista (m) — para mapa de trazada",
    "Y":                "Posición Y en pista (m) — para mapa de trazada",
    "SuspTravel_FL":    "Recorrido de suspensión del. izq. (mm)",
    "SuspTravel_FR":    "Recorrido de suspensión del. der. (mm)",
    "SuspTravel_RL":    "Recorrido de suspensión tras. izq. (mm)",
    "SuspTravel_RR":    "Recorrido de suspensión tras. der. (mm)",
    "TyreTempC_FL":     "Temperatura neumático del. izq. (°C)",
    "TyreTempC_FR":     "Temperatura neumático del. der. (°C)",
    "TyreTempC_RL":     "Temperatura neumático tras. izq. (°C)",
    "TyreTempC_RR":     "Temperatura neumático tras. der. (°C)",
    "FuelLevel":        "Combustible restante (kg o L según fuente)",
}

#: Tipos de fuente aceptados en los metadatos.
SOURCE_TYPES = ("fastf1", "assetto_corsa", "forza", "custom")


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

def validate_dataset(df: pd.DataFrame, strict: bool = False) -> tuple[bool, list[str]]:
    """Valida un DataFrame contra el schema canónico.

    ¿Por qué validar? Detectar un dataset mal formado al cargarlo evita
    gráficos vacíos o deltas absurdos que son difíciles de depurar después.

    Args:
        df: DataFrame a validar.
        strict: si True, columnas desconocidas también generan aviso.

    Returns:
        (ok, issues) — ok es False solo ante errores (los avisos no bloquean).
    """
    issues: list[str] = []
    ok = True

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        ok = False
        issues.append(f"ERROR: faltan columnas obligatorias: {missing}")
        return ok, issues

    if df.empty:
        return False, ["ERROR: el dataset está vacío"]

    # Rangos físicos razonables --------------------------------------------
    checks = [
        ("LapDistanceNorm", 0.0, 1.001),
        ("Speed", 0.0, 420.0),
        ("Throttle", 0.0, 100.001),
        ("Brake", 0.0, 100.001),
    ]
    for col, lo, hi in checks:
        series = pd.to_numeric(df[col], errors="coerce")
        if series.isna().any():
            ok = False
            issues.append(f"ERROR: '{col}' contiene valores no numéricos/NaN")
            continue
        if series.min() < lo or series.max() > hi:
            ok = False
            issues.append(
                f"ERROR: '{col}' fuera de rango [{lo}, {hi}] "
                f"(min={series.min():.2f}, max={series.max():.2f})"
            )

    # Cada Source debe tener suficientes muestras y tiempo creciente --------
    for src, grp in df.groupby("Source"):
        if len(grp) < 50:
            issues.append(f"AVISO: '{src}' tiene solo {len(grp)} muestras (<50)")
        t = grp["Time_seconds"].values
        if (pd.Series(t).diff().dropna() < 0).any():
            ok = False
            issues.append(f"ERROR: 'Time_seconds' no es creciente para '{src}'")

    if strict:
        known = set(REQUIRED_COLUMNS) | set(OPTIONAL_COLUMNS) | {"Time_from_start"}
        unknown = [c for c in df.columns if c not in known]
        if unknown:
            issues.append(f"AVISO: columnas no reconocidas por el schema: {unknown}")

    return ok, issues


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

def load_dataset(path: str, validate: bool = True) -> pd.DataFrame:
    """Carga un CSV canónico y (opcionalmente) lo valida.

    Añade `Time_from_start` (tiempo relativo por Source) si no existe,
    porque el cálculo de delta lo necesita.
    """
    df = pd.read_csv(path)

    if validate:
        ok, issues = validate_dataset(df)
        for msg in issues:
            print(f"  [{os.path.basename(path)}] {msg}")
        if not ok:
            raise ValueError(f"Dataset inválido: {path}. Revisa los errores anteriores.")

    if "Time_from_start" not in df.columns:
        df["Time_from_start"] = df.groupby("Source")["Time_seconds"].transform(
            lambda x: x - x.min()
        )
    return df


def load_metadata(csv_path: str) -> dict:
    """Carga el JSON de metadatos asociado a un dataset (<nombre>.meta.json).

    Los metadatos guardan lo que el CSV no puede: evento, año, sesión,
    tipo de fuente y setup usado. Devuelve {} si no existe.
    """
    meta_path = os.path.splitext(csv_path)[0] + ".meta.json"
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_metadata(csv_path: str, metadata: dict) -> str:
    """Guarda el sidecar de metadatos junto al CSV."""
    meta_path = os.path.splitext(csv_path)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, ensure_ascii=False)
    return meta_path


def list_datasets(data_dir: str) -> list[dict]:
    """Encuentra todos los datasets compatibles en `data_dir` (recursivo).

    Un dataset es "compatible" si es un CSV con las columnas obligatorias.
    Devuelve [{path, name, meta}, ...] ordenado por nombre — es lo que
    alimenta el dropdown del dashboard.
    """
    results = []
    for path in sorted(glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)):
        if os.sep + "cache" + os.sep in path or "template" in path:
            continue
        try:
            head = pd.read_csv(path, nrows=5)
        except Exception:
            continue
        if all(c in head.columns for c in REQUIRED_COLUMNS):
            meta = load_metadata(path)
            name = meta.get("title") or os.path.splitext(os.path.basename(path))[0]
            results.append({"path": path, "name": name, "meta": meta})
    return results


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

def create_template(out_path: str, n_rows: int = 5) -> str:
    """Genera un CSV de ejemplo con todas las columnas del schema.

    Úsalo como punto de partida para preparar un dataset a mano o para
    mapear la salida de cualquier fuente nueva.
    """
    import numpy as np

    x = np.linspace(0, 1, n_rows)
    template = pd.DataFrame({
        "LapDistanceNorm": x.round(4),
        "Speed": (200 + 80 * np.sin(x * 6.28)).round(1),
        "Throttle": (50 + 50 * np.cos(x * 6.28)).round(1),
        "Brake": [0, 100, 0, 0, 0][:n_rows],
        "Time_seconds": (x * 90).round(3),
        "Source": "EXAMPLE",
        # Opcionales (déjalas vacías o elimínalas si no las tienes)
        "Distance": (x * 5281).round(1),
        "RPM": (9000 + 2000 * np.sin(x * 6.28)).round(0),
        "Gear": [7, 3, 5, 7, 8][:n_rows],
    })
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    template.to_csv(out_path, index=False)
    return out_path
