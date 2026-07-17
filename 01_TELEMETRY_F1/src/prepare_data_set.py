"""
CLI para descargar y preparar datasets de F1 (FastF1) en formato canónico.

Ejemplos:
    # Comportamiento clásico del proyecto (Abu Dhabi 2021, HAM vs VER):
    python prepare_data_set.py

    # Cualquier otra sesión / pilotos:
    python prepare_data_set.py --year 2024 --gp Monza --session Q --drivers LEC NOR
    python prepare_data_set.py --year 2025 --gp "Sao Paulo" --session R --drivers VER NOR PIA

    # Ver el calendario de un año (para saber los nombres de GP):
    python prepare_data_set.py --list-events 2025

El resultado (<gp>_<año>_comparison.csv + .meta.json) aparece automáticamente
en el dropdown del dashboard.
"""

from __future__ import annotations

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from f1core.download import download_comparison, list_available_events  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga telemetría F1 y genera un dataset canónico.")
    parser.add_argument("--year", type=int, default=2021, help="Temporada")
    parser.add_argument("--gp", type=str, default="Abu Dhabi",
                        help="Nombre del GP (o número de ronda)")
    parser.add_argument("--session", type=str, default="Q",
                        help="FP1/FP2/FP3/Q/SQ/S/R")
    parser.add_argument("--drivers", nargs="+", default=["HAM", "VER"],
                        help="Códigos de piloto (HAM VER LEC ...)")
    parser.add_argument("--points", type=int, default=1000,
                        help="Puntos de la malla de alineación")
    parser.add_argument("--list-events", type=int, metavar="YEAR",
                        help="Muestra el calendario del año y sale")
    args = parser.parse_args()

    if args.list_events:
        print(list_available_events(args.list_events).to_string(index=False))
        return

    download_comparison(
        year=args.year,
        gp=args.gp,
        session_type=args.session,
        drivers=args.drivers,
        n_points=args.points,
    )
    print("\nListo. Arranca el dashboard con: python dashboard.py")


if __name__ == "__main__":
    main()
