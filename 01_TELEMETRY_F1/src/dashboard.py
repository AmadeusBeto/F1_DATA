"""
Dashboard de telemetría F1 / Sim Racing — multi-dataset, tres vistas.

Vistas:
    🎙 Presentación → para mostrar a otros: tarjetas, un gráfico grande,
                      conclusiones automáticas en lenguaje natural.
    🔬 Análisis     → para trabajar: todas las trazas, mini-sectores,
                      tabla de estadísticas y exportación de reportes.

Uso:
    python dashboard.py
    → http://127.0.0.1:8050

El dropdown lista automáticamente todo CSV en ../data/ que cumpla el schema
canónico (ver docs/DATA_TEMPLATE.md). Para añadir un dataset nuevo:
    python prepare_data_set.py --year 2024 --gp Monza --session Q --drivers LEC NOR
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from f1core import list_datasets, load_dataset, load_metadata  # noqa: E402
from f1core.prepare import compute_delta, summary_stats, sector_deltas  # noqa: E402

DATA_DIR = os.path.join(BASE_DIR, "..", "data")
REPORTS_DIR = os.path.join(BASE_DIR, "..", "reports")

# ---------------------------------------------------------------------------
# Tema
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#1a1a2e",
    "surface": "#16213e",
    "card": "#0f3460",
    "text": "#e0e0e0",
    "subtext": "#a0a0b0",
    "grid": "#2a2a4a",
    "accent": "#e94560",
}

#: Colores de equipo para pilotos conocidos; el resto usa la paleta cíclica.
TEAM_COLORS = {
    "HAM": "#00D2BE", "BOT": "#00D2BE", "RUS": "#00D2BE", "ANT": "#00D2BE",
    "VER": "#FF8700", "PER": "#FF8700", "TSU": "#FF8700", "LAW": "#FF8700",
    "LEC": "#DC0000", "SAI": "#DC0000", "BEA": "#DC0000",
    "NOR": "#FF8000", "PIA": "#FF8000", "RIC": "#FF8000",
    "ALO": "#006F62", "STR": "#006F62",
    "GAS": "#0090FF", "OCO": "#0090FF", "COL": "#0090FF",
    "ALB": "#005AFF", "SAR": "#005AFF",
    "HUL": "#52E252", "MAG": "#B6BABD", "BOR": "#52E252",
    "ZHO": "#900000", "HAD": "#6692FF",
}
PALETTE = ["#00D2BE", "#FF8700", "#DC0000", "#FF8000", "#0090FF",
           "#52E252", "#e94560", "#f5f5f5", "#a882dd", "#ffd166"]


def source_colors(sources: list[str]) -> dict[str, str]:
    """Asigna color por fuente: color de equipo si es un piloto conocido,
    si no, paleta cíclica (para trazas de sims, setups, etc.)."""
    out, i = {}, 0
    for src in sources:
        key = src.upper()[:3]
        if key in TEAM_COLORS and TEAM_COLORS[key] not in out.values():
            out[src] = TEAM_COLORS[key]
        else:
            while PALETTE[i % len(PALETTE)] in out.values():
                i += 1
            out[src] = PALETTE[i % len(PALETTE)]
            i += 1
    return out


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


def plot_layout(**overrides) -> dict:
    layout = dict(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], family="Arial, sans-serif"),
        legend=dict(bgcolor="rgba(0,0,0,0.4)", bordercolor=COLORS["grid"], borderwidth=1),
        xaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"],
                   showspikes=True, spikethickness=1, spikecolor=COLORS["subtext"],
                   spikemode="across"),
        yaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
        hovermode="x unified",
        margin=dict(l=50, r=20, t=40, b=40),
    )
    layout.update(overrides)
    return layout


# ---------------------------------------------------------------------------
# Figuras (genéricas: funcionan con cualquier dataset canónico)
# ---------------------------------------------------------------------------

def line_figure(df: pd.DataFrame, column: str, title: str, y_title: str,
                fill: bool = False) -> go.Figure:
    fig = go.Figure()
    colors = source_colors(list(df["Source"].unique()))
    for src, g in df.groupby("Source", sort=False):
        fig.add_trace(go.Scatter(
            x=g["LapDistanceNorm"], y=g[column], mode="lines", name=src,
            line=dict(color=colors[src], width=2),
            fill="tozeroy" if fill else None,
            fillcolor=hex_to_rgba(colors[src], 0.15) if fill else None,
            hovertemplate=f"<b>{src}</b><br>Distancia: %{{x:.3f}}<br>"
                          f"{y_title}: %{{y:.1f}}<extra></extra>",
        ))
    fig.update_layout(**plot_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis_title="Distancia normalizada (0 → 1)",
        yaxis_title=y_title,
    ))
    return fig


def delta_figure(df: pd.DataFrame, reference: str | None = None) -> go.Figure:
    delta = compute_delta(df, reference)
    reference = delta.attrs["reference"]
    colors = source_colors(list(df["Source"].unique()))

    fig = go.Figure()
    for col in delta.columns:
        if not col.startswith("Delta_"):
            continue
        src = col.replace("Delta_", "")
        fig.add_trace(go.Scatter(
            x=delta["LapDistanceNorm"], y=delta[col], mode="lines",
            name=f"{src} vs {reference}",
            line=dict(color=colors.get(src, "#ffffff"), width=2),
            fill="tozeroy", fillcolor=hex_to_rgba(colors.get(src, "#ffffff"), 0.20),
            hovertemplate=f"Distancia: %{{x:.3f}}<br>Δt {src}−{reference}: "
                          "%{y:+.3f} s<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["subtext"])
    fig.update_layout(**plot_layout(
        title=dict(text=f"Delta de tiempo acumulado (vs {reference}) · "
                        "positivo = pierde tiempo", font=dict(size=15)),
        xaxis_title="Distancia normalizada (0 → 1)",
        yaxis_title="Δ tiempo (s)",
    ))
    return fig


def has_track_coords(df: pd.DataFrame) -> bool:
    return ("X" in df.columns and "Y" in df.columns
            and df["X"].notna().any() and df["Y"].notna().any())


def track_map_figure(df: pd.DataFrame) -> go.Figure:
    """Mapa de dominancia: el trazado de la pista coloreado por diferencias.

    ¿Por qué esto y no un heatmap clásico? La telemetría vive sobre una línea
    (la trazada), no sobre una malla 2D. Pintar el trazado según quién es más
    rápido en cada punto ("who's faster where") comunica en un vistazo lo que
    el delta tarda un gráfico entero en explicar.

    - 2 trazas  → color continuo por diferencia de velocidad (km/h).
    - >2 trazas → color discreto por la traza más rápida en cada punto.
    - 1 traza   → heatmap de su propia velocidad.
    Requiere columnas X, Y (el dataset alineado comparte la malla de
    LapDistanceNorm, así que las velocidades son comparables punto a punto).
    """
    sources = list(df["Source"].unique())
    colors = source_colors(sources)
    # Trazado de referencia: la primera traza con coordenadas
    ref_src = next(s for s in sources
                   if df[df["Source"] == s]["X"].notna().any())
    ref = df[df["Source"] == ref_src].sort_values("LapDistanceNorm")
    x, y, dist = ref["X"].values, ref["Y"].values, ref["LapDistanceNorm"].values

    speed = {s: df[df["Source"] == s].sort_values("LapDistanceNorm")["Speed"].values
             for s in sources}

    fig = go.Figure()

    if len(sources) == 2:
        a, b = sources
        diff = speed[a] - speed[b]           # + = a más rápido
        lim = float(max(abs(diff).max(), 1.0))
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers",
            marker=dict(
                size=7, color=diff, cmin=-lim, cmax=lim,
                colorscale=[[0.0, colors[b]], [0.5, "#3a3a55"], [1.0, colors[a]]],
                colorbar=dict(
                    title=dict(text=f"Δv (km/h)<br>{a} ⟵⟶ {b}",
                               font=dict(size=11, color=COLORS["subtext"])),
                    tickfont=dict(color=COLORS["subtext"]),
                    thickness=14, len=0.7,
                ),
            ),
            customdata=list(zip(dist, speed[a], speed[b])),
            hovertemplate=("Distancia: %{customdata[0]:.3f}<br>"
                           f"{a}: %{{customdata[1]:.1f}} km/h<br>"
                           f"{b}: %{{customdata[2]:.1f}} km/h<br>"
                           "Δv: %{marker.color:+.1f} km/h<extra></extra>"),
            showlegend=False,
        ))
        title = f"Mapa de dominancia · {a} vs {b} (color = quién va más rápido ahí)"
    elif len(sources) > 2:
        import numpy as np
        stacked = np.vstack([speed[s] for s in sources])
        fastest_idx = stacked.argmax(axis=0)
        for i, s in enumerate(sources):
            mask = fastest_idx == i
            fig.add_trace(go.Scatter(
                x=x[mask], y=y[mask], mode="markers", name=f"{s} más rápido",
                marker=dict(size=7, color=colors[s]),
                customdata=dist[mask],
                hovertemplate=(f"<b>{s}</b> más rápido<br>"
                               "Distancia: %{customdata:.3f}<extra></extra>"),
            ))
        title = "Mapa de dominancia · traza más rápida en cada punto"
    else:
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers",
            marker=dict(size=7, color=speed[ref_src], colorscale="Turbo",
                        colorbar=dict(title=dict(text="km/h",
                                                 font=dict(color=COLORS["subtext"])),
                                      tickfont=dict(color=COLORS["subtext"]),
                                      thickness=14, len=0.7)),
            customdata=dist,
            hovertemplate=("Distancia: %{customdata:.3f}<br>"
                           "Velocidad: %{marker.color:.1f} km/h<extra></extra>"),
            showlegend=False,
        ))
        title = f"Mapa de velocidad · {ref_src}"

    # Línea de meta
    fig.add_trace(go.Scatter(
        x=[x[0]], y=[y[0]], mode="markers+text", text=["🏁"],
        textposition="top center", textfont=dict(size=16),
        marker=dict(size=1, color="rgba(0,0,0,0)"),
        hoverinfo="skip", showlegend=False,
    ))

    fig.update_layout(**plot_layout(
        title=dict(text=title, font=dict(size=15)),
        hovermode="closest",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        legend=dict(bgcolor="rgba(0,0,0,0.4)", bordercolor=COLORS["grid"],
                    borderwidth=1, orientation="h", y=-0.05),
        margin=dict(l=10, r=10, t=40, b=10),
    ))
    return fig


def track_map_placeholder() -> html.Div:
    """Aviso cuando el dataset no trae coordenadas X/Y."""
    return html.Div(
        style={**CHART_CARD, "padding": "22px 26px"},
        children=[
            html.H3("🗺 Mapa de pista no disponible para este dataset",
                    style={"color": COLORS["text"], "marginTop": "0"}),
            html.P("Este dataset no incluye coordenadas X/Y. Para datasets de "
                   "F1, regenera con la versión actual del descargador:",
                   style={"color": COLORS["subtext"]}),
            html.Code("python prepare_data_set.py --year 2021 --gp \"Abu Dhabi\" "
                      "--session Q --drivers HAM VER",
                      style={"color": COLORS["accent"], "backgroundColor":
                             COLORS["bg"], "padding": "6px 10px",
                             "borderRadius": "4px", "display": "inline-block"}),
        ],
    )


def build_insights(df: pd.DataFrame) -> list[str]:
    """Conclusiones automáticas en lenguaje natural para la vista Presentación."""
    stats = summary_stats(df)
    insights = []
    if len(stats) >= 2:
        fastest, second = stats.iloc[0], stats.iloc[1]
        gap = second["LapTime_s"] - fastest["LapTime_s"]
        insights.append(
            f"🏆 {fastest['Source']} marca la vuelta más rápida "
            f"({fastest['LapTime_s']:.3f}s), {gap:.3f}s por delante de "
            f"{second['Source']}.")

        sectors = sector_deltas(df, n_sectors=3, reference=fastest["Source"])
        col = [c for c in sectors.columns if c.startswith(second["Source"])]
        if col:
            worst = sectors.loc[sectors[col[0]].idxmax()]
            insights.append(
                f"📍 La mayor diferencia se construye en el sector {int(worst['Sector'])} "
                f"(tramo {worst['Range']} de la vuelta): {worst[col[0]]:+.3f}s.")

        vmax_leader = stats.loc[stats["VMax_kmh"].idxmax()]
        insights.append(
            f"🚀 Velocidad punta: {vmax_leader['Source']} con "
            f"{vmax_leader['VMax_kmh']:.0f} km/h.")

        ft_leader = stats.loc[stats["FullThrottle_pct"].idxmax()]
        insights.append(
            f"⚡ {ft_leader['Source']} va a fondo el {ft_leader['FullThrottle_pct']:.0f}% "
            "de la vuelta — un buen proxy de confianza en el coche.")
    elif len(stats) == 1:
        s = stats.iloc[0]
        insights.append(
            f"⏱ {s['Source']}: vuelta de {s['LapTime_s']:.3f}s, "
            f"Vmax {s['VMax_kmh']:.0f} km/h, a fondo el {s['FullThrottle_pct']:.0f}% "
            "de la vuelta.")
    return insights


# ---------------------------------------------------------------------------
# Componentes de layout
# ---------------------------------------------------------------------------

CARD = dict(backgroundColor=COLORS["card"], borderRadius="8px",
            padding="14px 20px", textAlign="center", minWidth="150px")
CHART_CARD = dict(backgroundColor=COLORS["surface"], borderRadius="8px",
                  padding="8px", marginBottom="16px",
                  border=f"1px solid {COLORS['card']}")


def stat_card(label: str, value: str, color: str) -> html.Div:
    return html.Div(style={**CARD, "borderLeft": f"4px solid {color}"}, children=[
        html.P(label, style={"color": COLORS["subtext"], "margin": "0",
                             "fontSize": "0.75rem"}),
        html.H3(value, style={"color": color, "margin": "4px 0 0",
                              "fontSize": "1.4rem"}),
    ])


def stats_cards(df: pd.DataFrame) -> html.Div:
    stats = summary_stats(df)
    colors = source_colors(list(df["Source"].unique()))
    cards = []
    for _, row in stats.iterrows():
        cards.append(stat_card(f"{row['Source']} · Vuelta",
                               f"{row['LapTime_s']:.3f} s", colors[row["Source"]]))
        cards.append(stat_card(f"{row['Source']} · Vmax",
                               f"{row['VMax_kmh']:.0f} km/h", colors[row["Source"]]))
    if len(stats) >= 2:
        gap = stats.iloc[1]["LapTime_s"] - stats.iloc[0]["LapTime_s"]
        cards.insert(0, stat_card("Diferencia", f"{gap:.3f} s", "#ffffff"))
    return html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "14px",
                           "justifyContent": "center", "padding": "18px 32px 8px"},
                    children=cards)


def make_table(df: pd.DataFrame, table_id: str) -> dash_table.DataTable:
    return dash_table.DataTable(
        id=table_id,
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_header={"backgroundColor": COLORS["card"], "color": COLORS["text"],
                      "fontWeight": "bold", "border": "none"},
        style_cell={"backgroundColor": COLORS["surface"], "color": COLORS["text"],
                    "border": f"1px solid {COLORS['grid']}", "padding": "8px",
                    "fontFamily": "Arial", "fontSize": "0.85rem",
                    "textAlign": "center"},
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    title="F1 Telemetry Lab",
    meta_tags=[{"name": "viewport",
                "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)

datasets = list_datasets(DATA_DIR)
DEFAULT_DATASET = next(
    (d["path"] for d in datasets if "comparison" in d["path"]),
    datasets[0]["path"] if datasets else None,
)

app.layout = html.Div(
    style={"backgroundColor": COLORS["bg"], "minHeight": "100vh",
           "fontFamily": "Arial, sans-serif"},
    children=[
        # Header ------------------------------------------------------------
        html.Div(
            style={"background": f"linear-gradient(135deg, {COLORS['surface']} 0%, "
                                 f"{COLORS['card']} 100%)",
                   "padding": "20px 32px",
                   "borderBottom": f"2px solid {COLORS['card']}",
                   "display": "flex", "flexWrap": "wrap", "gap": "16px",
                   "alignItems": "center", "justifyContent": "space-between"},
            children=[
                html.Div([
                    html.H1("🏎️ F1 Telemetry Lab",
                            style={"color": COLORS["text"], "margin": "0",
                                   "fontSize": "1.5rem"}),
                    html.P(id="dataset-subtitle",
                           style={"color": COLORS["subtext"], "margin": "4px 0 0"}),
                ]),
                html.Div(style={"minWidth": "320px", "flexGrow": "1",
                                "maxWidth": "480px"}, children=[
                    html.Label("Dataset:", style={"color": COLORS["subtext"],
                                                  "fontSize": "0.8rem"}),
                    dcc.Dropdown(
                        id="dataset-selector",
                        options=[{"label": d["name"], "value": d["path"]}
                                 for d in datasets],
                        value=DEFAULT_DATASET,
                        clearable=False,
                        style={"color": "#111"},
                    ),
                ]),
            ],
        ),

        # Tabs ---------------------------------------------------------------
        dcc.Tabs(
            id="view-tabs", value="presentation",
            colors={"border": COLORS["card"], "primary": COLORS["accent"],
                    "background": COLORS["surface"]},
            style={"backgroundColor": COLORS["surface"]},
            children=[
                dcc.Tab(label="🎙 Presentación", value="presentation",
                        style={"backgroundColor": COLORS["surface"],
                               "color": COLORS["subtext"], "border": "none"},
                        selected_style={"backgroundColor": COLORS["card"],
                                        "color": COLORS["text"], "border": "none",
                                        "fontWeight": "bold"}),
                dcc.Tab(label="🔬 Análisis", value="analysis",
                        style={"backgroundColor": COLORS["surface"],
                               "color": COLORS["subtext"], "border": "none"},
                        selected_style={"backgroundColor": COLORS["card"],
                                        "color": COLORS["text"], "border": "none",
                                        "fontWeight": "bold"}),
                dcc.Tab(label="🔧 Cinemática", value="kinematics",
                        style={"backgroundColor": COLORS["surface"],
                               "color": COLORS["subtext"], "border": "none"},
                        selected_style={"backgroundColor": COLORS["card"],
                                        "color": COLORS["text"], "border": "none",
                                        "fontWeight": "bold"}),
            ],
        ),

        html.Div(id="tab-content"),
        dcc.Download(id="download-report"),
        dcc.Download(id="download-csv"),
    ],
)


# ---------------------------------------------------------------------------
# Render de pestañas
# ---------------------------------------------------------------------------

@app.callback(
    Output("tab-content", "children"),
    Output("dataset-subtitle", "children"),
    Input("view-tabs", "value"),
    Input("dataset-selector", "value"),
)
def render_tab(tab: str, dataset_path: str):
    if not dataset_path:
        return html.Div("No hay datasets en la carpeta data/. Ejecuta "
                        "prepare_data_set.py para descargar uno.",
                        style={"color": COLORS["text"], "padding": "40px"}), ""

    df = load_dataset(dataset_path, validate=False)
    meta = load_metadata(dataset_path)
    subtitle = meta.get("title", os.path.basename(dataset_path))
    if meta.get("source_type"):
        subtitle += f"  ·  fuente: {meta['source_type']}"

    if tab == "presentation":
        return presentation_view(df), subtitle
    if tab == "kinematics":
        return kinematics_view(df), subtitle
    return analysis_view(df), subtitle


def presentation_view(df: pd.DataFrame) -> html.Div:
    """Vista amena: tarjetas, un gráfico protagonista y conclusiones."""
    insights = build_insights(df)

    if has_track_coords(df):
        track_section = html.Div(style=CHART_CARD, children=dcc.Graph(
            figure=track_map_figure(df), style={"height": "62vh"},
            config={"displayModeBar": False}))
    else:
        track_section = track_map_placeholder()

    return html.Div([
        stats_cards(df),
        html.Div(style={"padding": "10px 32px 0"}, children=track_section),
        html.Div(style={"padding": "4px 32px"}, children=[
            dcc.RadioItems(
                id="presentation-chart",
                options=[{"label": " Velocidad", "value": "speed"},
                         {"label": " Delta de tiempo", "value": "delta"},
                         {"label": " Frenada y acelerador", "value": "pedals"}],
                value="speed", inline=True,
                style={"color": COLORS["text"]},
                inputStyle={"marginRight": "4px", "marginLeft": "14px"},
            ),
        ]),
        html.Div(id="presentation-chart-container",
                 style={"padding": "10px 32px 6px"}),
        html.Div(
            style={"padding": "6px 32px 32px"},
            children=html.Div(
                style={**CHART_CARD, "padding": "18px 24px"},
                children=[
                    html.H3("Conclusiones", style={"color": COLORS["text"],
                                                   "marginTop": "0"}),
                    *[html.P(t, style={"color": COLORS["text"],
                                       "fontSize": "1.02rem",
                                       "margin": "8px 0"}) for t in insights],
                ],
            ),
        ),
    ])


@app.callback(
    Output("presentation-chart-container", "children"),
    Input("presentation-chart", "value"),
    State("dataset-selector", "value"),
)
def update_presentation_chart(which: str, dataset_path: str):
    df = load_dataset(dataset_path, validate=False)
    if which == "delta" and df["Source"].nunique() > 1:
        fig = delta_figure(df)
    elif which == "pedals":
        fig = line_figure(df, "Throttle", "Acelerador y freno", "Pedal (%)")
        colors = source_colors(list(df["Source"].unique()))
        for src, g in df.groupby("Source", sort=False):
            fig.add_trace(go.Scatter(
                x=g["LapDistanceNorm"], y=g["Brake"], mode="lines",
                name=f"{src} · freno",
                line=dict(color=colors[src], width=1.5, dash="dot"),
            ))
    else:
        fig = line_figure(df, "Speed", "Velocidad a lo largo de la vuelta",
                          "Velocidad (km/h)")
    return html.Div(style=CHART_CARD, children=dcc.Graph(
        figure=fig, style={"height": "58vh"}, config={"displayModeBar": False}))


def analysis_view(df: pd.DataFrame) -> html.Div:
    """Vista técnica: todas las trazas, mini-sectores, tablas y exportación."""
    sources = list(df["Source"].unique())
    has_delta = len(sources) > 1

    figures = [
        line_figure(df, "Speed", "Velocidad", "km/h"),
        line_figure(df, "Throttle", "Acelerador", "%"),
        line_figure(df, "Brake", "Freno", "%", fill=True),
    ]
    if has_delta:
        figures.append(delta_figure(df))
    if "RPM" in df.columns and df["RPM"].notna().any():
        figures.append(line_figure(df, "RPM", "Régimen de motor", "RPM"))
    if "Gear" in df.columns and df["Gear"].notna().any():
        figures.append(line_figure(df, "Gear", "Marcha engranada", "Marcha"))

    grid_children = [
        html.Div(style={**CHART_CARD, "flex": "1 1 46%", "minWidth": "420px"},
                 children=dcc.Graph(figure=fig, style={"height": "40vh"},
                                    config={"displayModeBar": True}))
        for fig in figures
    ]

    controls = html.Div(
        style={"display": "flex", "flexWrap": "wrap", "gap": "18px",
               "alignItems": "flex-end", "padding": "18px 32px 0"},
        children=[
            html.Div([
                html.Label("Referencia para deltas:",
                           style={"color": COLORS["subtext"], "fontSize": "0.8rem"}),
                dcc.Dropdown(id="reference-selector",
                             options=[{"label": s, "value": s} for s in sources],
                             value=sources[0], clearable=False,
                             style={"width": "180px", "color": "#111"}),
            ]),
            html.Div([
                html.Label("Mini-sectores:",
                           style={"color": COLORS["subtext"], "fontSize": "0.8rem"}),
                dcc.Dropdown(id="sectors-selector",
                             options=[{"label": f"{n} sectores", "value": n}
                                      for n in (3, 6, 12, 20)],
                             value=6, clearable=False,
                             style={"width": "150px", "color": "#111"}),
            ]),
            html.Button("⬇ Exportar reporte HTML", id="btn-report", n_clicks=0,
                        style={"backgroundColor": COLORS["accent"], "color": "#fff",
                               "border": "none", "borderRadius": "6px",
                               "padding": "10px 18px", "cursor": "pointer",
                               "fontWeight": "bold"}),
            html.Button("⬇ Exportar resumen CSV", id="btn-csv", n_clicks=0,
                        style={"backgroundColor": COLORS["card"],
                               "color": COLORS["text"],
                               "border": f"1px solid {COLORS['grid']}",
                               "borderRadius": "6px", "padding": "10px 18px",
                               "cursor": "pointer"}),
        ],
    )

    return html.Div([
        controls,
        html.Div(style={"padding": "14px 32px 0"}, children=[
            html.H3("Estadísticas por traza", style={"color": COLORS["text"]}),
            make_table(summary_stats(df), "stats-table"),
        ]),
        html.Div(id="sectors-container", style={"padding": "14px 32px 0"}),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "16px",
                        "padding": "18px 32px 32px"},
                 children=grid_children),
    ])


@app.callback(
    Output("sectors-container", "children"),
    Input("sectors-selector", "value"),
    Input("reference-selector", "value"),
    State("dataset-selector", "value"),
)
def update_sectors(n_sectors: int, reference: str, dataset_path: str):
    df = load_dataset(dataset_path, validate=False)
    if df["Source"].nunique() < 2:
        return html.P("Se necesitan ≥2 trazas para mini-sectores.",
                      style={"color": COLORS["subtext"]})
    table = sector_deltas(df, n_sectors=n_sectors, reference=reference)
    return html.Div([
        html.H3(f"Delta por mini-sector (referencia: {reference}) · "
                "positivo = pierde tiempo en ese tramo",
                style={"color": COLORS["text"], "fontSize": "1.05rem"}),
        make_table(table, "sectors-table"),
    ])


# ---------------------------------------------------------------------------
# Vista Cinemática — puente con el módulo 03_KINEMATICS_F1
# ---------------------------------------------------------------------------
# ¿Por qué un import perezoso con fallback? El dashboard debe funcionar
# aunque el módulo 03 no exista todavía (repos clonados parcialmente).
KIN_SRC = os.path.join(BASE_DIR, "..", "..", "03_KINEMATICS_F1", "src")

_SUSP_FRONT = ["SuspTravel_FL", "SuspTravel_FR"]
_SUSP_REAR = ["SuspTravel_RL", "SuspTravel_RR"]


def _load_kin_module():
    """Devuelve (quarter_car, validate_kinematics) o (None, None)."""
    try:
        if KIN_SRC not in sys.path:
            sys.path.insert(0, KIN_SRC)
        import quarter_car
        import validate_kinematics
        return quarter_car, validate_kinematics
    except Exception:
        return None, None


def has_susp_channels(df: pd.DataFrame) -> bool:
    return all(c in df.columns and df[c].notna().any() for c in _SUSP_FRONT)


def susp_figure(df: pd.DataFrame, cols: list[str], title: str) -> go.Figure:
    """Recorridos de suspensión: una traza por (Source, esquina).
    La esquina derecha va punteada para distinguir lado sin duplicar color."""
    colors = source_colors(list(df["Source"].unique()))
    fig = go.Figure()
    for src, g in df.groupby("Source", sort=False):
        for col in cols:
            corner = col.split("_")[1]
            fig.add_trace(go.Scatter(
                x=g["LapDistanceNorm"], y=g[col], mode="lines",
                name=f"{src} · {corner}",
                line=dict(color=colors[src], width=2,
                          dash="dot" if corner.endswith("R") else "solid"),
            ))
    fig.update_layout(**plot_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis_title="Distancia normalizada (0 → 1)",
        yaxis_title="Recorrido (mm)",
    ))
    return fig


def kinematics_placeholder() -> html.Div:
    return html.Div(style={**CHART_CARD, "padding": "22px 26px"}, children=[
        html.H3("🔧 Este dataset no trae canales de suspensión",
                style={"color": COLORS["text"], "marginTop": "0"}),
        html.P("La validación cinemática necesita SuspTravel_FL/FR (más "
               "LongAccel/LatAccel). La telemetría oficial de F1 no los "
               "publica: se capturan en Assetto Corsa con ACTI → MoTeC i2 "
               "(ver docs/SIM_TELEMETRY.md). Para probar el pipeline sin "
               "capturas reales:",
               style={"color": COLORS["subtext"]}),
        html.Code("cd 03_KINEMATICS_F1/src && python make_demo_data.py "
                  "--to-dashboard",
                  style={"color": COLORS["accent"], "backgroundColor": COLORS["bg"],
                         "padding": "6px 10px", "borderRadius": "4px",
                         "display": "inline-block"}),
    ])


def kinematics_view(df: pd.DataFrame) -> html.Div:
    """Vista del módulo 03: recorridos medidos y, si hay geometría y
    aceleraciones, la predicción del quarter-car con sus métricas."""
    if not has_susp_channels(df):
        return html.Div(style={"padding": "18px 32px"},
                        children=kinematics_placeholder())

    children = []
    qc, vk = _load_kin_module()
    can_predict = (qc is not None and "LongAccel" in df.columns
                   and "LatAccel" in df.columns
                   and df["LongAccel"].notna().any())

    if can_predict:
        try:
            geo = qc.load_geometry()
            modes = qc.natural_modes(geo)
            cards = [
                stat_card("f suspendida", f"{modes['f_sprung_Hz']} Hz",
                          COLORS["accent"]),
                stat_card("f no suspendida", f"{modes['f_unsprung_Hz']} Hz",
                          COLORS["accent"]),
                stat_card("Amortiguamiento ζ", f"{modes['damping_ratio']}",
                          COLORS["accent"]),
                stat_card("Rigidez en rueda",
                          f"{modes['wheel_rate_N_per_mm']} N/mm",
                          COLORS["accent"]),
            ]
            for src, g in df.groupby("Source"):
                g = g.sort_values("LapDistanceNorm")
                pred = qc.predict_front_travel(g, geo)
                for corner in ("FL", "FR"):
                    met = vk.corner_metrics(
                        g[f"SuspTravel_{corner}"].values,
                        pred[f"PredTravel_{corner}"].values)
                    cards.append(stat_card(f"{src} {corner} · r / ganancia",
                                           f"{met['r']} / {met['gain']}",
                                           "#ffffff"))
                # Overlay modelo vs medido (centrados — el cero del sensor
                # es arbitrario, ver quarter_car.predict_front_travel)
                fig = go.Figure()
                for corner, c in (("FL", "#00D2BE"), ("FR", "#FF8700")):
                    meas = g[f"SuspTravel_{corner}"].values
                    p = pred[f"PredTravel_{corner}"].values
                    fig.add_trace(go.Scatter(
                        x=g["LapDistanceNorm"], y=meas - meas.mean(),
                        name=f"Medido {corner}", line=dict(color=c, width=2)))
                    fig.add_trace(go.Scatter(
                        x=g["LapDistanceNorm"], y=p - p.mean(),
                        name=f"Modelo {corner}",
                        line=dict(color=c, width=1.5, dash="dash")))
                fig.update_layout(**plot_layout(
                    title=dict(text=f"{src} · quarter-car vs medición "
                                    "(señales centradas)", font=dict(size=15)),
                    xaxis_title="Distancia normalizada (0 → 1)",
                    yaxis_title="Recorrido centrado (mm)",
                ))
                children.append(html.Div(style=CHART_CARD, children=dcc.Graph(
                    figure=fig, style={"height": "46vh"},
                    config={"displayModeBar": True})))
            children.insert(0, html.Div(
                style={"display": "flex", "flexWrap": "wrap", "gap": "14px",
                       "justifyContent": "center", "padding": "4px 0 14px"},
                children=cards))
        except Exception as exc:
            children.append(html.P(f"Modelo no disponible: {exc}",
                                   style={"color": COLORS["subtext"]}))
    else:
        children.append(html.P(
            "Sin LongAccel/LatAccel (o sin el módulo 03) solo se muestran los "
            "recorridos medidos — la predicción del quarter-car necesita "
            "aceleraciones.", style={"color": COLORS["subtext"]}))

    children.append(html.Div(style=CHART_CARD, children=dcc.Graph(
        figure=susp_figure(df, _SUSP_FRONT, "Recorrido de suspensión delantera"),
        style={"height": "40vh"}, config={"displayModeBar": True})))
    if all(c in df.columns and df[c].notna().any() for c in _SUSP_REAR):
        children.append(html.Div(style=CHART_CARD, children=dcc.Graph(
            figure=susp_figure(df, _SUSP_REAR, "Recorrido de suspensión trasera"),
            style={"height": "40vh"}, config={"displayModeBar": True})))

    return html.Div(style={"padding": "18px 32px 32px"}, children=children)


# ---------------------------------------------------------------------------
# Exportación de reportes
# ---------------------------------------------------------------------------

@app.callback(
    Output("download-report", "data"),
    Input("btn-report", "n_clicks"),
    State("dataset-selector", "value"),
    State("reference-selector", "value"),
    State("sectors-selector", "value"),
    prevent_initial_call=True,
)
def export_report(n_clicks: int, dataset_path: str, reference: str, n_sectors: int):
    df = load_dataset(dataset_path, validate=False)
    meta = load_metadata(dataset_path)
    title = meta.get("title", os.path.basename(dataset_path))
    html_doc = build_html_report(df, meta, title, reference, n_sectors)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    slug = os.path.splitext(os.path.basename(dataset_path))[0]
    filename = f"report_{slug}_{datetime.now():%Y%m%d_%H%M}.html"
    with open(os.path.join(REPORTS_DIR, filename), "w", encoding="utf-8") as fh:
        fh.write(html_doc)

    return dict(content=html_doc, filename=filename)


@app.callback(
    Output("download-csv", "data"),
    Input("btn-csv", "n_clicks"),
    State("dataset-selector", "value"),
    prevent_initial_call=True,
)
def export_csv(n_clicks: int, dataset_path: str):
    df = load_dataset(dataset_path, validate=False)
    stats = summary_stats(df)
    slug = os.path.splitext(os.path.basename(dataset_path))[0]
    return dict(content=stats.to_csv(index=False),
                filename=f"summary_{slug}.csv")


def build_html_report(df: pd.DataFrame, meta: dict, title: str,
                      reference: str | None, n_sectors: int) -> str:
    """Reporte HTML autocontenido: stats + mini-sectores + gráficos interactivos.

    ¿Por qué HTML y no PDF? Conserva los gráficos Plotly interactivos (zoom,
    hover) y se comparte como un solo archivo que abre cualquier navegador.
    """
    stats = summary_stats(df)
    parts = [f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{title}</title>
<style>
 body {{ background:{COLORS['bg']}; color:{COLORS['text']};
        font-family: Arial, sans-serif; margin: 0; padding: 24px 5vw; }}
 h1 {{ font-size: 1.6rem; }} h2 {{ font-size: 1.1rem; color:{COLORS['subtext']}; }}
 table {{ border-collapse: collapse; margin: 12px 0 28px; }}
 th, td {{ border: 1px solid {COLORS['grid']}; padding: 8px 14px;
          text-align: center; font-size: 0.9rem; }}
 th {{ background: {COLORS['card']}; }}
 .chart {{ background:{COLORS['surface']}; border-radius: 8px;
          padding: 8px; margin-bottom: 20px; }}
 .meta {{ color: {COLORS['subtext']}; font-size: 0.85rem; }}
</style></head><body>
<h1>🏎️ {title}</h1>
<p class="meta">Reporte generado el {datetime.now():%Y-%m-%d %H:%M} ·
F1 Telemetry Lab</p>
<h2>Estadísticas por traza</h2>
{stats.to_html(index=False, border=0)}"""]

    if df["Source"].nunique() > 1:
        sectors = sector_deltas(df, n_sectors=n_sectors, reference=reference)
        parts.append(f"<h2>Delta por mini-sector (ref: {reference or 'auto'})</h2>"
                     f"{sectors.to_html(index=False, border=0)}")

    figures = []
    if has_track_coords(df):
        figures.append(track_map_figure(df))
    figures += [
        line_figure(df, "Speed", "Velocidad", "km/h"),
        line_figure(df, "Throttle", "Acelerador", "%"),
        line_figure(df, "Brake", "Freno", "%", fill=True),
    ]
    if df["Source"].nunique() > 1:
        figures.append(delta_figure(df, reference))

    include_js = "cdn"
    for fig in figures:
        parts.append('<div class="chart">')
        parts.append(fig.to_html(full_html=False, include_plotlyjs=include_js,
                                 config={"displayModeBar": False}))
        parts.append("</div>")
        include_js = False  # el JS de Plotly solo se incluye una vez

    parts.append("</body></html>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
