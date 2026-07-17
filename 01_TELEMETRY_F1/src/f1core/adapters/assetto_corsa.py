"""
Adaptador de Assetto Corsa → schema canónico.

Ruta recomendada para sacar telemetría de AC:
    1. Instalar ACTI (Assetto Corsa Telemetry Interface) — graba en formato
       MoTeC (.ld/.ldx) mientras conduces.
    2. Abrir en MoTeC i2 Pro y exportar la vuelta como CSV
       (File → Export Data → CSV, con canal Distance activado).
    3. Llamar a from_motec_csv() con ese archivo.

Alternativa sin MoTeC: cualquier app de AC que exporte CSV con columnas de
tiempo/velocidad/pedales sirve — usa from_generic_csv() con tu column_map.

¿Por qué pasar por distancia normalizada?
    Igual que con FastF1: la única forma justa de comparar dos vueltas es
    punto a punto de la pista, no segundo a segundo.
"""

from __future__ import annotations

import io
import os

import numpy as np
import pandas as pd

#: Mapa por defecto: nombre de canal MoTeC/ACTI → columna canónica.
DEFAULT_COLUMN_MAP = {
    "Time": "Time_seconds",
    "Distance": "Distance",
    "Ground Speed": "Speed",
    "Throttle Pos": "Throttle",
    "Brake Pos": "Brake",
    "Engine RPM": "RPM",
    "Gear": "Gear",
    "Steered Angle": "SteerAngle",
    "G Force Long": "LongAccel",
    "G Force Lat": "LatAccel",
    "Susp Pos FL": "SuspTravel_FL",
    "Susp Pos FR": "SuspTravel_FR",
    "Susp Pos RL": "SuspTravel_RL",
    "Susp Pos RR": "SuspTravel_RR",
    "Tyre Temp Core FL": "TyreTempC_FL",
    "Tyre Temp Core FR": "TyreTempC_FR",
    "Tyre Temp Core RL": "TyreTempC_RL",
    "Tyre Temp Core RR": "TyreTempC_RR",
    "Fuel Level": "FuelLevel",
}


def from_motec_csv(path: str, source_label: str = "AC",
                   column_map: dict | None = None,
                   speed_unit: str = "kmh") -> pd.DataFrame:
    """Convierte un CSV exportado de MoTeC i2 al schema canónico.

    Los CSV de MoTeC llevan varias filas de metadatos antes de la cabecera
    real y una fila de unidades después; esta función las detecta y las salta.

    Args:
        path: CSV exportado de MoTeC i2.
        source_label: etiqueta para la columna Source (p. ej. 'AC_SetupA').
        column_map: sobreescribe DEFAULT_COLUMN_MAP si tus canales se llaman
            distinto (idioma, versión de ACTI...).
        speed_unit: 'kmh', 'ms' (m/s) o 'mph' según la unidad exportada.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    cmap = column_map or DEFAULT_COLUMN_MAP

    # Detectar la fila de cabecera: la primera que contiene 'Time'
    header_idx = next(
        (i for i, ln in enumerate(lines)
         if "Time" in ln and ("," in ln or ";" in ln)),
        0,
    )
    sep = ";" if lines[header_idx].count(";") > lines[header_idx].count(",") else ","

    df = pd.read_csv(io.StringIO("".join(lines[header_idx:])), sep=sep)
    df.columns = [c.strip().strip('"') for c in df.columns]

    # Fila de unidades justo bajo la cabecera (valores tipo 's', 'km/h')
    if not _is_number(df.iloc[0].get("Time", df.iloc[0, 0])):
        df = df.iloc[1:].reset_index(drop=True)
    df = df.apply(pd.to_numeric, errors="coerce")

    return _finalize(df.rename(columns=cmap), source_label, speed_unit)


def from_generic_csv(path: str, column_map: dict, source_label: str = "AC",
                     speed_unit: str = "kmh") -> pd.DataFrame:
    """Convierte cualquier CSV de telemetría con un mapa de columnas explícito.

    column_map: {nombre_en_tu_csv: nombre_canonico}. Mínimo necesitas mapear
    Time_seconds, Speed, Throttle y Brake, más Distance (o se integra desde
    la velocidad).
    """
    df = pd.read_csv(path).rename(columns=column_map)
    return _finalize(df, source_label, speed_unit)


# ---------------------------------------------------------------------------
# Internos
# ---------------------------------------------------------------------------

def _finalize(df: pd.DataFrame, source_label: str, speed_unit: str) -> pd.DataFrame:
    """Normaliza unidades, recorta a una vuelta y añade LapDistanceNorm."""
    keep = [c for c in df.columns if c in {
        "Time_seconds", "Distance", "Speed", "Throttle", "Brake", "RPM", "Gear",
        "SteerAngle", "LongAccel", "LatAccel", "FuelLevel",
        "SuspTravel_FL", "SuspTravel_FR", "SuspTravel_RL", "SuspTravel_RR",
        "TyreTempC_FL", "TyreTempC_FR", "TyreTempC_RL", "TyreTempC_RR",
    }]
    df = df[keep].dropna(subset=["Time_seconds", "Speed"]).reset_index(drop=True)

    # Unidades ---------------------------------------------------------------
    if speed_unit == "ms":
        df["Speed"] = df["Speed"] * 3.6
    elif speed_unit == "mph":
        df["Speed"] = df["Speed"] * 1.60934

    # Pedales: ACTI exporta 0–1 o 0–100 según canal → normalizamos a 0–100
    for col in ("Throttle", "Brake"):
        if col in df.columns and df[col].max() <= 1.001:
            df[col] = df[col] * 100

    # Distancia: si no viene, la integramos desde la velocidad (v·dt)
    if "Distance" not in df.columns:
        dt = df["Time_seconds"].diff().fillna(0)
        df["Distance"] = (df["Speed"] / 3.6 * dt).cumsum()

    df["Time_seconds"] = df["Time_seconds"] - df["Time_seconds"].min()
    df["Distance"] = df["Distance"] - df["Distance"].min()
    df["LapDistanceNorm"] = df["Distance"] / df["Distance"].max()
    df["Source"] = source_label

    if "Throttle" not in df.columns:
        df["Throttle"] = 0.0
    if "Brake" not in df.columns:
        df["Brake"] = 0.0
    return df


def _is_number(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def save_canonical(df: pd.DataFrame, out_dir: str, name: str) -> str:
    """Guarda la traza canónica en data/sim/ lista para build_comparison()."""
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{name}.csv")
    df.to_csv(out_path, index=False)
    print(f"[OK] Telemetría AC guardada: {out_path}")
    return out_path
