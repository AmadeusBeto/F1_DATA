# Regulatory compliance - FIA 2026 Front suspension

This document tracks compliance of the front suspension design against the FIA 2026 Technical Regulations, Issue 8

**Status legend:** 
- `Compliant` - verified in CAD
- `By design` - inherently satisfied by the design approach
- `Pending` - not yet modelled or verified
- `N/A` - not aplicable to this component

---

## Article 10.2 - Sprung suspension 

| Article | Rquirement | Implementation | Status | 
|---------|------------|----------------|--------|
| 10.2.1 | Car must be fitted with sprung suspension | Spring medium connecting all the wheels to sprung mass | Pending |
| 10.2.2 | Front and rear axles must be independent; response results only from loads on that axle | Front suspension isolated from rear; no cross-axle coupling | Pending | 
| 10.2.4 | No powered device may alter supension configuration or performance | No active elements in design | By design |
| 10.2.5 | No adjusment while car is in motion | No in-motion adjusment mechanism | By design |
| 10.2.6 | Suspension state uniquely defined by rocker angular position and velocity | Single rocker per wheel; no additional DOF | Pending |
| 10.2.6(a) | No inerters, mass dampers, or acceleration-sensitive valves | None included | By design |
| 10.2.6(B) | No coupling to braking or steering systems | Suspension isolated from brake/steer inputs | By design |
| 10.2.6(c) | No ride height control or self-levelling systems | None included | By desgin |
| 10.2.6(h) | No mass dampers (as defined in Art. 10.1.5) | None included | By design |

---

## Article 10.3 - Outboard suspension

| Article | Rquirement | Implementation | Status | 
|---------|------------|----------------|--------|
| 10.3.1 | Wheel centre position and rotastion axis uniquely defined by vertical travel (steering fixed) | 5-DOF via 6-memeber layput | Pending |
| 10.3.1 | In side view, ZW axis angle variation ≤5° over full vertical travel | To verified in CAD | Pending |
| 10.3.2 | Exactly 6 suspension members per upright | 6 memebers defined un layout | Pending |
| 10.3.2 | No redundant members | Confirmed by member count and function | Pending |
| 10.3.2 | One member per wheel connected to steering system | Front tie rod connects to steering | Pending |
| 10.3.4 | Outboard attachments points outboard of YW=0 | All joints positioned outboard | Pending |
| 10.3.4 | Above ZW=100 (front axle) | Joints above ZW=100 | Pending |
| 10.3.4 | Inside the wheel drum (Art. 3.14.12) | Joints within drum volume | Pending |
| 10.3.5 | 4 non_steering/non-rocker members form 2 independent pairs | Pair A (upper wishbone arms), B pair (lower wishbone arms) | Pending |
| 10.3.5 | Inboard attachments of each pair separated ≥300 mm in X | To be verified in CAD | Pending |
| 10.3.5 | Inboard attachments above Z=250 mm | To be verified in CAD | Pending |
| 10.3.6(a) | Member cross-section has 2 ortogonal axes of simmetry | Circular o simmetryc aerofoil sections | Pending |
| 10.3.6(b) | If in contect with airstream, cross-section must be circular | Expose members use circular section | Pending |
| 10.3.7 | Minimum steering lock: +23°/−21° from X-plane | Steering geometry to allow required lock | Pending |
| 10.3.8 | Wheel tethers fitted per Art. 14.4.1 | Tether attachments points included | Pending |

---

## Article 10.4 - Inboard suspension

| Article | Rquirement | Implementation | Status | 
|---------|------------|----------------|--------|
| 10.4.1 | Inboard suspension actuated via single rocker per wheel | One rocker per corner | Pending |
| 10.4.1 | Only single outboard suspension connection to each rocker | Push/pull rod connects uprightto rocker | Pending |
| 10.4.2(a) | Suspension elements only permit relative rotation at nodes | Rod ends and spherical bearings at all nodes | Pending |
| 10.4.2(b) | Elements arranged in parallel only | No series spring-spring elements | By design |
| 10.4.3(a) | Only springs (monotolically increasing load-deflection) | Coil spring or torsion bar | Pending |
| 10.4.3(b) | Only dampers (opposing force as function of relative velocity) | Telescopic damper | Pending |
| 10.4.3 | Sprin elements using fluid medium not permitted | Mechanical spring only | By design |
| 10.4.3 | Links actuating remote elements must be rigid, minimal mass | Rigid push/pull rod | Pending |

---

## Article 10.5 - Steering

| Article | Rquirement | Implementation | Status | 
|---------|------------|----------------|--------|
| 10.5 (general) | Steering system requirements | Steering column and rack whitin regs | Pending |

---

## Article 10.6 - Suspension uprights

| 10.6 (general) | Upright structural requirements | Upright geometry to be difined in CAD | Pending | 

---

*Last update: - Regulation: FIA 2026 Technical Regulations, Issue 8 (24 June 2024)*