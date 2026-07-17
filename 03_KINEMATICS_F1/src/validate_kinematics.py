"""
Validación cinemática: modelo quarter-car vs telemetría real.

Este script cierra el ciclo del portafolio:
    reglamento (02) → CAD (02) → modelo físico (quarter_car.py) → datos (01)

¿Qué significa "validar" aquí?
    Predecimos el recorrido de suspensión que DEBERÍA verse según la
    geometría diseñada, y lo comparamos con lo que un sensor MIDIÓ
    (canales SuspTravel_FL/FR de Assetto Corsa vía ACTI/MoTeC).
    Tres métricas, cada una responde a una pregunta distinta:

    - Correlación r  → ¿la FORMA es correcta? (la física de transferencias
      de carga: dónde comprime, dónde extiende). r > 0.9 = el modelo
      entiende la vuelta. r negativa = convención de signos invertida.
    - Ganancia (pendiente medida/predicha) → ¿la AMPLITUD es correcta?
      1.0 = rigidez y motion ratio bien medidos. 1.3 = el coche real es un
      30% más blando de lo que dice geometry.json.
    - RMSE (mm) → error global, útil para comparar iteraciones del modelo.

Uso:
    python validate_kinematics.py ruta/al/dataset.csv
    python validate_kinematics.py ruta.csv --geometry ../geometry.json --out ../reports

El CSV debe ser canónico (schema de 01_TELEMETRY_F1) e incluir
SuspTravel_FL/FR, LongAccel, LatAccel y Speed.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from quarter_car import load_geometry, natural_modes, predict_front_travel

# Mismo tema oscuro que el dashboard del proyecto 01
COLORS = {"bg": "#1a1a2e", "surface": "#16213e", "card": "#0f3460",
          "text": "#e0e0e0", "subtext": "#a0a0b0", "grid": "#2a2a4a",
          "accent": "#e94560"}
CORNER_COLORS = {"FL": "#00D2BE", "FR": "#FF8700"}

REQUIRED = ["Speed", "LongAccel", "LatAccel", "SuspTravel_FL", "SuspTravel_FR"]


def check_columns(df: pd.DataFrame) -> list[str]:
    """Comprueba que la telemetría trae lo necesario y explica cómo
    conseguirlo si falta (la razón de ser de docs/SIM_TELEMETRY.md)."""
    missing = [c for c in REQUIRED if c not in df.columns or df[c].isna().all()]
    if missing:
        print(f"[ERROR] Faltan canales: {missing}")
        print("  Captura en Assetto Corsa con ACTI -> exporta CSV de MoTeC i2")
        print("  -> conviertelo con f1core.adapters.assetto_corsa.from_motec_csv()")
        print("  (ver 01_TELEMETRY_F1/docs/SIM_TELEMETRY.md)")
    return missing


def corner_metrics(measured: np.ndarray, predicted: np.ndarray) -> dict:
    """Métricas de una esquina. Ambas señales se centran en su media porque
    el cero del potenciómetro es arbitrario (ver predict_front_travel)."""
    m = measured - measured.mean()
    p = predicted - predicted.mean()
    r = float(np.corrcoef(m, p)[0, 1])
    gain = float(np.dot(m, p) / np.dot(p, p)) if np.dot(p, p) > 0 else np.nan
    rmse = float(np.sqrt(np.mean((m - p) ** 2)))
    return {"r": round(r, 3), "gain": round(gain, 3), "rmse_mm": round(rmse, 2)}


def interpret(metrics: dict, corner: str) -> str:
    """Traducción a lenguaje de ingeniero: qué hacer con cada resultado."""
    r, gain = metrics["r"], metrics["gain"]
    if abs(r) < 0.5:
        return (f"{corner}: r={r} — el modelo NO explica la señal. Revisa que "
                "los canales sean de la esquina correcta y que LongAccel/"
                "LatAccel estén en g.")
    if r < 0:
        return (f"{corner}: correlación negativa (r={r}) — convención de signos "
                "invertida. Invierte el signo lateral en front_wheel_loads().")
    msg = f"{corner}: r={r} — la física de transferencias es correcta."
    if not (0.8 <= gain <= 1.2):
        direction = "más blanda" if gain > 1 else "más rígida"
        msg += (f" Pero ganancia={gain}: la suspensión real es ~{abs(gain-1)*100:.0f}% "
                f"{direction} que geometry.json → re-mide spring_rate y motion_ratio.")
    else:
        msg += f" Ganancia={gain}: rigidez y motion ratio dentro de ±20%."
    return msg


def validate(df: pd.DataFrame, geo: dict) -> tuple[pd.DataFrame, dict, list[str]]:
    """Ejecuta la validación por Source y por esquina."""
    rows, notes, preds = [], [], {}
    for src, g in df.groupby("Source"):
        g = g.sort_values("LapDistanceNorm")
        pred = predict_front_travel(g, geo)
        preds[src] = (g, pred)
        for corner in ("FL", "FR"):
            met = corner_metrics(g[f"SuspTravel_{corner}"].values,
                                 pred[f"PredTravel_{corner}"].values)
            rows.append({"Source": src, "Corner": corner, **met})
            notes.append(interpret(met, f"{src}/{corner}"))
    return pd.DataFrame(rows), preds, notes


def comparison_figure(g: pd.DataFrame, pred: pd.DataFrame, corner: str,
                      src: str) -> go.Figure:
    """Medido vs predicho (ambos centrados) sobre la distancia de vuelta."""
    x = g["LapDistanceNorm"].values
    meas = g[f"SuspTravel_{corner}"].values
    p = pred[f"PredTravel_{corner}"].values
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=meas - meas.mean(), name=f"Medido {corner}",
                             line=dict(color=CORNER_COLORS[corner], width=2)))
    fig.add_trace(go.Scatter(x=x, y=p - p.mean(), name=f"Modelo {corner}",
                             line=dict(color=COLORS["accent"], width=2, dash="dash")))
    fig.update_layout(
        paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], family="Arial"),
        title=dict(text=f"{src} · {corner}: recorrido medido vs quarter-car",
                   font=dict(size=15)),
        xaxis=dict(title="Distancia normalizada (0 → 1)", gridcolor=COLORS["grid"]),
        yaxis=dict(title="Recorrido centrado (mm)", gridcolor=COLORS["grid"]),
        hovermode="x unified", margin=dict(l=50, r=20, t=40, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0.4)"),
    )
    return fig


def build_report(metrics: pd.DataFrame, preds: dict, notes: list[str],
                 geo: dict, dataset_name: str, out_dir: str) -> str:
    """Reporte HTML autocontenido (mismo criterio que el dashboard: los
    gráficos Plotly siguen siendo interactivos y se comparte un solo archivo)."""
    modes = natural_modes(geo)
    est = geo["car"].get("estimated") or geo["front_corner"].get("estimated")
    warning = ("<p style='color:#e94560'><b>AVISO:</b> geometry.json contiene "
               "valores estimados — esto valida el PIPELINE, no el diseño CAD."
               "</p>" if est else "")

    parts = [f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Validación cinemática · {dataset_name}</title>
<style>
 body {{ background:{COLORS['bg']}; color:{COLORS['text']};
        font-family: Arial, sans-serif; margin:0; padding:24px 5vw; }}
 h1 {{ font-size:1.5rem; }} h2 {{ font-size:1.1rem; color:{COLORS['subtext']}; }}
 table {{ border-collapse:collapse; margin:12px 0 24px; }}
 th,td {{ border:1px solid {COLORS['grid']}; padding:8px 14px; text-align:center;
         font-size:0.9rem; }}
 th {{ background:{COLORS['card']}; }}
 .chart {{ background:{COLORS['surface']}; border-radius:8px; padding:8px;
          margin-bottom:20px; }}
 .note {{ background:{COLORS['surface']}; border-left:4px solid {COLORS['accent']};
         padding:10px 16px; margin:8px 0; border-radius:4px; }}
</style></head><body>
<h1>🔧 Validación cinemática — quarter-car vs telemetría</h1>
<p style="color:{COLORS['subtext']}">Dataset: {dataset_name} ·
{datetime.now():%Y-%m-%d %H:%M}</p>
{warning}
<h2>Modos propios del modelo</h2>
{pd.DataFrame([modes]).to_html(index=False, border=0)}
<h2>Métricas por esquina</h2>
{metrics.to_html(index=False, border=0)}
<h2>Interpretación</h2>
{''.join(f'<div class="note">{n}</div>' for n in notes)}"""]

    include_js = "cdn"
    for src, (g, pred) in preds.items():
        for corner in ("FL", "FR"):
            fig = comparison_figure(g, pred, corner, src)
            parts.append('<div class="chart">')
            parts.append(fig.to_html(full_html=False, include_plotlyjs=include_js,
                                     config={"displayModeBar": False}))
            parts.append("</div>")
            include_js = False

    parts.append("</body></html>")

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"kinematics_{dataset_name}_"
                                 f"{datetime.now():%Y%m%d_%H%M}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return path


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset", help="CSV canónico con canales SuspTravel_*")
    ap.add_argument("--geometry", default=None, help="ruta a geometry.json")
    ap.add_argument("--out", default=os.path.join(base, "..", "reports"))
    args = ap.parse_args()

    geo = load_geometry(args.geometry)
    df = pd.read_csv(args.dataset)
    if check_columns(df):
        raise SystemExit(1)

    metrics, preds, notes = validate(df, geo)
    print("\n" + metrics.to_string(index=False))
    print()
    for n in notes:
        print(f"  - {n}")

    name = os.path.splitext(os.path.basename(args.dataset))[0]
    path = build_report(metrics, preds, notes, geo, name, args.out)
    print(f"\n[OK] Reporte: {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
