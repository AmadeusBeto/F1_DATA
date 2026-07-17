"""
Preparación de datos: alineación, deltas y estadísticas.

El problema central de comparar vueltas:
    Cada fuente muestrea en instantes distintos. Para comparar dos trazas hay
    que re-muestrearlas sobre una MISMA malla de distancia normalizada (0→1).
    Una vez alineadas, "restar" curvas tiene sentido físico: en el mismo punto
    de la pista, ¿quién iba más rápido y cuánto tiempo llevaba acumulado?
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import OPTIONAL_COLUMNS

#: Columnas que se interpolan si existen (además de las obligatorias).
_INTERP_CANDIDATES = ["Speed", "Throttle", "Brake", "Time_seconds", "Distance",
                      "RPM", "SteerAngle", "LongAccel", "LatAccel",
                      "SuspTravel_FL", "SuspTravel_FR", "SuspTravel_RL", "SuspTravel_RR",
                      "TyreTempC_FL", "TyreTempC_FR", "TyreTempC_RL", "TyreTempC_RR",
                      "FuelLevel", "X", "Y"]

#: Columnas discretas: se interpolan con "vecino más cercano" (una marcha no
#: puede valer 5.5).
_NEAREST_COLS = ["Gear", "DRS"]


def align_laps(dfs: list[pd.DataFrame], n_points: int = 1000) -> pd.DataFrame:
    """Re-muestrea varias trazas sobre una malla común de LapDistanceNorm.

    ¿Por qué 1000 puntos? Balance entre resolución (~5 m por punto en un
    circuito de 5 km, suficiente para ver puntos de frenada) y fluidez del
    dashboard.

    Args:
        dfs: lista de DataFrames canónicos (uno por Source).
        n_points: puntos de la malla común.

    Returns:
        DataFrame apilado con todas las fuentes alineadas + Time_from_start.
    """
    grid = np.linspace(0, 1, n_points)
    aligned = []

    for df in dfs:
        df = df.sort_values("LapDistanceNorm")
        out = {"LapDistanceNorm": grid, "Source": df["Source"].iloc[0]}

        for col in _INTERP_CANDIDATES:
            if col in df.columns:
                out[col] = np.interp(grid, df["LapDistanceNorm"], df[col])

        for col in _NEAREST_COLS:
            if col in df.columns:
                idx = np.searchsorted(df["LapDistanceNorm"].values, grid).clip(
                    0, len(df) - 1)
                out[col] = df[col].values[idx]

        aligned.append(pd.DataFrame(out))

    combined = pd.concat(aligned, ignore_index=True)
    combined["Time_from_start"] = combined.groupby("Source")["Time_seconds"].transform(
        lambda x: x - x.min()
    )
    return combined


def compute_delta(df: pd.DataFrame, reference: str | None = None) -> pd.DataFrame:
    """Calcula el delta de tiempo acumulado de cada Source contra una referencia.

    Interpretación: delta > 0 en un punto significa que esa fuente llegó MÁS
    TARDE que la referencia a ese punto de la pista (va perdiendo tiempo).
    La pendiente del delta dice DÓNDE se gana/pierde: pendiente positiva =
    tramo donde la referencia es más rápida.

    Args:
        df: dataset alineado (salida de align_laps).
        reference: Source de referencia; por defecto la primera.

    Returns:
        DataFrame wide: LapDistanceNorm + una columna Delta_<source> por fuente.
    """
    sources = list(df["Source"].unique())
    if reference is None:
        reference = sources[0]

    ref = df[df["Source"] == reference].sort_values("LapDistanceNorm")
    out = pd.DataFrame({"LapDistanceNorm": ref["LapDistanceNorm"].values})

    for src in sources:
        if src == reference:
            continue
        other = df[df["Source"] == src].sort_values("LapDistanceNorm")
        out[f"Delta_{src}"] = (
            other["Time_from_start"].values - ref["Time_from_start"].values
        )
    out.attrs["reference"] = reference
    return out


def summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Estadísticas resumen por Source — la base de los reportes.

    Métricas y su porqué:
        LapTime_s        → resultado final.
        VMax_kmh / VMin  → capacidad en recta / velocidad mínima en curva lenta.
        AvgSpeed_kmh     → ritmo global.
        FullThrottle_pct → % de vuelta a fondo: proxy de confianza + motor.
        Braking_pct      → % de vuelta frenando: estilo y eficiencia de frenada.
        Coasting_pct     → ni gas ni freno: normalmente tiempo perdido.
    """
    rows = []
    for src, g in df.groupby("Source"):
        throttle_full = (g["Throttle"] >= 98).mean() * 100
        braking = (g["Brake"] > 0).mean() * 100
        coasting = ((g["Throttle"] < 5) & (g["Brake"] == 0)).mean() * 100
        row = {
            "Source": src,
            "LapTime_s": round(g["Time_from_start"].max(), 3),
            "VMax_kmh": round(g["Speed"].max(), 1),
            "VMin_kmh": round(g["Speed"].min(), 1),
            "AvgSpeed_kmh": round(g["Speed"].mean(), 1),
            "FullThrottle_pct": round(throttle_full, 1),
            "Braking_pct": round(braking, 1),
            "Coasting_pct": round(coasting, 1),
        }
        if "RPM" in g.columns:
            row["MaxRPM"] = round(g["RPM"].max(), 0)
        if "Gear" in g.columns:
            row["TopGear"] = int(g["Gear"].max())
        rows.append(row)
    return pd.DataFrame(rows).sort_values("LapTime_s").reset_index(drop=True)


def sector_deltas(df: pd.DataFrame, n_sectors: int = 3,
                  reference: str | None = None) -> pd.DataFrame:
    """Divide la vuelta en mini-sectores y calcula el delta por sector.

    ¿Por qué? El delta acumulado dice el resultado; los mini-sectores dicen
    EN QUÉ PARTE de la pista se construye la diferencia (curvas lentas,
    rectas, sectores revirados...).
    """
    delta = compute_delta(df, reference)
    reference = delta.attrs["reference"]
    edges = np.linspace(0, 1, n_sectors + 1)

    rows = []
    for i in range(n_sectors):
        lo, hi = edges[i], edges[i + 1]
        mask = (delta["LapDistanceNorm"] >= lo) & (delta["LapDistanceNorm"] <= hi)
        seg = delta[mask]
        row = {"Sector": i + 1, "Range": f"{lo:.2f}–{hi:.2f}"}
        for col in delta.columns:
            if col.startswith("Delta_"):
                # Ganancia del sector = delta al final - delta al inicio
                row[col.replace("Delta_", "") + f"_vs_{reference}_s"] = round(
                    seg[col].iloc[-1] - seg[col].iloc[0], 3)
        rows.append(row)
    return pd.DataFrame(rows)


def build_comparison(csv_paths: list[str], labels: list[str] | None = None,
                     n_points: int = 1000, out_path: str | None = None) -> pd.DataFrame:
    """Combina varios CSV canónicos individuales en un dataset de comparación.

    Útil para mezclar fuentes: p. ej. tu vuelta en Assetto Corsa contra la
    vuelta real de Hamilton, o dos setups distintos del mismo coche.
    """
    dfs = []
    for i, path in enumerate(csv_paths):
        df = pd.read_csv(path)
        if labels and i < len(labels):
            df["Source"] = labels[i]
        dfs.append(df)

    combined = align_laps(dfs, n_points=n_points)
    if out_path:
        combined.to_csv(out_path, index=False)
        print(f"[OK] Comparación guardada: {out_path}")
    return combined
