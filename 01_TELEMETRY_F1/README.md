# F1_DATA – Interactive Telemetry
 
Comparativa interactiva de vueltas rápidas entre pilotos de F1.
Soporta cualquier carrera, sesión y combinación de pilotos disponibles en FastF1.
 
---
 
## Repository structure
 
```
F1_DATA/
├── data/
│   ├── cache/                              ← Cache de FastF1 (auto-generado)
│   ├── abu_dhabi_2021_Q_HAM.csv           ← Telemetría individual
│   ├── abu_dhabi_2021_Q_VER.csv
│   └── abu_dhabi_2021_Q_comparison.csv    ← Dataset alineado (input del dashboard)
├── notebooks/
│   ├── 01_visualizacion_validacion.ipynb
│   └── 02_telemetry_preprocessing.ipynb
└── src/
    ├── prepare_data_set.py   ← Descarga y procesa datos con FastF1
    └── dashboard.py          ← Dashboard interactivo con Dash / Plotly
```
 
---
 
## Instalation
 
```bash
python -m venv f1_env
 
# Windows
.\f1_env\Scripts\activate
# Linux / macOS
source f1_env/bin/activate
 
pip install -r requirements.txt
```
 
---
 
## Workflow
 
### 1. Download telemetry
 
```bash
cd F1_DATA/src
 
# Modo interactivo (te pregunta carrera, sesión y pilotos)
python prepare_data_set.py
 
# Modo con argumentos
python prepare_data_set.py --year 2023 --gp "Monaco" --session Q --drivers HAM LEC VER
python prepare_data_set.py --year 2022 --gp "Monza"  --session R --drivers VER LEC
```
 
**Avalible sesions:** `Q` Qualifying · `R` Race · `FP1/FP2/FP3` Practices · `S` Sprint
 
Los CSV se guardan automáticamente en `../data/` con el nombre:
```
<gp>_<año>_<sesión>_comparison.csv
```
 
### 2. Lanzar el dashboard
 
```bash
python dashboard.py
```
 
Abre **http://127.0.0.1:8050** en el navegador.
 
El dashboard **detecta automáticamente** todos los CSV disponibles en `../data/` y los muestra en el selector de sesión. No necesitas reiniciar al agregar nuevos datos.
 
---
 
## Vistas disponibles
 
| Vista | Descripción |
|---|---|
| **Velocidad** | Traza de velocidad (km/h) a lo largo de la vuelta normalizada |
| **Acelerador** | Posición del acelerador (%) de cada piloto |
| **Frenos** | Uso de frenos a lo largo de la vuelta |
| **Delta de tiempo** | Diferencia acumulada de tiempo entre pilotos |
| **Vista completa** | Todos los gráficos simultáneamente |
 
---
 
## Notas técnicas
 
- La distancia se **normaliza** (0 → 1) para poder comparar pilotos independientemente del tiempo de vuelta.
- Se interpolan **1 000 puntos uniformes** por piloto para alinear las trazas.
- El campo `Time_from_start` corrige el offset de tiempo de sesión de FastF1.
- Los colores se asignan automáticamente por orden de aparición en el dataset.