# 03 — Validación cinemática: del CAD a los datos

Cierra el ciclo del portafolio: **reglamento FIA → CAD (02_SUSPENSION_F1) →
modelo físico → telemetría (01_TELEMETRY_F1)**. Un quarter-car construido con
la geometría diseñada predice el recorrido de suspensión, y esa predicción se
compara contra lo que mide Assetto Corsa (canales `SuspTravel_*` vía
ACTI/MoTeC).

![Status](https://img.shields.io/badge/status-pipeline%20ready-yellow)
![Geometry](https://img.shields.io/badge/geometry-placeholder-orange)

---

## ¿Por qué esto vale la pena?

Diseñar una suspensión en CAD y no confrontarla nunca con datos es la mitad
del trabajo. La pregunta de ingeniería real es: *¿el sistema que dibujé se
comporta como predije?* Este módulo responde con tres números por rueda:

| Métrica | Pregunta que responde | Valor sano |
|---|---|---|
| Correlación `r` | ¿La **física** (transferencias de carga) es correcta? | > 0.9 |
| Ganancia | ¿La **rigidez + motion ratio** están bien medidos? | 0.8 – 1.2 |
| RMSE (mm) | ¿Cuánto error global queda? | comparar entre iteraciones |

Una `r` negativa delata una convención de signos invertida; una ganancia de
1.3 significa que el coche real es un 30% más blando que tu `geometry.json`.
El reporte HTML interpreta esto automáticamente.

## El modelo (y sus límites)

`quarter_car.py` implementa el modelo de 2 grados de libertad: masa suspendida
sobre muelle+amortiguador (a través del **motion ratio** del rocker) y masa no
suspendida sobre la rigidez del neumático. Dos modos:

1. **Cuasi-estático** — de `Speed`, `LongAccel`, `LatAccel` predice la carga
   por rueda (estático + aero·v² + transferencias) y de ahí el recorrido que
   debería medir el potenciómetro. Es lo que se valida contra telemetría.
2. **Dinámico** — integra la respuesta transitoria ante un perfil de pista
   (RK4, sin scipy). Da frecuencias propias y amortiguamiento: un F1 sano
   vive en ~3–5 Hz (masa suspendida) y ~15–25 Hz (rueda).

Límites asumidos: sin no-linealidad de rocker, sin heave/roll acoplados, sin
dinámica de transferencia (todo instantáneo). Para validar geometría y
rigideces es suficiente; para diseñar amortiguadores habría que crecer a
half-car.

## Flujo de trabajo

```bash
cd 03_KINEMATICS_F1/src

# 0. Ver los modos propios de la geometría actual
python quarter_car.py

# 1. (Hoy) Probar el pipeline con datos sintéticos — NO valida física,
#    solo comprueba que la cadena corre. Esperado: r≈0.99, gain≈1.15.
python make_demo_data.py --to-dashboard
python validate_kinematics.py ../data/demo_synthetic_lap.csv

# 2. (Cuando termines el CAD) Medir en CATIA y actualizar geometry.json:
#    motion_ratio, spring_rate, masas... y poner "estimated": false.

# 3. (Cuando captures en AC) ACTI → MoTeC i2 → export CSV →
python -c "import sys; sys.path.insert(0,'../../01_TELEMETRY_F1/src'); \
from f1core.adapters.assetto_corsa import from_motec_csv; \
from_motec_csv('mi_vuelta.csv','AC_Real').to_csv('../data/ac_real.csv', index=False)"
python validate_kinematics.py ../data/ac_real.csv
```

El dashboard del proyecto 01 muestra todo esto en la pestaña **🔧 Cinemática**
(aparece con cualquier dataset que traiga `SuspTravel_FL/FR`).

## Cómo medir el motion ratio en CATIA

En el ensamblaje de 02_SUSPENSION_F1: desplaza la rueda 10 mm en Z (kinematics
del mecanismo) y mide cuánto se comprime el muelle a través del rocker.
`MR = Δrueda / Δmuelle`. Si el rocker es progresivo, toma el valor alrededor
de la posición estática — el modelo es lineal.

## Estructura

```
03_KINEMATICS_F1/
├── geometry.json        # parámetros del modelo — EDITAR con medidas del CAD
├── src/
│   ├── quarter_car.py          # modelo físico (2 modos)
│   ├── validate_kinematics.py  # comparación + métricas + reporte HTML
│   └── make_demo_data.py       # vuelta sintética para probar el pipeline
├── data/                # datasets canónicos con SuspTravel_* (y demo)
└── reports/             # reportes HTML generados
```
