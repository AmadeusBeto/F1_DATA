"""
sector_analysis.py
==================
F1 telemetry analysis module.

Single responsibility: receive a telemetry DataFrame and return a data structure
containing analysis results.

Main functions:
    detect_brake_zones(df, driver) → list of brake zones
    compute_sectors(df, driver_a, driver_b) → list of sector deltas
    compute_lap_summary(df) → general lap summary

Typical usage:
    df = pd.read_csv('abu_dhabi_2021_Q_comparison.csv')
    zones = detect_brake_zones(df, 'HAM')
    sectors = compute_sectors(df, 'HAM', 'VER')
    summary = compute_lap_summary(df)
"""

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Minimum consecutive points with active braking required to consider
# a real brake zone (noise filtering).
# With 1000 points per lap, 3 points ≈ 0.3% of total lap distance.
MIN_BRAKE_POINTS = 3

# Minimum speed to consider a point as "in motion".
# Filters first/last frames of the CSV that sometimes have v ≈ 0.
MIN_SPEED_KMH = 30.0

# ---------------------------------------------------------------------------
# Function 1: detect_brake_zones
# ---------------------------------------------------------------------------

def detect_brake_zones(df: pd.DataFrame, driver: str) -> list[dict]:
    """
    Detects brake zones for a driver along the lap.

    A "brake zone" is a continuous sequence of points where Brake > 0.
    For each detected zone, the following metrics are calculated:

        - dist_start      : normalized lap position (0 → 1)
        - dist_end        : normalized lap position (0 → 1)
        - speed_entry     : speed at brake entry (km/h)
        - speed_min       : minimum speed within the zone (km/h)
        - speed_exit      : speed at zone exit (km/h)
        - delta_speed     : speed reduction (entry - minimum)
        - duration_norm   : zone length in normalized lap distance
        - time_start      : time from lap start (s)

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns:
        LapDistanceNorm, Speed, Brake, Time_from_start, Source

    driver : str
        Driver code, e.g., 'HAM'
    
    Returns
        -------
        list[dict]
            List sorted by dist_start. Each element is a dictionary
            containing the fields described above.
        """

    # Filter only the data for the requested driver
    d = df[df['Source'] == driver].copy()

    # Make sure the data is sorted by distance, as we do not assume it is sorted by default
    d = d.sort_values('LapDistanceNorm').reset_index(drop=True)

    # Filter very low velocity points (possible noise at the start/end)
    d = d[d['Speed'] >= MIN_SPEED_KMH].reset_index(drop=True)

    zones = []
    in_zone = []
    zone_start_idx = None

    # Iterate point by point looking for Brake transitions (0→1 and 1→0)
    # This is known as "edge detection" — a classic signal processing technique
    for i, row in d.iterrows():
        braking = row['Brake'] > 0

        # Rising edge detected: start of brake zone
        if braking and not in_zone:
            in_zone = True
            zone_start_idx = i
        
        # Faling edge detected: end of the brake zone
        elif not braking and in_zone:
            in_zone = False
            zone_end_idx = i - 1 

            # Extract data of the zone
            zone_data = d.loc[zone_start_idx:zone_end_idx]

            # Filter very short zones (sensor noise)
            if len(zone_data) < MIN_BRAKE_POINTS:
                continue
            
            zones.append({
                'driver': driver,
                'dist_start': float(zone_data['LapDistanceNorm'].iloc[0]),
                'dist_end': float(zone_data['LapDistanceNorm'].iloc[-1]),
                'duration_norm': float(zone_data['LapDistanceNorm'].iloc[-1] - zone_data['LapDistanceNorm'].iloc[0]),
                'speed_entry': float(zone_data['Speed'].iloc[0]),
                'speed_min': float(zone_data['Speed'].min()),
                'speed_exit': float(zone_data['Speed'].iloc[-1]),
                'delta_speed': float(zone_data['Speed'].iloc[0] - zone_data['Speed'].min()),
                'time_start': float(zone_data['Time_from_start'].iloc[0]),
                'time_end': float(zone_data['Time_from_start'].iloc[-1])
            })

    # Try the case where the last zone is at the end of the CSV
    if in_zone and zone_start_idx is not None:
        zone_data = d.loc[zone_start_idx:]
        if len(zone_data) >= MIN_BRAKE_POINTS:
            zones.append({
                'driver':       driver,
                'dist_start':   float(zone_data['LapDistanceNorm'].iloc[0]),
                'dist_end':     float(zone_data['LapDistanceNorm'].iloc[-1]),
                'duration_norm':float(zone_data['LapDistanceNorm'].iloc[-1] - zone_data['LapDistanceNorm'].iloc[0]),
                'speed_entry':  float(zone_data['Speed'].iloc[0]),
                'speed_min':    float(zone_data['Speed'].min()),
                'speed_exit':   float(zone_data['Speed'].iloc[-1]),
                'delta_speed':  float(zone_data['Speed'].iloc[0] - zone_data['Speed'].min()),
                'time_start':   float(zone_data['Time_from_start'].iloc[0]),
                'time_end':     float(zone_data['Time_from_start'.iloc[-1]])
            })

    return sorted(zones, key=lambda z: z['dist_start'])

