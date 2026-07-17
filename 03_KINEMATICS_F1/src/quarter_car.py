"""
Modelo quarter-car de la suspensión delantera (proyecto 02_SUSPENSION_F1).

¿Qué es un quarter-car y por qué lo usamos?
    Es el modelo mínimo que captura la física vertical de UNA esquina del
    coche: masa suspendida (chasis) sobre muelle+amortiguador, masa no
    suspendida (rueda/manguita) sobre la rigidez vertical del neumático.
    Con solo 6 parámetros predice recorridos de suspensión, frecuencias
    propias y amortiguamiento — suficiente para validar si la geometría
    diseñada en CAD se comporta como esperamos ante datos reales.

¿Por qué importa el motion ratio (MR)?
    El muelle no está en la rueda: la fuerza pasa por el push/pull-rod y el
    rocker. MR = recorrido de rueda / recorrido de muelle. Por conservación
    de energía, la rigidez "vista" en la rueda es k_wheel = k_spring / MR².
    Un error del 10% en MR es ~20% de error en rigidez: por eso hay que
    medirlo en el CAD, no estimarlo.

Dos modos de uso:
    1. Cuasi-estático (predict_front_travel): a partir de aceleraciones y
       velocidad de la telemetría, predice el recorrido de suspensión punto
       a punto. Es lo que se compara contra los canales SuspTravel_* de
       Assetto Corsa.
    2. Dinámico (simulate): integra las 2 masas en el tiempo ante un perfil
       de carretera. Sirve para entender frecuencias y ajustar amortiguador.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

G = 9.81  # m/s²

DEFAULT_GEOMETRY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "geometry.json")


def load_geometry(path: str | None = None) -> dict:
    """Carga geometry.json y avisa si sigue siendo la geometría estimada.

    ¿Por qué avisar? Para que ningún resultado con placeholders se confunda
    con una validación del diseño real de 02_SUSPENSION_F1.
    """
    path = path or DEFAULT_GEOMETRY
    with open(path, encoding="utf-8") as fh:
        geo = json.load(fh)
    if geo.get("car", {}).get("estimated") or geo.get("front_corner", {}).get("estimated"):
        print("[AVISO] geometry.json contiene valores ESTIMADOS - reemplazalos "
              "midiendo el CAD de 02_SUSPENSION_F1 antes de sacar conclusiones.")
    return geo


def wheel_rate(geo: dict) -> float:
    """Rigidez efectiva en la rueda (N/mm): k_spring / MR²."""
    fc = geo["front_corner"]
    return fc["spring_rate_N_per_mm"] / fc["motion_ratio"] ** 2


def natural_modes(geo: dict) -> dict:
    """Frecuencias propias y amortiguamiento del quarter-car.

    ¿Para qué? Son el "carnet de identidad" dinámico de la suspensión:
        - Modo de masa suspendida (heave): en F1 suele estar en 3–5 Hz
          (un coche de calle está en 1–1.5 Hz). Si tu diseño sale fuera de
          ese orden, hay un error de rigidez o de MR.
        - Modo de masa no suspendida (wheel hop): típicamente 15–25 Hz;
          lo controla el neumático.
        - zeta (ratio de amortiguamiento): ~0.3–0.7 en competición.
    """
    car, fc = geo["car"], geo["front_corner"]
    m_corner = car["mass_total_kg"] * car["weight_dist_front"] / 2.0
    ms = m_corner - fc["unsprung_mass_kg"]          # masa suspendida (kg)
    mu = fc["unsprung_mass_kg"]                     # masa no suspendida (kg)
    kw = wheel_rate(geo) * 1000.0                   # N/m
    kt = fc["tire_vertical_stiffness_N_per_mm"] * 1000.0
    cw = (fc["damper_coeff_Ns_per_mm"] / fc["motion_ratio"] ** 2) * 1000.0

    # Serie muelle+neumático para el modo de heave (ride rate)
    ride_rate = kw * kt / (kw + kt)
    f_sprung = np.sqrt(ride_rate / ms) / (2 * np.pi)
    f_unsprung = np.sqrt((kw + kt) / mu) / (2 * np.pi)
    zeta = cw / (2 * np.sqrt(kw * ms))

    return {
        "sprung_mass_kg": round(ms, 1),
        "wheel_rate_N_per_mm": round(kw / 1000.0, 1),
        "ride_rate_N_per_mm": round(ride_rate / 1000.0, 1),
        "f_sprung_Hz": round(f_sprung, 2),
        "f_unsprung_Hz": round(f_unsprung, 2),
        "damping_ratio": round(zeta, 3),
    }


# ---------------------------------------------------------------------------
# Modo 1: predicción cuasi-estática desde telemetría
# ---------------------------------------------------------------------------

def front_wheel_loads(df: pd.DataFrame, geo: dict) -> pd.DataFrame:
    """Carga vertical en cada rueda delantera a partir de la telemetría.

    Física (todo cuasi-estático, es decir, ignorando transitorios):
        F_rueda = estático + aero + transferencia longitudinal + lateral

        - Estático: m·g repartido según weight_dist_front.
        - Aero: crece con v² — en un F1 domina sobre todo lo demás a alta
          velocidad, por eso el coche "se aplasta" en las rectas.
        - Longitudinal: frenar (ax<0) carga el eje delantero: Δ = -m·ax·h/L.
        - Lateral: en curva la rueda exterior gana lo que pierde la interior:
          Δ = ±m·ay·h/track · reparto_delantero.

    Requiere columnas: Speed (km/h), LongAccel y LatAccel (g).
    Devuelve F_FL y F_FR en Newtons.
    """
    car = geo["car"]
    m = car["mass_total_kg"]
    h, L, t = car["cg_height_m"], car["wheelbase_m"], car["track_front_m"]

    v = df["Speed"].values / 3.6                       # m/s
    ax = df["LongAccel"].values * G                    # m/s²
    ay = df["LatAccel"].values * G

    static = m * G * car["weight_dist_front"] / 2.0
    aero = car["downforce_front_N_per_ms2"] * v ** 2 / 2.0
    long_tr = -m * ax * h / (2.0 * L)
    lat_tr = m * ay * h / t * car["lat_transfer_front_share"] / 1.0

    # Convención de signos: ay > 0 desplaza carga hacia la rueda izquierda.
    # Si tu sim usa la convención opuesta, la validación lo detecta como
    # correlación negativa en un lado: invierte el signo aquí.
    return pd.DataFrame({
        "F_FL": static + aero + long_tr + lat_tr,
        "F_FR": static + aero + long_tr - lat_tr,
    }, index=df.index)


def predict_front_travel(df: pd.DataFrame, geo: dict) -> pd.DataFrame:
    """Predice el recorrido de suspensión delantero (mm) que debería medir
    el sensor, punto a punto de la vuelta.

    Cadena de conversión:
        carga rueda (N) → deflexión de rueda = F/k_wheel → deflexión del
        sensor: si el potenciómetro está en el amortiguador (caso MoTeC),
        recorrido_sensor = recorrido_rueda / MR.

    El cero del sensor es arbitrario (depende de dónde se montó), así que
    la comparación válida es en VARIACIONES: ambas señales se centran en su
    media antes de comparar. Lo que validamos es la GANANCIA (rigidez+MR
    correctos) y la FORMA (la física de transferencias), no el offset.
    """
    fc = geo["front_corner"]
    loads = front_wheel_loads(df, geo)
    kw = wheel_rate(geo)                               # N/mm en la rueda

    out = pd.DataFrame(index=df.index)
    for corner in ("FL", "FR"):
        wheel_mm = loads[f"F_{corner}"] / kw
        if fc.get("sensor_measures", "spring") == "spring":
            out[f"PredTravel_{corner}"] = wheel_mm / fc["motion_ratio"]
        else:
            out[f"PredTravel_{corner}"] = wheel_mm
    return out


# ---------------------------------------------------------------------------
# Modo 2: simulación dinámica 2-DOF
# ---------------------------------------------------------------------------

def simulate(geo: dict, t: np.ndarray, z_road: np.ndarray) -> dict:
    """Integra el quarter-car (2 grados de libertad) sobre un perfil de pista.

    Estados: [z_s, vz_s, z_u, vz_u] (masa suspendida y no suspendida).
    Integrador RK4 propio con numpy — sin dependencia de scipy, y el paso
    fijo es suficiente porque el sistema es lineal y las frecuencias están
    acotadas (<30 Hz).

    ¿Para qué sirve si ya tenemos el modo cuasi-estático?
        Para lo que aquel no ve: la respuesta TRANSITORIA. Pianos, bumps y
        kerbs excitan los modos propios; aquí se ve si el amortiguador los
        controla o el coche rebota.

    Returns:
        dict con z_s, z_u (m) y travel_sensor_mm (lo que mediría el pot).
    """
    car, fc = geo["car"], geo["front_corner"]
    m_corner = car["mass_total_kg"] * car["weight_dist_front"] / 2.0
    ms = m_corner - fc["unsprung_mass_kg"]
    mu = fc["unsprung_mass_kg"]
    kw = wheel_rate(geo) * 1000.0
    cw = (fc["damper_coeff_Ns_per_mm"] / fc["motion_ratio"] ** 2) * 1000.0
    kt = fc["tire_vertical_stiffness_N_per_mm"] * 1000.0

    def deriv(state, zr):
        zs, vs, zu, vu = state
        f_susp = kw * (zu - zs) + cw * (vu - vs)      # muelle+amortiguador
        f_tire = kt * (zr - zu)                        # neumático
        return np.array([vs, f_susp / ms, vu, (f_tire - f_susp) / mu])

    n = len(t)
    states = np.zeros((n, 4))
    for i in range(n - 1):
        dt = t[i + 1] - t[i]
        s, zr = states[i], z_road[i]
        k1 = deriv(s, zr)
        k2 = deriv(s + dt / 2 * k1, zr)
        k3 = deriv(s + dt / 2 * k2, zr)
        k4 = deriv(s + dt * k3, z_road[i + 1])
        states[i + 1] = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

    travel_wheel_m = states[:, 2] - states[:, 0]       # z_u - z_s
    travel_sensor = travel_wheel_m * 1000.0
    if fc.get("sensor_measures", "spring") == "spring":
        travel_sensor = travel_sensor / fc["motion_ratio"]

    return {"t": t, "z_s": states[:, 0], "z_u": states[:, 2],
            "travel_sensor_mm": travel_sensor}


if __name__ == "__main__":
    geo = load_geometry()
    print("\nModos propios del quarter-car delantero:")
    for k, v in natural_modes(geo).items():
        print(f"  {k:>22}: {v}")
