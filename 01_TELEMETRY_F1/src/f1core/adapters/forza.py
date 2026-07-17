"""
Adaptador de Forza (Motorsport / Horizon) → schema canónico.

Cómo sacar telemetría de Forza (función nativa, sin mods):
    1. En el juego: Ajustes → HUD → "Salida de datos" (Data Out) → ON.
    2. IP: la de tu PC de captura (127.0.0.1 si es la misma máquina).
    3. Puerto: 5300 (o el que elijas).
    4. Ejecutar capture_udp() ANTES de rodar la vuelta.

Forza transmite un paquete UDP binario por tick (~60 Hz). El layout depende
del juego; esta librería lo detecta por el tamaño del paquete:
    232 bytes → FM7 "Sled" (sin velocidad/pedales: usa modo Dash mejor)
    311 bytes → FM7 "Dash"
    324 bytes → FH4 / FH5 (Dash con 12 bytes extra tras el Sled)
    331 bytes → Forza Motorsport (2023)

Flujo completo:
    raw = capture_udp(port=5300, duration_s=120)      # graba mientras ruedas
    lap = extract_lap(raw, lap_number=1)              # aísla una vuelta
    df  = to_canonical(lap, source_label="FM_SetupA") # schema canónico
"""

from __future__ import annotations

import os
import socket
import struct
import time

import pandas as pd

#: offset del bloque "Dash" según tamaño de paquete.
_DASH_OFFSET = {311: 232, 324: 244, 331: 232}


def capture_udp(port: int = 5300, duration_s: float = 120.0,
                out_csv: str | None = None, host: str = "0.0.0.0") -> pd.DataFrame:
    """Captura el stream Data Out de Forza y lo decodifica a un DataFrame crudo.

    ¿Por qué grabar crudo primero? Separar captura de procesamiento te deja
    re-procesar la sesión (elegir otra vuelta, otro recorte) sin volver a rodar.

    Args:
        port: puerto UDP configurado en el juego.
        duration_s: segundos de captura (graba la sesión completa).
        out_csv: si se indica, guarda el crudo ahí.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(2.0)
    print(f"[..] Escuchando UDP en {host}:{port} durante {duration_s:.0f}s — ¡a rodar!")

    rows = []
    t_end = time.time() + duration_s
    try:
        while time.time() < t_end:
            try:
                packet, _ = sock.recvfrom(1024)
            except socket.timeout:
                continue
            row = _parse_packet(packet)
            if row is not None:
                rows.append(row)
    finally:
        sock.close()

    df = pd.DataFrame(rows)
    print(f"[OK] Capturados {len(df)} ticks")
    if out_csv and not df.empty:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        df.to_csv(out_csv, index=False)
        print(f"[OK] Crudo guardado: {out_csv}")
    return df


def _parse_packet(packet: bytes) -> dict | None:
    """Decodifica un paquete Data Out. Devuelve None si está pausado o es Sled."""
    size = len(packet)
    if size not in _DASH_OFFSET:
        return None

    is_race_on = struct.unpack_from("<i", packet, 0)[0]
    if not is_race_on:  # juego en pausa / menú
        return None

    d = _DASH_OFFSET[size]
    f = lambda off: struct.unpack_from("<f", packet, off)[0]
    u8 = lambda off: struct.unpack_from("<B", packet, off)[0]
    s8 = lambda off: struct.unpack_from("<b", packet, off)[0]

    row = {
        "TimestampMS": struct.unpack_from("<I", packet, 4)[0],
        "RPM": f(16),
        # Sled: aceleraciones en el sistema del coche (m/s²) → g
        "LatAccel": f(20) / 9.80665,
        "LongAccel": f(28) / 9.80665,
        # Recorrido de suspensión en metros → mm
        "SuspTravel_FL": f(196) * 1000, "SuspTravel_FR": f(200) * 1000,
        "SuspTravel_RL": f(204) * 1000, "SuspTravel_RR": f(208) * 1000,
        # Dash
        "X": f(d + 0), "Y": f(d + 8),           # posición (X, Z en el juego)
        "Speed": f(d + 12) * 3.6,               # m/s → km/h
        "TyreTempC_FL": (f(d + 24) - 32) / 1.8,  # °F → °C
        "TyreTempC_FR": (f(d + 28) - 32) / 1.8,
        "TyreTempC_RL": (f(d + 32) - 32) / 1.8,
        "TyreTempC_RR": (f(d + 36) - 32) / 1.8,
        "FuelLevel": f(d + 44),
        "DistanceTraveled": f(d + 48),
        "CurrentLapTime": f(d + 60),
        "LapNumber": struct.unpack_from("<H", packet, d + 68)[0],
        "Throttle": u8(d + 71) / 255 * 100,
        "Brake": u8(d + 72) / 255 * 100,
        "Gear": u8(d + 75),
        "SteerAngle": s8(d + 76) / 127 * 100,   # -100 a 100 (% de giro)
    }
    return row


def extract_lap(raw: pd.DataFrame, lap_number: int | None = None) -> pd.DataFrame:
    """Aísla una vuelta del crudo capturado.

    En Motorsport / carreras de Horizon, LapNumber y CurrentLapTime son
    fiables. En mundo abierto de Horizon no hay vueltas: usa recorte manual
    por DistanceTraveled (raw[(raw.DistanceTraveled > a) & (< b)]).
    """
    if lap_number is None:
        # La vuelta completa más rápida (excluye la vuelta de salida 0)
        laps = raw[raw["LapNumber"] > 0].groupby("LapNumber")["CurrentLapTime"].max()
        if laps.empty:
            raise ValueError("No hay vueltas completas; recorta por DistanceTraveled.")
        lap_number = int(laps.idxmin())
        print(f"[OK] Vuelta más rápida detectada: {lap_number} ({laps.min():.3f}s)")

    lap = raw[raw["LapNumber"] == lap_number].copy()
    if lap.empty:
        raise ValueError(f"No hay datos para la vuelta {lap_number}")
    return lap.reset_index(drop=True)


def to_canonical(lap: pd.DataFrame, source_label: str = "FORZA") -> pd.DataFrame:
    """Convierte una vuelta cruda de Forza al schema canónico."""
    df = lap.copy()
    df["Time_seconds"] = df["CurrentLapTime"]
    if df["Time_seconds"].max() <= 0:
        # Mundo abierto (sin cronómetro de vuelta): usa el timestamp
        df["Time_seconds"] = (df["TimestampMS"] - df["TimestampMS"].iloc[0]) / 1000

    df["Distance"] = df["DistanceTraveled"] - df["DistanceTraveled"].iloc[0]
    df["LapDistanceNorm"] = df["Distance"] / df["Distance"].max()
    df["Source"] = source_label

    cols = ["LapDistanceNorm", "Speed", "Throttle", "Brake", "Time_seconds",
            "Source", "Distance", "RPM", "Gear", "SteerAngle", "LongAccel",
            "LatAccel", "FuelLevel",
            "SuspTravel_FL", "SuspTravel_FR", "SuspTravel_RL", "SuspTravel_RR",
            "TyreTempC_FL", "TyreTempC_FR", "TyreTempC_RL", "TyreTempC_RR",
            "X", "Y"]
    return df[[c for c in cols if c in df.columns]]


def save_canonical(df: pd.DataFrame, out_dir: str, name: str) -> str:
    """Guarda la traza canónica en data/sim/ lista para build_comparison()."""
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{name}.csv")
    df.to_csv(out_path, index=False)
    print(f"[OK] Telemetría Forza guardada: {out_path}")
    return out_path
