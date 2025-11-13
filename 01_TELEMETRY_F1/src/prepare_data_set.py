import fastf1
import pandas as pd 
import numpy as np
import os

# Habilitar cache
fastf1.Cache.enable_cache('../data/cache')

# Configuración
YEAR = 2021
GP = 'Abu Dhabi'
SESSION_TYPE = 'Q'
PILOTS = ['HAM', 'VER']

# Descargar sesión
session = fastf1.get_session(YEAR, GP, SESSION_TYPE)
session.load()

# Asegurar que existe la carpeta data
os.makedirs('../data', exist_ok=True)

# Guardar datos de pilotos
for driver in PILOTS:
    try:
        lap = session.laps.pick_driver(driver).pick_fastest()
        telemetry = lap.get_car_data().add_distance()
        
        # Normalización
        telemetry['LapDistanceNorm'] = telemetry['Distance'] / telemetry['Distance'].max()
        telemetry["Source"] = driver
        
        # **CONVERTIR TIME A SEGUNDOS**
        telemetry['Time_seconds'] = telemetry['Time'].dt.total_seconds()
        
        output_path = f"../data/{GP.lower().replace(' ', '_')}_{YEAR}_{driver.lower()}.csv"
        
        # Guardar solo columnas necesarias
        columns_to_save = ['LapDistanceNorm', 'Speed', 'Throttle', 'Brake', 'Time_seconds', 'Source']
        telemetry[columns_to_save].to_csv(output_path, index=False)
        
        print(f"✅ Guardado: {output_path}")
        print(f"   Tiempo total: {telemetry['Time_seconds'].max():.2f} segundos")
        
    except Exception as e:
        print(f"❌ Error con {driver}: {e}")

# Combinar datasets
dfs = []
for driver in PILOTS:
    try:
        file_path = f"../data/{GP.lower().replace(' ', '_')}_{YEAR}_{driver.lower()}.csv"
        df = pd.read_csv(file_path)
        dfs.append(df)
        print(f"📂 Cargado: {file_path}")
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {file_path}")

if not dfs:
    print("❌ No se pudieron cargar datos. Saliendo...")
    exit()

# Crear rango normalizado
normalized_range = np.linspace(0, 1, 1000)
aligned_dfs = []

for df in dfs:
    try:
        interp_df = pd.DataFrame({
            'LapDistanceNorm': normalized_range,
            'Speed': np.interp(normalized_range, df['LapDistanceNorm'], df['Speed']),
            'Throttle': np.interp(normalized_range, df['LapDistanceNorm'], df['Throttle']),
            'Brake': np.interp(normalized_range, df['LapDistanceNorm'], df['Brake']),
            'Time_seconds': np.interp(normalized_range, df['LapDistanceNorm'], df['Time_seconds']),
            'Source': df['Source'].iloc[0]
        })
        aligned_dfs.append(interp_df)
        
    except Exception as e:
        print(f"❌ Error interpolando datos de {df['Source'].iloc[0]}: {e}")

# Combinar todos los datos
if aligned_dfs:
    combined = pd.concat(aligned_dfs, ignore_index=True)
    
    # **CALCULAR TIEMPO RELATIVO ENTRE PILOTOS**
    combined['Time_from_start'] = combined.groupby('Source')['Time_seconds'].transform(
        lambda x: x - x.min()
    )
    
    output_file = f"../data/{GP.lower().replace(' ', '_')}_{YEAR}_comparison.csv"
    combined.to_csv(output_file, index=False)
    
    print(f"✅ Dataset combinado creado: {output_file}")
    print(f"📊 Pilotos incluidos: {combined['Source'].unique()}")
    print(f"📈 Total de puntos: {len(combined)}")
    
    # Mostrar estadísticas básicas
    print("\n📋 Estadísticas por piloto:")
    for driver in combined['Source'].unique():
        driver_data = combined[combined['Source'] == driver]
        lap_time = driver_data['Time_seconds'].max() - driver_data['Time_seconds'].min()
        print(f"   {driver}: Tiempo vuelta = {lap_time:.3f}s, Velocidad max = {driver_data['Speed'].max():.1f} km/h")
        
else:
    print("❌ No se pudieron crear datos alineados")