# F1 2026 - Front Suspension Design

Conceptual design of a Formula 1 front suspension system compliant with the FIA 2026 Technical Regulations (Issue 8, Art. 10)

![Status](https://img.shields.io/badge/status-in%20progress-yellow)
![Regulation](https://img.shields.io/badge/FIA-2026%20Issue%208-blue)
![Article](https://img.shields.io/badge/scope-Article%2010-lightgrey)

---

## Overview 

This project develops a front suspension concept for a 2026 Formula 1 car, stricly bounded by the FIA Technical Regulations. The scope covers outboard and inboard suspension geometry (Art. 10, and 10.4), rocker kinematics, suspension member cross-section compliance, stering range verification.

The objective is to demostrate end-to-end workflow:

> Regulation extraction → Geometric constraint → CAD model → Kinematics analisys → Compliance documentation

---

## Design specifications 

| Parameter | Value | Source |
|-----------|-------|--------|
| Regulation | FIA 2026 Technical Regulations, Issue 8 | — |
| Article scope | Art. 10.2 – 10.6 | — |
| Suspension members per upright | 6 (no redundant members) | Art. 10.3.2 |
| Minimum steering lock | +23° / −21° from X-plane | Art. 10.3.7 |
| Inboard actuator | Single rocker per wheel | Art. 10.4.1 |
| Member cross-section | Symmetric, constant, centroid ≤5 mm from load line | Art. 10.3.6 |
| Outboard attachment minimum Z | ZW ≥ −100 mm (front axle) | Art. 10.3.4 |

--- 

## Repository structure

```
f1-front-suspension-2026/
├── docs/                    # Regulation excerpts, notes, constraint summaries
│   ├── FIA_2026_TR_Issue8.pdf
│   └── regulation-notes.md
├── cad/                     # CAD files (STEP, STL, native format)
│   ├── assembly/
│   └── components/
├── analysis/                # Kinematic scripts, compliance checks
│   └── kinematics.py
├── renders/                 # Visualization images
├── COMPLIANCE.md            # Full article-by-article compliance table
└── README.md

```
---

## Regulatory compliance

Full detail in [`COMPLIANCE.md`](./COMPLIANCE.md). Summary of key constraints:

| Article | Constraint | Status |
|----------|------------|--------|
| 10.2.1 | Car must be fitted with sprung suspension | Pending CAD |
| 10.2.2 | Front and rear axles must be independent | Pending CAD |
| 10.2.4 | No powered device may alter suspension configuration | By design |
| 10.2.6 | Suspension state uniquely defined by rocker angular position | Pending CAD |
| 10.3.2 | Six suspension members per upright, no redundant members | Pending CAD |
| 10.3.4 | Outboard attachments outboard of YW=0, above ZW=100 | Pending CAD |
| 10.3.5 | Front axle: two independent pairs, inboard attachments separated ≥300 mm in X | Pending CAD |
| 10.3.6 | Member cross-section symmetric, constant, centroid ≤5 mm from load line | Pending CAD |
| 10.3.7 | Steering lock minimum +23°/−21° from X-plane | Pending CAD |
| 10.3.8 | Wheel tethers must be fitted (Art. 14.4.1) | Pending CAD |
| 10.4.1 | Inboard suspension actuated via a single rocker per wheel only | Pending CAD |
| 10.2.4 | Only springs and dampers permitted as suspension elements | Pending CAD |

---

## Coordinate system 

All geomtry references the FIA coordinate system defined in Art. 2.6.

```
X  →  longitudinal, positive forward
Y  →  lateral, positive to car right
Z  →  vertical, positive upward
 
Origin: defined per Art. 2.6.1 (front axle reference)
Wheel CSYS (XW, YW, ZW): defined per Art. 2.6.3
  → used for all outboard attachment point constraints (Art. 10.3.4)
  → origin at wheel centre, YW=0 at wheel centreline
```

---

## Key Design constraints (Art. 10.3 summary)

The six supension members connecting each front upright to the sprung mass must satisfy:

1. **Geometry** - With steering fixed, wheel centrem position and rotation axis must be uniquely by vetical travel (Art. 10.3.1)
2. **Count** - Exactly 6 members per uprigth; one must connect to the steering system (Art. 10.3.2)
3. **Outboar attachments** - Must lie outboard of YW=0, above ZW=100, and inside the wheel drum (Art. 10.3.4)
4. **Front axle pairing** - 4 non-steering members must form 2 independent pairs with ≥300 mm X separation at inboard attachments (Art. 10.3.5)
5. **Cross-section** - Two axes of simmetry, constant shape and size along length, centroid ≤5 mm from load line (Art. 10.3.6)
6. **Steering range** - Minimum +23°/−21° achievable (Art. 10.3.7)

---

## Toolchain

| Task | Tool |
| CAD Modeling | TBD |
| Kinemaitc analisys  | Python/Numpy |
| Compliance cheking | Manual + CAD measurement |
| Documentation | Markdown |

---

## Status 

- [x] Regulation study (Art. 10.2 – 10.6)
- [x] Constraint extraction and documentation
- [ ] Coordinate system setup in CAD
- [ ] Upright geometry definition
- [ ] 6-member layout (outboard attachments)
- [ ] Inboard rocker and suspension elements
- [ ] Steering system integration
- [ ] Compliance verification (CAD measurement)
- [ ] Kinematic analysis script
- [ ] Renders and documentation

---

## References
 
FIA (2024). *2026 Formula 1 Technical Regulations, Issue 8.* Fédération Internationale de l'Automobile. 24 June 2024.