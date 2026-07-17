"""
Descarga de datos oficiales de F1 vía FastF1.

¿Por qué FastF1?
    Es la única fuente pública con telemetría real de F1 (velocidad, acelerador,
    freno, RPM, marcha, DRS) sincronizada con tiempos oficiales. La telemetría
    viene de la transmisión de datos en vivo de la FOM, muestreada a ~4-5 Hz.

Flujo típico:
    download_session()        → carga una sesión completa (con caché local)
    get_fastest_lap_telemetry() → telemetría canónica de la vuelta rápida
    download_comparison()     → hace todo: descarga N pilotos, alinea y guarda
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .schema import save_metadata
from .prepare import align_laps

#: Columnas FastF1 → columnas canónicas (las que existan se copian).
_FASTF1_OPTIONAL_MAP = {
    "RPM": "RPM",
    "nGear": "Gear",
    "DRS": "DRS",
}


def enable_cache(cache_dir: str) -> None:
    """Activa la caché de FastF1.

    ¿Por qué? La API tarda minutos en bajar una sesión; con caché la segunda
    carga es casi instantánea y no castigas los servidores.
    """
    import fastf1

    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)


def download_session(year: int, gp: str, session_type: str = "Q",
                     cache_dir: str | None = None):
    """Descarga y carga una sesión de F1.

    Args:
        year: temporada, p. ej. 2021.
        gp: nombre del GP, p. ej. 'Abu Dhabi', 'Monza', o número de ronda.
        session_type: 'FP1', 'FP2', 'FP3', 'Q', 'SQ', 'S' (sprint), 'R' (carrera).
        cache_dir: carpeta de caché; por defecto '../data/cache'.
    """
    import fastf1

    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")
    enable_cache(cache_dir)

    session = fastf1.get_session(year, gp, session_type)
    session.load()
    return session


def get_fastest_lap_telemetry(session, driver: str) -> pd.DataFrame:
    """Extrae la telemetría de la vuelta más rápida de un piloto en formato canónico.

    Pasos (y por qué):
        1. pick_fastest(): comparamos siempre la mejor vuelta de cada piloto,
           es la comparación más justa en clasificación.
        2. get_telemetry(): fusiona datos de coche (velocidad, pedales) con
           datos de POSICIÓN (X, Y) — las coordenadas permiten dibujar el
           mapa de pista y el mapa de dominancia del dashboard.
        3. add_distance(): integra la velocidad para obtener distancia — la
           clave para comparar pilotos es alinear por DISTANCIA, no por tiempo
           (dos pilotos pasan por el mismo punto en momentos distintos).
        4. Normalizamos la distancia 0→1 para que vueltas con medición
           ligeramente distinta de longitud sean comparables.
    """
    laps = session.laps.pick_drivers(driver) if hasattr(session.laps, "pick_drivers") \
        else session.laps.pick_driver(driver)
    lap = laps.pick_fastest()
    try:
        # Telemetría completa: incluye X, Y (décimas de metro)
        tel = lap.get_telemetry()
        if "Distance" not in tel.columns:
            tel = tel.add_distance()
    except Exception:
        # Fallback sin datos de posición (el mapa de pista no estará disponible)
        tel = lap.get_car_data().add_distance()

    out = pd.DataFrame({
        "LapDistanceNorm": tel["Distance"] / tel["Distance"].max(),
        "Speed": tel["Speed"],
        "Throttle": tel["Throttle"],
        "Brake": tel["Brake"].astype(float),
        "Time_seconds": tel["Time"].dt.total_seconds(),
        "Source": driver,
        "Distance": tel["Distance"],
    })
    # FastF1 entrega Brake como bool o numérico 0/1 según versión;
    # escalamos a 0–100 para consistencia con los sims (igual que en adapters)
    if out["Brake"].max() <= 1.001:
        out["Brake"] = out["Brake"] * 100.0
    out["Brake"] = out["Brake"].clip(0, 100)

    for src_col, dst_col in _FASTF1_OPTIONAL_MAP.items():
        if src_col in tel.columns:
            out[dst_col] = tel[src_col].values

    # Coordenadas de pista: FastF1 las da en décimas de metro → metros
    if "X" in tel.columns and "Y" in tel.columns:
        out["X"] = tel["X"].values / 10.0
        out["Y"] = tel["Y"].values / 10.0

    return out


def download_comparison(year: int, gp: str, session_type: str = "Q",
                        drivers: list[str] = ("HAM", "VER"),
                        n_points: int = 1000,
                        data_dir: str | None = None) -> str:
    """Pipeline completo: descarga, convierte, alinea y guarda un dataset.

    Genera:
        <gp>_<año>_<piloto>.csv        → telemetría cruda canónica por piloto
        <gp>_<año>_comparison.csv      → dataset alineado (n_points por piloto)
        <gp>_<año>_comparison.meta.json → metadatos (evento, sesión, pilotos)

    Returns:
        Ruta del CSV de comparación (lo que consume el dashboard).
    """
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    session = download_session(year, gp, session_type)
    slug = f"{gp.lower().replace(' ', '_')}_{year}"

    raw_dfs = []
    lap_times = {}
    for driver in drivers:
        try:
            tel = get_fastest_lap_telemetry(session, driver)
        except Exception as exc:
            print(f"[ERROR] {driver}: {exc}")
            continue
        raw_dfs.append(tel)
        lap_times[driver] = float(tel["Time_seconds"].max() - tel["Time_seconds"].min())

        raw_path = os.path.join(data_dir, f"{slug}_{driver.lower()}.csv")
        tel.to_csv(raw_path, index=False)
        print(f"[OK] {driver}: {raw_path} (vuelta: {lap_times[driver]:.3f}s)")

    if not raw_dfs:
        raise RuntimeError("No se pudo descargar telemetría de ningún piloto.")

    combined = align_laps(raw_dfs, n_points=n_points)
    out_path = os.path.join(data_dir, f"{slug}_comparison.csv")
    combined.to_csv(out_path, index=False)

    save_metadata(out_path, {
        "title": f"{gp} {year} · {_session_name(session_type)}",
        "source_type": "fastf1",
        "year": year,
        "event": gp,
        "session": session_type,
        "sources": list(lap_times.keys()),
        "lap_times_s": {k: round(v, 3) for k, v in lap_times.items()},
        "n_points": n_points,
        "setup_id": None,
    })
    print(f"[OK] Dataset combinado: {out_path}")
    return out_path


def _session_name(code: str) -> str:
    return {
        "FP1": "Práctica 1", "FP2": "Práctica 2", "FP3": "Práctica 3",
        "Q": "Clasificación", "SQ": "Sprint Qualy", "S": "Sprint", "R": "Carrera",
    }.get(code, code)


def list_available_events(year: int) -> pd.DataFrame:
    """Devuelve el calendario de un año — útil para saber qué nombres de GP usar."""
    import fastf1

    schedule = fastf1.get_event_schedule(year)
    return schedule[["RoundNumber", "EventName", "Location", "EventDate"]]
