"""
Generador de vuelta sintética — SOLO para probar el pipeline.

IMPORTANTE: esto NO valida nada físicamente. La "medición" se fabrica con el
propio modelo (más ruido y una ganancia conocida), así que el resultado
esperado está predeterminado. Su única función es comprobar que toda la
cadena (CSV canónico → predicción → métricas → reporte) corre sin errores,
ANTES de tener capturas reales de Assetto Corsa.

¿Por qué introducir ganancia 1.15 y ruido a propósito?
    Para verificar que las métricas detectan lo que deben: la validación
    debería reportar r ≈ 0.99 y gain ≈ 1.15 — si no, el bug está en nuestro
    código, no en los datos.

Uso:
    python make_demo_data.py                    # escribe en ../data/
    python make_demo_data.py --to-dashboard     # copia también a 01_.../data/sim/
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from quarter_car import load_geometry, predict_front_travel

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "..", "data")
DASHBOARD_SIM_DIR = os.path.join(BASE, "..", "..", "01_TELEMETRY_F1", "data", "sim")

RNG = np.random.default_rng(42)  # reproducible: mismos "datos" en cada corrida


def synthetic_lap(lap_time: float = 90.0, hz: float = 20.0) -> pd.DataFrame:
    """Vuelta artificial de ~90 s con 6 curvas.

    La velocidad se construye como una recta base con "valles" gaussianos en
    las curvas; de ahí salen aceleraciones coherentes entre sí:
        ax = dv/dt  ·  ay = v²·curvatura (con signo alternado por curva)
    Esa coherencia interna importa: el modelo cuasi-estático combina Speed,
    LongAccel y LatAccel, y con señales incoherentes la demo no probaría nada.
    """
    n = int(lap_time * hz)
    t = np.linspace(0, lap_time, n)
    s = t / lap_time                                   # distancia normalizada aprox.

    # Curvas: (posición en vuelta, severidad km/h, ancho, sentido)
    corners = [(0.10, 180, 0.030, +1), (0.25, 120, 0.025, -1),
               (0.45, 220, 0.020, +1), (0.60, 100, 0.035, +1),
               (0.78, 150, 0.025, -1), (0.92, 200, 0.020, -1)]

    v_kmh = np.full(n, 320.0)
    curvature_signed = np.zeros(n)
    for pos, drop, width, sign in corners:
        bump = drop * np.exp(-((s - pos) / width) ** 2)
        v_kmh -= bump
        curvature_signed += sign * bump

    v = v_kmh / 3.6
    ax = np.gradient(v, t) / 9.81                      # g
    # Escala de curvatura elegida para ay pico ~4.5 g (orden F1)
    ay = curvature_signed / curvature_signed.max() * 4.5 * (v / v.max()) ** 2

    throttle = np.clip(50 + 60 * np.clip(ax, 0, None) * 3, 0, 100)
    throttle[v_kmh > 310] = 100
    brake = np.clip(-ax * 60, 0, 100)

    return pd.DataFrame({
        "LapDistanceNorm": s.round(5),
        "Speed": v_kmh.round(2),
        "Throttle": throttle.round(1),
        "Brake": brake.round(1),
        "Time_seconds": t.round(4),
        "Source": "AC_DEMO_SYNTH",
        "LongAccel": ax.round(4),
        "LatAccel": ay.round(4),
    })


def add_fake_measurement(df: pd.DataFrame, geo: dict,
                         gain: float = 1.15, noise_mm: float = 0.4) -> pd.DataFrame:
    """Fabrica los canales SuspTravel_* que "mediría" el sensor:
    predicción del modelo × ganancia conocida + ruido + offset arbitrario."""
    pred = predict_front_travel(df, geo)
    for corner in ("FL", "FR"):
        df[f"SuspTravel_{corner}"] = (
            pred[f"PredTravel_{corner}"] * gain
            + RNG.normal(0, noise_mm, len(df))
            + 25.0                                     # offset de montaje del pot
        ).round(3)
    # Traseros: copia atenuada, solo para que el dashboard pinte 4 esquinas
    df["SuspTravel_RL"] = (df["SuspTravel_FL"] * 0.8).round(3)
    df["SuspTravel_RR"] = (df["SuspTravel_FR"] * 0.8).round(3)
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--to-dashboard", action="store_true",
                    help="copiar también a 01_TELEMETRY_F1/data/sim/")
    args = ap.parse_args()

    geo = load_geometry()
    df = add_fake_measurement(synthetic_lap(), geo)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "demo_synthetic_lap.csv")
    df.to_csv(path, index=False)
    meta = {"title": "DEMO sintética — prueba de pipeline (NO son datos reales)",
            "source_type": "custom", "synthetic": True,
            "expected": {"r": "≈0.99", "gain": "≈1.15"}}
    with open(os.path.splitext(path)[0] + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    print(f"[OK] {os.path.abspath(path)}")
    print(f"     Esperado al validar: r ~ 0.99, gain ~ 1.15")

    if args.to_dashboard:
        os.makedirs(DASHBOARD_SIM_DIR, exist_ok=True)
        dst = os.path.join(DASHBOARD_SIM_DIR, "demo_synthetic_lap.csv")
        df.to_csv(dst, index=False)
        with open(os.path.splitext(dst)[0] + ".meta.json", "w",
                  encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
        print(f"[OK] Copiado al dashboard: {os.path.abspath(dst)}")


if __name__ == "__main__":
    main()
