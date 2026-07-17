"""
Adaptadores: convierten telemetría de simuladores al schema canónico.

Regla de oro: un adaptador SOLO traduce columnas y unidades. Toda la lógica
de alineación, deltas y estadísticas vive en f1core.prepare y funciona igual
para cualquier fuente.

Disponibles:
    assetto_corsa → CSV exportado de MoTeC i2 / ACTI, o captura UDP propia.
    forza         → captura UDP del "Data Out" de Forza Motorsport / Horizon.
"""

from . import assetto_corsa, forza
