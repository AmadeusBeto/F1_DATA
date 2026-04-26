"""
Dashboard interactivo de telemetría F1 – Abu Dhabi 2021 Clasificación
Lewis Hamilton (HAM) vs Max Verstappen (VER)

Uso:
    python dashboard.py

Luego abre http://127.0.0.1:8050 en el navegador.
"""

import os
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd

# ---------------------------------------------------------------------------
# Rutas de datos
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "abu_dhabi_2021_comparison.csv")

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
df = pd.read_csv(DATA_PATH)

ham = df[df["Source"] == "HAM"].copy()
ver = df[df["Source"] == "VER"].copy()

# ---------------------------------------------------------------------------
# Colores / tema
# ---------------------------------------------------------------------------
COLORS = {
    "HAM": "#00D2BE",   # Mercedes teal
    "VER": "#FF8700",   # Red Bull orange
    "bg": "#1a1a2e",
    "surface": "#16213e",
    "card": "#0f3460",
    "text": "#e0e0e0",
    "subtext": "#a0a0b0",
    "grid": "#2a2a4a",
}


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a '#RRGGBB' colour string to an rgba(...) CSS value."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


PLOT_LAYOUT = dict(
    paper_bgcolor=COLORS["surface"],
    plot_bgcolor=COLORS["bg"],
    font=dict(color=COLORS["text"], family="Arial, sans-serif"),
    legend=dict(
        bgcolor="rgba(0,0,0,0.4)",
        bordercolor=COLORS["grid"],
        borderwidth=1,
    ),
    xaxis=dict(
        gridcolor=COLORS["grid"],
        zerolinecolor=COLORS["grid"],
        showspikes=True,
        spikethickness=1,
        spikecolor=COLORS["subtext"],
        spikemode="across",
    ),
    yaxis=dict(
        gridcolor=COLORS["grid"],
        zerolinecolor=COLORS["grid"],
    ),
    hovermode="x unified",
    margin=dict(l=50, r=20, t=40, b=40),
)

# ---------------------------------------------------------------------------
# Figuras estáticas (se computan una sola vez al arrancar)
# ---------------------------------------------------------------------------

