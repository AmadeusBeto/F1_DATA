"""
test_sector_analysis.py
=======================
Tests unitarios para sector_analysis.py

Cómo ejecutar:
    pytest tests/test_sector_analysis.py -v

Qué es un test unitario:
    Una función pequeña que verifica que otra función hace exactamente
    lo que esperamos. Cada test tiene tres partes:
        1. ARRANGE  → preparar los datos de entrada
        2. ACT      → llamar la función que queremos probar
        3. ASSERT   → verificar que el resultado es correcto

Si un test falla, sabemos exactamente qué función se rompió y por qué.
Eso es mucho mejor que descubrirlo en producción.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Hacer que Python encuentre nuestro módulo aunque
# el test se ejecute desde cualquier directorio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sector_analysis import (
    detect_brake_zones,
    compute_sectors,
    compute_brake_comparison,
    compute_lap_summary,
    run_full_analysis,
)


# ---------------------------------------------------------------------------
# Fixtures: datos de prueba reutilizables
# ---------------------------------------------------------------------------
# Un "fixture" en pytest es una función que crea datos de prueba.
# El decorador @pytest.fixture le dice a pytest que la puede inyectar
# automáticamente en cualquier test que la pida como argumento.

@pytest.fixture
def simple_df():
    n = 100
    dist = np.linspace(0, 1, n)

    def make_driver(name, brake_at=(20, 60)):
        brake = np.zeros(n)
        speed = np.full(n, 200.0)
        time  = np.linspace(0, 85.0, n)

        for start in brake_at:
            end = min(start + 5, n)
            brake[start:end] = 1.0
            speed[start:end] = np.linspace(200, 100, end - start)

        return pd.DataFrame({
            'LapDistanceNorm': dist,
            'Speed':           speed,
            'Throttle':        np.full(n, 80.0),
            'Brake':           brake,
            'Time_seconds':    time + 3600.0,
            'Time_from_start': time,
            'Source':          pd.Series([name] * n),  # ← esto era el bug
            'GP':              pd.Series(['Test GP'] * n),
            'Year':            pd.Series([2024] * n),
            'Session':         pd.Series(['Q'] * n),
        })

    return pd.concat([make_driver('HAM'), make_driver('VER', brake_at=(19, 59))], ignore_index=True)


@pytest.fixture
def real_df():
    """
    Carga el CSV real de Abu Dhabi 2021 si existe.
    Si no existe, salta el test (no lo falla).
    """
    path = os.path.join(
        os.path.dirname(__file__), '..', 'data',
        'abu_dhabi_2021_Q_comparison.csv'
    )
    if not os.path.exists(path):
        pytest.skip("CSV real no disponible — ejecuta prepare_data_set.py primero")
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Tests de detect_brake_zones
# ---------------------------------------------------------------------------

class TestDetectBrakeZones:

    def test_returns_list(self, simple_df):
        # ARRANGE: ya tenemos simple_df
        # ACT
        result = detect_brake_zones(simple_df, 'HAM')
        # ASSERT
        assert isinstance(result, list), "Debe devolver una lista"

    def test_detects_correct_number_of_zones(self, simple_df):
        result = detect_brake_zones(simple_df, 'HAM')
        # Creamos 2 frenadas en el fixture, debe detectar 2
        assert len(result) == 2, f"Se esperaban 2 zonas, se detectaron {len(result)}"

    def test_zone_has_required_fields(self, simple_df):
        result = detect_brake_zones(simple_df, 'HAM')
        required = {
            'driver', 'dist_start', 'dist_end', 'duration_norm',
            'speed_entry', 'speed_min', 'speed_exit', 'delta_speed',
            'time_start', 'time_end'
        }
        for zone in result:
            missing = required - set(zone.keys())
            assert not missing, f"Faltan campos en zona: {missing}"

    def test_zones_sorted_by_distance(self, simple_df):
        result = detect_brake_zones(simple_df, 'HAM')
        dists = [z['dist_start'] for z in result]
        assert dists == sorted(dists), "Las zonas deben estar ordenadas por distancia"

    def test_speed_entry_greater_than_min(self, simple_df):
        result = detect_brake_zones(simple_df, 'HAM')
        for zone in result:
            assert zone['speed_entry'] >= zone['speed_min'], \
                f"La velocidad de entrada ({zone['speed_entry']}) debe ser >= mínima ({zone['speed_min']})"

    def test_delta_speed_positive(self, simple_df):
        result = detect_brake_zones(simple_df, 'HAM')
        for zone in result:
            assert zone['delta_speed'] >= 0, "delta_speed nunca puede ser negativo"

    def test_invalid_driver_returns_empty(self, simple_df):
        result = detect_brake_zones(simple_df, 'NOEXISTE')
        assert result == [], "Piloto inválido debe devolver lista vacía"

    def test_with_real_data(self, real_df):
        result = detect_brake_zones(real_df, 'HAM')
        assert len(result) >= 5, "Abu Dhabi tiene al menos 5 zonas de frenada fuerte"
        assert len(result) <= 15, "Abu Dhabi no tiene más de 15 zonas de frenada"


# ---------------------------------------------------------------------------
# Tests de compute_sectors
# ---------------------------------------------------------------------------

class TestComputeSectors:

    def test_returns_list(self, simple_df):
        result = compute_sectors(simple_df, 'HAM', 'VER')
        assert isinstance(result, list)

    def test_sectors_have_required_fields(self, simple_df):
        result = compute_sectors(simple_df, 'HAM', 'VER')
        required = {'sector_num', 'dist_start', 'dist_end', 'delta', 'winner', 'gap_ms'}
        for s in result:
            missing = required - set(s.keys())
            assert not missing, f"Faltan campos: {missing}"

    def test_times_are_positive(self, simple_df):
        result = compute_sectors(simple_df, 'HAM', 'VER')
        for s in result:
            assert s.get('time_ham', 1) > 0, "Tiempo HAM debe ser positivo"
            assert s.get('time_ver', 1) > 0, "Tiempo VER debe ser positivo"

    def test_winner_matches_delta(self, simple_df):
        result = compute_sectors(simple_df, 'HAM', 'VER')
        for s in result:
            if s['delta'] < 0:
                assert s['winner'] == 'VER', \
                    f"Delta negativo ({s['delta']}) debería tener winner=VER, no {s['winner']}"
            elif s['delta'] > 0:
                assert s['winner'] == 'HAM', \
                    f"Delta positivo ({s['delta']}) debería tener winner=HAM, no {s['winner']}"
            # delta == 0.0 o -0.0: empate, cualquier ganador es válido

    def test_gap_ms_is_absolute(self, simple_df):
        result = compute_sectors(simple_df, 'HAM', 'VER')
        for s in result:
            assert s['gap_ms'] >= 0, "gap_ms siempre debe ser positivo (es absoluto)"

    def test_sectors_sequential(self, simple_df):
        result = compute_sectors(simple_df, 'HAM', 'VER')
        nums = [s['sector_num'] for s in result]
        assert nums == list(range(1, len(nums) + 1)), "Los sectores deben ser consecutivos"

    def test_with_real_data(self, real_df):
        result = compute_sectors(real_df, 'HAM', 'VER')
        assert len(result) >= 4, "Abu Dhabi debe tener al menos 4 sectores"
        total_delta = sum(s['delta'] for s in result)
        # VER fue más rápido en Abu Dhabi 2021 Q, delta total debe ser negativo
        assert total_delta < 0, f"VER debió ser más rápido en total. Delta={total_delta:.3f}"


# ---------------------------------------------------------------------------
# Tests de compute_lap_summary
# ---------------------------------------------------------------------------

class TestComputeLapSummary:

    def test_returns_dict(self, simple_df):
        result = compute_lap_summary(simple_df)
        assert isinstance(result, dict)

    def test_has_both_drivers(self, simple_df):
        result = compute_lap_summary(simple_df)
        assert 'HAM' in result['lap_times']
        assert 'VER' in result['lap_times']

    def test_lap_times_are_positive(self, simple_df):
        result = compute_lap_summary(simple_df)
        for drv, t in result['lap_times'].items():
            assert t > 0, f"Tiempo de vuelta de {drv} debe ser positivo"

    def test_gap_is_positive(self, simple_df):
        result = compute_lap_summary(simple_df)
        assert result['gap'] >= 0, "El gap entre pilotos siempre es positivo"

    def test_fastest_driver_has_shortest_time(self, simple_df):
        result = compute_lap_summary(simple_df)
        fastest = result['fastest_driver']
        slowest = [d for d in result['drivers'] if d != fastest][0]
        assert result['lap_times'][fastest] <= result['lap_times'][slowest], \
            "El piloto más rápido debe tener el menor tiempo"

    def test_with_real_data(self, real_df):
        result = compute_lap_summary(real_df)
        # En Abu Dhabi 2021 Q, VER hizo la pole
        assert result['fastest_driver'] == 'VER', \
            f"VER hizo la pole en Abu Dhabi 2021 Q. fastest={result['fastest_driver']}"
        # Tiempos realistas de vuelta en F1 (entre 60s y 120s)
        for drv, t in result['lap_times'].items():
            assert 60 < t < 120, f"Tiempo de vuelta de {drv} fuera de rango: {t:.3f}s"


# ---------------------------------------------------------------------------
# Tests de run_full_analysis (integración)
# ---------------------------------------------------------------------------

class TestRunFullAnalysis:

    def test_returns_all_keys(self, simple_df):
        result = run_full_analysis(simple_df)
        required = {'summary', 'sectors', 'brake_zones', 'brake_comparison', 'drivers'}
        missing = required - set(result.keys())
        assert not missing, f"Faltan claves en resultado: {missing}"

    def test_brake_zones_for_all_drivers(self, simple_df):
        result = run_full_analysis(simple_df)
        for drv in result['drivers']:
            assert drv in result['brake_zones'], f"Faltan zonas para {drv}"

    def test_raises_with_single_driver(self, simple_df):
        # Solo un piloto → debe lanzar ValueError
        df_one = simple_df[simple_df['Source'] == 'HAM']
        with pytest.raises(ValueError):
            run_full_analysis(df_one)

    def test_with_real_data(self, real_df):
        result = run_full_analysis(real_df)
        assert result['summary']['fastest_driver'] == 'VER'
        assert len(result['sectors']) >= 4
        assert len(result['brake_comparison']) >= 5