# ---------------------------------------------------------------------------
# Auxiliar function: Align zones between two pilots
# ---------------------------------------------------------------------------

def _align_brake_zones(zones_a: list[dict], zones_b: list[dict], tolerance: float = 0.03) -> list[tuple]:
    """
    Matches the braking zones of two drivers that correspond
    to the same physical corner.

    A tolerance window in normalized distance is used to
    determine whether two zones represent the "same corner."

    Parameters
    ----------
    zones_a, zones_b : list[dict]
        Output of detect_brake_zones for each driver
    tolerance : float
        Maximum difference in dist_start to consider the same corner.
        0.03 = 3% of the lap ≈ ~150 m on a 5 km circuit

    Returns
    -------
    list[tuple[dict, dict]]
        List of pairs (zone_a, zone_b) corresponding to the same corner
    """
    pairs = []
    used_b = set()

    for za in zones_a:
        best_match = None
        best_dist = float('inf')

        for j, zb in enumerate(zones_b):
            if j in used_b:
                continue
            dist = abs(za['dist_start'] - zb['dist_start'])
            if dist < tolerance and dist < best_dist:
                best_dist = dist
                best_match = j

        if best_match is not None:
            pairs.append((za, zones_b[best_match]))
            used_b.add(best_match)

    return pairs

# ---------------------------------------------------------------------------
# Function two:  compute sectors
# ---------------------------------------------------------------------------

def compute_sectors(df: pd.DataFrame, driver_a: str, driver_b: str) -> list[dict]:
    """
    Divides the lap into sectors using the braking zones as boundaries
    and computes each driver's time in every sector.

    The logic is as follows: a "sector" is the segment between the end of
    one braking zone and the beginning of the next. In other words, the
    acceleration and top-speed section between two corners.

    Parameters
    ----------
    df : pd.DataFrame
    driver_a, driver_b : str
        Driver codes of the two drivers to compare

    Returns
    -------
    list[dict]
        List of sectors, each containing:
            sector_num      : sector number (1-indexed)
            dist_start/end  : normalized sector distance
            time_a / time_b : sector time per driver (s)
            delta           : time_b - time_a (negative = driver_b faster)
            winner          : faster driver
            gap_ms          : time difference in milliseconds (more readable)
    """

    zones_a = detect_brake_zones(df, driver_a)
    zones_b = detect_brake_zones(df, driver_b)

    # Sector are aligned to ensure and accurate comparison of the same corner
    pairs = _align_brake_zones(zones_a, zones_b)

    if (len(pairs) < 2):
        raise ValueError(
            f"We need at least 2 aligned brake zones. "
            f"Only {len(pairs)} were found. Please check the CSV file."
        )
    
    sectors = []

    # Each sector is defined from the end of zone[i] to the beginning of zone[i+1]
    for i in range(len(pairs)-1):
        za_end, zb_end = pairs[i]
        za_next, zb_next = pairs[i+1]

        time_a = za_next['time_start'] - za_end['time_end']
        time_b = zb_next['time_start'] - zb_end['time_end']

        # Sanity check: a sector cannot have negative time
        # If it does, there is likely an issue with the data

        if time_a < 0 or time_b < 0 :
            continue

        delta = time_b - time_a
        winner = driver_b if delta < 0 else driver_a

        sectors.append({
            'sector_num': i+1,
            'dist_start': round(za_end['dist_end'], 4),
            'dist_end': round(za_next['dist_start'], 4),
            f'time_{driver_a.lower()}': round(time_a, 4),
            f'time_{driver_b.lower()}': round(time_b, 4),
            'delta': round(delta, 4),
            'winner': winner,
            'gap_ms': round(abs(delta) * 1000)
        })

    return sectors
    
# ---------------------------------------------------------------------------
# Function 3: compute_brake_comparison
# ---------------------------------------------------------------------------

