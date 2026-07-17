# 🏎️ F1 Telemetry Analysis — Abu Dhabi 2021 Qualifying: Hamilton vs Verstappen

**The lap that defined a championship.**

Abu Dhabi 2021. The last qualifying session of the season, and both Lewis Hamilton and Max Verstappen were separated by exactly zero points in the Drivers' Championship. Pole position mattered.

Verstappen took it — by just **0.252 seconds**.

But what actually happened across those 82 seconds? Where did Verstappen gain his advantage? Did Hamilton ever lead? This project answers those questions with **real telemetry data**, visualized in an interactive Python dashboard.

---

## 🔬 What We Analyzed

Using the **FastF1** library — which pulls official F1 telemetry via the Ergast/F1 API — I extracted the fastest qualifying lap for both drivers and aligned them on a normalized distance axis (0 → 1 = start/finish line → start/finish line). This lets us compare their inputs frame-by-frame, regardless of small timing differences.

Four channels were analyzed:

- **Speed (km/h)** — how fast each car was traveling at every point of the circuit
- **Throttle (%)** — how aggressively each driver was using the accelerator
- **Brake** — when and how long each driver was on the brakes
- **Time Delta (s)** — who was ahead, and by how much, at each point of the lap

---

## 📊 Key Numbers

| Metric | HAM (Mercedes) | VER (Red Bull) |
|---|---|---|
| Lap time | 1:22.242 | **1:21.990** |
| Top speed | 320.9 km/h | **325.0 km/h** |
| Avg. throttle | **84.6%** | 82.1% |
| Full throttle laps % | 74.7% | **75.4%** |
| Time braking | 11.7% | 12.4% |

---

## 🔍 What the Telemetry Reveals

**Verstappen's top speed advantage was 4.1 km/h.** That gap is almost entirely explained by the Red Bull's straight-line performance in 2021 — a car that was optimized for low drag on Abu Dhabi's long straights. Hamilton drove with slightly more throttle on average, suggesting he was fighting harder to stay with the Red Bull through the traction zones.

**Hamilton briefly led in the first sector.** In the opening portion of the lap (distance 0.00–0.10), Hamilton was marginally ahead — up to +0.091s. This reflects Mercedes' strong performance in the first sector's technical corners.

**Verstappen built his advantage through the middle of the lap.** At the midpoint of the circuit (~distance 0.50), Verstappen was ahead by **0.309 seconds** — his maximum lead. The Yas Marina Circuit's long back straight, where the Red Bull's aero advantage was fully exposed, is the main contributor here.

**The final gap was 0.161s.** Despite Hamilton recovering slightly in the final sector, Verstappen crossed the line 0.252s ahead. The championship's most consequential qualifying session came down to those straights.

---

## 🛠️ The Stack

- **FastF1** — official F1 telemetry data
- **Pandas / NumPy** — data processing and interpolation
- **Dash / Plotly** — interactive visualization dashboard
- **Python 3.10+**

The dashboard runs locally and lets you toggle between Speed, Throttle, Brake, and Delta views with a single click.

---

## 📁 What You Get

The full project is available on GitHub and includes:

- `prepare_data_set.py` — downloads and preprocesses the telemetry (or use the pre-built CSVs)
- `dashboard.py` — launch the interactive Dash app
- `notebooks/` — step-by-step Jupyter notebooks for exploration and validation
- `data/` — pre-processed CSVs ready to use without re-downloading

**If you find this useful, a coffee helps keep these projects coming. Every new analysis takes hours of data work, engineering, and documentation.** ☕

---

*Part of an ongoing F1 Data Analysis portfolio. Next up: tire degradation modeling, sector-by-sector breakdowns, and 2024 season comparisons.*
