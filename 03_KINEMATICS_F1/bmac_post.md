# 🔧 I Designed an F1 Suspension in CAD — Then Built a Physics Model to Check If It Actually Works

> **[BORRADOR]** Los números marcados `[PENDIENTE]` se rellenan cuando haya
> geometría real medida en CATIA y una captura real de Assetto Corsa.
> No publicar antes: el gancho del post es la validación con datos reales.

**Anyone can draw a suspension. The real question is: does it behave the way you predicted?**

For my 2026 F1 front suspension project (designed in CATIA, bounded by the actual FIA Technical Regulations, Art. 10), I wanted more than a pretty render. So I built a physics model of my own design and validated it against telemetry — closing the full engineering loop:

**Regulations → CAD → Physics model → Data.**

---

## 🔬 The Idea

A *quarter-car model* is the minimal physics of one corner of the car: the chassis mass sitting on a spring and damper, the wheel mass sitting on the tire's stiffness. Six parameters — all measured from my CAD model:

- Spring rate and damper coefficient
- **Motion ratio** — how much the spring compresses per mm of wheel travel, measured by articulating the CATIA assembly. Get this 10% wrong and your stiffness is off by 20%.
- Sprung/unsprung masses and tire stiffness

Feed it speed and accelerations from a lap, and it predicts the suspension travel a sensor should measure. Then compare against what Assetto Corsa's suspension channels *actually* measured (captured with ACTI → MoTeC i2 — the same telemetry software real teams use).

## 📊 Three Numbers That Judge the Design

| Metric | What it answers | My result |
|---|---|---|
| Correlation **r** | Is the load-transfer physics right? | `[PENDIENTE]` |
| **Gain** | Are stiffness + motion ratio measured correctly? | `[PENDIENTE]` |
| **RMSE** | How much error remains overall | `[PENDIENTE]` |

An r of 0.95 means the model understands *where* the car compresses and extends. A gain of 1.2 would mean the real car is 20% softer than my CAD numbers — and would send me straight back to re-measure the rocker.

The model also predicts the suspension's "identity card": natural frequencies (`[PENDIENTE]` Hz sprung — F1 cars live around 3–5 Hz, road cars near 1 Hz) and damping ratio.

## 🛠️ The Stack

- **Python + NumPy** — quarter-car model with its own RK4 integrator
- **CATIA** — geometry source (motion ratio measured on the actual mechanism)
- **Assetto Corsa + ACTI + MoTeC i2** — telemetry capture
- **Plotly / Dash** — interactive validation reports, integrated as a third view in my existing F1 telemetry dashboard

Everything flows through the same canonical data schema as my telemetry project — one pipeline, any data source.

## 💡 What I Learned

`[PENDIENTE — 2-3 hallazgos reales de la validación: p.ej. cuánto se desvió el
motion ratio medido vs estimado, qué convención de signos tenía AC, qué parte
del modelo falló primero]`

---

*If you enjoy engineering that connects regulations, CAD and real data, you can support my work here on Buy Me a Coffee. Full code on my GitHub.*
