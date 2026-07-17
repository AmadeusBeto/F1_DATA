"""
f1core – Núcleo de datos del proyecto de telemetría F1.

Módulos:
    schema    → Formato canónico de dataset, validación y carga.
    download  → Descarga de datos oficiales vía FastF1.
    prepare   → Alineación, interpolación y cálculo de deltas.
    setups    → Carga y comparación de configuraciones de vehículo.
    adapters  → Conversión de telemetría de simuladores (Assetto Corsa, Forza).
"""

from .schema import (
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
    validate_dataset,
    load_dataset,
    load_metadata,
    list_datasets,
    create_template,
)
from .prepare import align_laps, compute_delta, summary_stats, build_comparison
from .setups import load_setup, validate_setup, compare_setups

__version__ = "1.0.0"