def make_speed_figure():
    fig = go.Figure()
    for source, data, name in [
        ("HAM", ham, "Lewis Hamilton"),
        ("VER", ver, "Max Verstappen"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=data["LapDistanceNorm"],
                y=data["Speed"],
                mode="lines",
                name=f"{source} – {name}",
                line=dict(color=COLORS[source], width=2),
                hovertemplate=(
                    f"<b>{source}</b><br>"
                    "Distancia: %{x:.3f}<br>"
                    "Velocidad: %{y:.1f} km/h<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text="Velocidad a lo largo de la vuelta", font=dict(size=15)),
        xaxis_title="Distancia normalizada (0 → 1)",
        yaxis_title="Velocidad (km/h)",
    )
    return fig


def make_throttle_figure():
    fig = go.Figure()
    for source, data, name in [
        ("HAM", ham, "Lewis Hamilton"),
        ("VER", ver, "Max Verstappen"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=data["LapDistanceNorm"],
                y=data["Throttle"],
                mode="lines",
                name=f"{source} – {name}",
                line=dict(color=COLORS[source], width=2),
                hovertemplate=(
                    f"<b>{source}</b><br>"
                    "Distancia: %{x:.3f}<br>"
                    "Acelerador: %{y:.1f} %%<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text="Posición del acelerador", font=dict(size=15)),
        xaxis_title="Distancia normalizada (0 → 1)",
        yaxis_title="Acelerador (%)",
    )
    return fig


def make_brake_figure():
    fig = go.Figure()
    for source, data, name in [
        ("HAM", ham, "Lewis Hamilton"),
        ("VER", ver, "Max Verstappen"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=data["LapDistanceNorm"],
                y=data["Brake"],
                mode="lines",
                name=f"{source} – {name}",
                line=dict(color=COLORS[source], width=2),
                fill="tozeroy",
                fillcolor=hex_to_rgba(COLORS[source], 0.15),
                hovertemplate=(
                    f"<b>{source}</b><br>"
                    "Distancia: %{x:.3f}<br>"
                    "Freno: %{y:.2f}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text="Uso de frenos", font=dict(size=15)),
        xaxis_title="Distancia normalizada (0 → 1)",
        yaxis_title="Freno (0/1)",
    )
    return fig


def make_delta_figure():
    """Diferencia de tiempo acumulado entre HAM y VER.

    delta = VER_time - HAM_time: positivo significa que VER tardó más en
    llegar a esa distancia, por lo tanto HAM va delante en ese tramo.
    """
    delta = ver["Time_from_start"].values - ham["Time_from_start"].values
    x = ham["LapDistanceNorm"].values

    fig = go.Figure()

    # Área positiva (HAM delante)
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[max(d, 0) for d in delta],
            mode="lines",
            name="HAM delante",
            fill="tozeroy",
            line=dict(color=COLORS["HAM"], width=0),
            fillcolor=hex_to_rgba(COLORS["HAM"], 0.35),
            hoverinfo="skip",
        )
    )
    # Área negativa (VER delante)
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[min(d, 0) for d in delta],
            mode="lines",
            name="VER delante",
            fill="tozeroy",
            line=dict(color=COLORS["VER"], width=0),
            fillcolor=hex_to_rgba(COLORS["VER"], 0.35),
            hoverinfo="skip",
        )
    )
    # Línea del delta
    fig.add_trace(
        go.Scatter(
            x=x,
            y=delta,
            mode="lines",
            name="Δ tiempo (VER – HAM)",
            line=dict(color="#ffffff", width=1.5),
            hovertemplate=(
                "Distancia: %{x:.3f}<br>"
                "Δt VER–HAM: %{y:.3f} s<extra></extra>"
            ),
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["subtext"])
    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text="Delta de tiempo acumulado (VER − HAM)", font=dict(size=15)),
        xaxis_title="Distancia normalizada (0 → 1)",
        yaxis_title="Δ tiempo (s)",
    )
    return fig


# Precompute
fig_speed = make_speed_figure()
fig_throttle = make_throttle_figure()
fig_brake = make_brake_figure()
fig_delta = make_delta_figure()

# ---------------------------------------------------------------------------
# Estadísticas de resumen
# ---------------------------------------------------------------------------
ham_lap = ham["Time_seconds"].max()
ver_lap = ver["Time_seconds"].max()
ham_vmax = ham["Speed"].max()
ver_vmax = ver["Speed"].max()

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
STAT_CARD_STYLE = dict(
    backgroundColor=COLORS["card"],
    borderRadius="8px",
    padding="14px 20px",
    textAlign="center",
    minWidth="160px",
)

app = dash.Dash(
    __name__,
    title="F1 Telemetría – Abu Dhabi 2021",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.layout = html.Div(
    style={"backgroundColor": COLORS["bg"], "minHeight": "100vh", "fontFamily": "Arial, sans-serif"},
    children=[
        # ── Header ──────────────────────────────────────────────────────────
        html.Div(
            style={
                "background": f"linear-gradient(135deg, {COLORS['surface']} 0%, {COLORS['card']} 100%)",
                "padding": "24px 32px",
                "borderBottom": f"2px solid {COLORS['card']}",
            },
            children=[
                html.H1(
                    "🏎️  Telemetría F1 – Abu Dhabi 2021 · Clasificación",
                    style={"color": COLORS["text"], "margin": "0", "fontSize": "1.6rem"},
                ),
                html.P(
                    "Comparativa de la vuelta más rápida: Lewis Hamilton vs Max Verstappen",
                    style={"color": COLORS["subtext"], "margin": "6px 0 0"},
                ),
            ],
        ),

        # ── Stats row ────────────────────────────────────────────────────────
        html.Div(
            style={
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "16px",
                "padding": "24px 32px 8px",
                "justifyContent": "center",
            },
            children=[
                # HAM lap time
                html.Div(
                    style={**STAT_CARD_STYLE, "borderLeft": f"4px solid {COLORS['HAM']}"},
                    children=[
                        html.P("HAM · Tiempo de vuelta", style={"color": COLORS["subtext"], "margin": "0", "fontSize": "0.75rem"}),
                        html.H3(f"{ham_lap:.3f} s", style={"color": COLORS["HAM"], "margin": "4px 0 0", "fontSize": "1.5rem"}),
                    ],
                ),
                # VER lap time
                html.Div(
                    style={**STAT_CARD_STYLE, "borderLeft": f"4px solid {COLORS['VER']}"},
                    children=[
                        html.P("VER · Tiempo de vuelta", style={"color": COLORS["subtext"], "margin": "0", "fontSize": "0.75rem"}),
                        html.H3(f"{ver_lap:.3f} s", style={"color": COLORS["VER"], "margin": "4px 0 0", "fontSize": "1.5rem"}),
                    ],
                ),
                # Gap
                html.Div(
                    style={**STAT_CARD_STYLE, "borderLeft": "4px solid #ffffff"},
                    children=[
                        html.P("Diferencia (HAM − VER)", style={"color": COLORS["subtext"], "margin": "0", "fontSize": "0.75rem"}),
                        html.H3(
                            f"{ham_lap - ver_lap:+.3f} s",
                            style={"color": "#ffffff", "margin": "4px 0 0", "fontSize": "1.5rem"},
                        ),
                    ],
                ),
                # HAM vmax
                html.Div(
                    style={**STAT_CARD_STYLE, "borderLeft": f"4px solid {COLORS['HAM']}"},
                    children=[
                        html.P("HAM · Vel. máxima", style={"color": COLORS["subtext"], "margin": "0", "fontSize": "0.75rem"}),
                        html.H3(f"{ham_vmax:.0f} km/h", style={"color": COLORS["HAM"], "margin": "4px 0 0", "fontSize": "1.5rem"}),
                    ],
                ),
                # VER vmax
                html.Div(
                    style={**STAT_CARD_STYLE, "borderLeft": f"4px solid {COLORS['VER']}"},
                    children=[
                        html.P("VER · Vel. máxima", style={"color": COLORS["subtext"], "margin": "0", "fontSize": "0.75rem"}),
                        html.H3(f"{ver_vmax:.0f} km/h", style={"color": COLORS["VER"], "margin": "4px 0 0", "fontSize": "1.5rem"}),
                    ],
                ),
            ],
        ),

        # ── Selector de métrica ──────────────────────────────────────────────
        html.Div(
            style={"padding": "8px 32px 0"},
            children=[
                html.Label("Selecciona la vista:", style={"color": COLORS["subtext"], "fontSize": "0.85rem"}),
                dcc.RadioItems(
                    id="chart-selector",
                    options=[
                        {"label": " Velocidad", "value": "speed"},
                        {"label": " Acelerador", "value": "throttle"},
                        {"label": " Frenos", "value": "brake"},
                        {"label": " Delta de tiempo", "value": "delta"},
                        {"label": " Vista completa", "value": "all"},
                    ],
                    value="all",
                    inline=True,
                    style={"color": COLORS["text"], "marginTop": "6px"},
                    inputStyle={"marginRight": "4px", "marginLeft": "14px"},
                ),
            ],
        ),

        # ── Charts ───────────────────────────────────────────────────────────
        html.Div(id="charts-container", style={"padding": "16px 32px 32px"}),
    ],
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("charts-container", "children"),
    Input("chart-selector", "value"),
)
def update_charts(selection):
    chart_map = {
        "speed":    ("Velocidad", fig_speed),
        "throttle": ("Acelerador", fig_throttle),
        "brake":    ("Frenos", fig_brake),
        "delta":    ("Delta de tiempo", fig_delta),
    }

    card_style = dict(
        backgroundColor=COLORS["surface"],
        borderRadius="8px",
        padding="8px",
        marginBottom="16px",
        border=f"1px solid {COLORS['card']}",
    )

    if selection == "all":
        return [
            html.Div(
                style=card_style,
                children=dcc.Graph(figure=fig, config={"displayModeBar": False}),
            )
            for _, fig in chart_map.values()
        ]

    _, fig = chart_map[selection]
    return html.Div(
        style=card_style,
        children=dcc.Graph(
            figure=fig,
            style={"height": "65vh"},
            config={"displayModeBar": True},
        ),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
