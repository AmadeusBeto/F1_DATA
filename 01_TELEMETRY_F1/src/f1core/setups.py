"""
Configuraciones de vehículo (setups).

¿Por qué guardar setups como JSON separado de la telemetría?
    Un setup describe el ESTADO del coche (muelles, alerones, presiones);
    la telemetría describe su COMPORTAMIENTO. Se relacionan por `setup_id`
    en los metadatos del dataset. Así puedes correr el mismo circuito con
    dos setups, etiquetar cada traza y ver en el dashboard qué cambio
    mecánico produjo qué cambio de comportamiento.

Estructura: ver data/template/setup_template.json y docs/SIM_TELEMETRY.md.
"""

from __future__ import annotations

import json
import os

#: Secciones esperadas en un setup. Solo 'meta' es obligatoria: los sims
#: exponen parámetros distintos y un setup parcial sigue siendo útil.
SETUP_SECTIONS = ("meta", "aero", "suspension", "tyres", "brakes",
                  "differential", "gearing", "fuel")


def load_setup(path: str) -> dict:
    """Carga y valida un setup JSON."""
    with open(path, encoding="utf-8") as fh:
        setup = json.load(fh)
    ok, issues = validate_setup(setup)
    for msg in issues:
        print(f"  [{os.path.basename(path)}] {msg}")
    if not ok:
        raise ValueError(f"Setup inválido: {path}")
    return setup


def validate_setup(setup: dict) -> tuple[bool, list[str]]:
    """Reglas mínimas: 'meta' con setup_id y car; secciones conocidas."""
    issues = []
    ok = True

    meta = setup.get("meta")
    if not isinstance(meta, dict):
        return False, ["ERROR: falta la sección 'meta'"]
    for key in ("setup_id", "car"):
        if not meta.get(key):
            ok = False
            issues.append(f"ERROR: meta.{key} es obligatorio")

    unknown = [k for k in setup if k not in SETUP_SECTIONS]
    if unknown:
        issues.append(f"AVISO: secciones no estándar: {unknown}")
    return ok, issues


def compare_setups(setup_a: dict, setup_b: dict) -> list[dict]:
    """Diff plano entre dos setups: qué parámetros cambian y cuánto.

    ¿Por qué? Al comparar dos vueltas con setups distintos, lo primero que
    quieres en el reporte es la lista exacta de diferencias mecánicas.
    """
    flat_a = _flatten(setup_a)
    flat_b = _flatten(setup_b)
    diffs = []
    for key in sorted(set(flat_a) | set(flat_b)):
        va, vb = flat_a.get(key), flat_b.get(key)
        if va != vb:
            row = {"parameter": key, "a": va, "b": vb}
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                row["change"] = round(vb - va, 4)
            diffs.append(row)
    return diffs


def _flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out
