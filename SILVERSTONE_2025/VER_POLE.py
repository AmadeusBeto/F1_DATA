import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt

# Enable FastF1 cache
fastf1.Cache.enable_cache('cache')

# Load Race session (can use 'Q' for qualifying)
session = fastf1.get_session(2025, 'Silverstone', 'R')
session.load()

# Get fastest laps
ver_lap = session.laps.pick_drivers('VER').pick_fastest()
pia_lap = session.laps.pick_drivers('PIA').pick_fastest()

# Get telemetry and add distance
ver_tel = ver_lap.get_car_data().add_distance()
pia_tel = pia_lap.get_car_data().add_distance()

# SPEED
plt.figure(figsize=(10, 4))
plt.plot(ver_tel['Distance'], ver_tel['Speed'], label='Verstappen', color='blue')
plt.plot(pia_tel['Distance'], pia_tel['Speed'], label='Piastri', color='orange')
plt.title('Velocidad vs Distancia')
plt.xlabel('Distancia (m)')
plt.ylabel('Velocidad (km/h)')
plt.legend()
plt.tight_layout()
plt.savefig('speed_silverstone_2025.png')

# THROTTLE
plt.figure(figsize=(10, 4))
plt.plot(ver_tel['Distance'], ver_tel['Throttle'], label='Verstappen', color='blue')
plt.plot(pia_tel['Distance'], pia_tel['Throttle'], label='Piastri', color='orange')
plt.title('Throttle vs Distancia')
plt.xlabel('Distancia (m)')
plt.ylabel('Acelerador (%)')
plt.legend()
plt.tight_layout()
plt.savefig('throttle_silverstone_2025.png')

# BRAKE (0 or 1 usually)
plt.figure(figsize=(10, 4))
plt.plot(ver_tel['Distance'], ver_tel['Brake'], label='Verstappen', color='blue')
plt.plot(pia_tel['Distance'], pia_tel['Brake'], label='Piastri', color='orange')
plt.title('Frenado vs Distancia')
plt.xlabel('Distancia (m)')
plt.ylabel('Frenando (1 = sí)')
plt.legend()
plt.tight_layout()
plt.savefig('brake_silverstone_2025.png')