def compute_brake_comparison(df: pd.DataFrame, driver_a: str, driver_b: str) -> list[dict]:
    """
    Compares the braking zones of two drivers corner by corner.

    For each aligned pair of corners, it computes:
        - Entry speed difference       (who arrives faster)
        - Minimum speed difference     (who brakes harder)
        - Braking point difference     (who brakes later)
        - Relative aggressiveness      (delta_speed ratio)

    Parameters
    ----------
    df : pd.DataFrame
    driver_a, driver_b : str

    Returns
    -------
    list[dict]
        List of per-corner comparisons
    """
    zones_a = detect_brake_zones(df, driver_a)
    zones_b = detect_brake_zones(df, driver_b)
    pairs   = _align_brake_zones(zones_a, zones_b)
 
    comparisons = []
    for idx, (za, zb) in enumerate(pairs):
        delta_entry    = zb['speed_entry'] - za['speed_entry']
        delta_min      = zb['speed_min']   - za['speed_min']
        delta_bp       = zb['dist_start']  - za['dist_start']  # positive = B brakes later
        aggr_a         = za['delta_speed']
        aggr_b         = zb['delta_speed']
 
        comparisons.append({
            'zone_num':     idx + 1,
            'dist':         round((za['dist_start'] + zb['dist_start']) / 2, 3),
            f'entry_{driver_a.lower()}':   round(za['speed_entry'], 1),
            f'entry_{driver_b.lower()}':   round(zb['speed_entry'], 1),
            f'min_{driver_a.lower()}':     round(za['speed_min'], 1),
            f'min_{driver_b.lower()}':     round(zb['speed_min'], 1),
            'delta_entry':  round(delta_entry, 1),  # positive = B entry faster
            'delta_min':    round(delta_min, 1),    # positive = B arrive faster to the apex
            'delta_brake_point': round(delta_bp, 4),  # positive = B brakes later
            f'aggression_{driver_a.lower()}': round(aggr_a, 1),
            f'aggression_{driver_b.lower()}': round(aggr_b, 1),
            'entry_advantage':  driver_b if delta_entry > 0 else driver_a,
            'apex_advantage':   driver_a if delta_min < 0 else driver_b,
        })
 
    return comparisons

# ---------------------------------------------------------------------------
# Función 4: compute_lap_summary
# ---------------------------------------------------------------------------

def compute_lap_summary(df: pd.DataFrame) -> dict:
    """
    Computes the overall summary for all drivers in the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    dict containing:
        drivers         : list of drivers
        lap_times       : dict {driver: lap_time_s}
        vmax            : dict {driver: max_speed_kmh}
        avg_speed       : dict {driver: average_speed_kmh}
        gap             : time difference between first and second driver (s)
        fastest_driver  : fastest driver
    """
    
    drivers = list(df['Source'].unique())
    lap_times = {}
    vmax      = {}
    avg_speed = {}
 
    for drv in drivers:
        d = df[df['Source'] == drv]
        lap_times[drv] = round(d['Time_from_start'].max(), 4)
        vmax[drv]      = round(d['Speed'].max(), 1)
        avg_speed[drv] = round(d['Speed'].mean(), 1)
 
    sorted_drivers = sorted(drivers, key=lambda d: lap_times[d])
    fastest = sorted_drivers[0]
 
    gap = None
    if len(sorted_drivers) >= 2:
        gap = round(lap_times[sorted_drivers[1]] - lap_times[sorted_drivers[0]], 4)
 
    return {
        'drivers':        drivers,
        'lap_times':      lap_times,
        'vmax':           vmax,
        'avg_speed':      avg_speed,
        'gap':            gap,
        'fastest_driver': fastest,
        'gp':             df['GP'].iloc[0]      if 'GP'      in df.columns else None,
        'year':           int(df['Year'].iloc[0]) if 'Year'  in df.columns else None,
        'session':        df['Session'].iloc[0] if 'Session' in df.columns else None,
    }

# ---------------------------------------------------------------------------
# Función 5: run_full_analysis  (orchestrator)
# ---------------------------------------------------------------------------

def run_full_analysis(df: pd.DataFrame) -> dict:
    """
    Runs the complete analysis for all driver pairs in the DataFrame
    and returns a dictionary containing all results.

    This is the main entry point used by the dashboard.

    Parameters
    ----------
    df : pd.DataFrame
        Comparison DataFrame (comparison CSV)

    Returns
    -------
    dict with keys:
        summary          : result of compute_lap_summary
        sectors          : result of compute_sectors (first driver pair)
        brake_zones      : dict {driver: zones} for each driver
        brake_comparison : result of compute_brake_comparison
        drivers          : list of detected drivers
    """

    drivers = list(df['Source'].unique())
 
    if len(drivers) < 2:
        raise ValueError(f"Se necesitan al menos 2 pilotos. Se encontró: {drivers}")
 
    # Para el análisis de sectores y frenadas usamos los primeros dos pilotos.
    # Si hay más de dos, se pueden agregar pares adicionales en el futuro.
    driver_a, driver_b = drivers[0], drivers[1]
 
    summary          = compute_lap_summary(df)
    brake_zones      = {drv: detect_brake_zones(df, drv) for drv in drivers}
    sectors          = compute_sectors(df, driver_a, driver_b)
    brake_comparison = compute_brake_comparison(df, driver_a, driver_b)
 
    return {
        'summary':          summary,
        'sectors':          sectors,
        'brake_zones':      brake_zones,
        'brake_comparison': brake_comparison,
        'drivers':          drivers,
        'driver_a':         driver_a,
        'driver_b':         driver_b,
    }