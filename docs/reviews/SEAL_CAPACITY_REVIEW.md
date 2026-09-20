# Seal capacity — is the maths right?

Reviewed 26 Aug 2026, at Lars's request. Short answer: **the physics is standard and the port is
correct.** Two things were checked — the equations against the literature, and the implementation
against an independently computed calibration chart.

---

## The physics

Two equations, both standard, both traceable to Schowalter (1979), *Mechanics of secondary
hydrocarbon migration and entrapment*, AAPG Bulletin 63(5), 723–760.

**Capillary entry pressure of the seal**

    P_c = 2 γ cos θ / r

γ interfacial tension, θ contact angle, r pore-throat radius.

**Buoyancy balance at seal capacity**

    P_c = Δρ g H   →   H = P_c / (Δρ g)

**The complete form, subtracting the reservoir's own entry pressure**

    H = 2 γ cos θ (1/r − 1/R) / (g Δρ)

with `R` the reservoir's pore-throat radius. Hydrocarbon already occupies the reservoir pores, so
only the *difference* has to be overcome. This is the form `subtract_reservoir=True` implements, and
it is confirmed independently by published statements of the same relation.

**Nothing here is exotic.** The uncertainty in a seal-capacity estimate is entirely in the *inputs*
— overwhelmingly in `r`, because `P_c ∝ 1/r`. That is measured and asserted by
`tests/test_seals.py`: across the default ranges, pore-throat radius produces a P10–P90 spread of
~120 m where the next largest contributor, hydrocarbon density, produces ~31 m.

---

## The implementation, against an independent calibration chart

The chart: porosity falls with burial (Hansen, 1996), each of four published models turns porosity
into an entry pressure, and the buoyancy balance turns that into a column. Regenerating it from the
implemented functions, at **ρ_hc 0.70, ρ_w 1.04**:

| Burial | Model | Computed | Reference chart |
|---:|---|---:|---:|
| 3 000 m | Ibrahim | 216 m | ~230 m |
| 3 000 m | Hildebrand | 221 m | ~215 m |
| 5 000 m | Ibrahim | **818 m** | **~820 m** |
| 5 000 m | Hildebrand | **740 m** | **~740 m** |

The port reproduces the chart. An earlier comparison appeared to show a 30–75 % discrepancy; that
was **my error, not the code's** — I had plotted with ρ_hc 0.80 / ρ_w 1.05 (Δρ = 0.25) against a
chart drawn at Δρ = 0.34. Seal capacity goes as `1/Δρ`, so the density contrast has to be matched
before any comparison means anything, which is itself the lesson.

---

## The four models, and what to make of them

| | Form |
|---|---|
| Ibrahim | quintic in porosity % |
| Hildebrand | `48.793 · exp(−0.123 φ)` |
| PetroMod® | `−1.7345 φ + 49.485` |
| Greenland | `260.19 · φ^−0.964` |

**They disagree by roughly a factor of five**, and that is the honest state of the art rather than a
defect in any of them. The tool offers all four and draws the envelope; picking one as *the* answer
would be false precision.

They are fits, and they misbehave outside the porosity range they were fitted over — PetroMod is
linear and crosses zero near 28.5 % porosity, Ibrahim is a quintic and turns over, Greenland is a
power law and diverges towards zero porosity. The port returns NaN rather than a negative or absurd
column, which is why the shallow end of some curves is blank.

### One naming point worth chasing

**"Hildebrand" is almost certainly Hilden*brand*** — Hildenbrand et al. (2004), on capillary entry
pressure and displacement pressure in mudstones, is the standard reference in this space and there
is no seal-capacity correlation under "Hildebrand". Worth confirming against the original source
before the paper cites it. **"Greenland"** likewise reads as a *dataset*
(shales from Greenland) rather than an author.

---

## In the app

The chart is regenerated live inside the top-seal calculator (tab ③ → Retention → *Is this capacity
plausible?*), from the ported functions rather than from cached cells, with the ±5 porosity-point
cases as dotted lines — **and with the distribution you have selected drawn on it**. If the selected
bar sits outside the published envelope at your burial depth, either the pore-throat radius or the
envelope is wrong, and it is worth knowing which.

## What has *not* been checked

The Aplin & Yang interfacial-tension correlations (`91.657·exp(−0.0126 T)` for gas,
`−0.1886 T + 24.866` for oil) are reproduced as given and have not been traced to their
source. *15 Sep 2026:* checked against the literature in `archive/development_notes/IFT_CHECK_2026-09-15.md`. The gas
line is consistent with methane–brine data; the oil line falls below every measured
reservoir-condition value above about 60 °C and understated the shipped oil seal capacity by
about 1.9×. Yang & Aplin (1998) is not its source. The oil line is replaced by an elicited range
(default 18–28 dyne/cm) the same day; the gas line stays. The oil one is known to go non-positive near 132 °C, which the code refuses rather than
silently returning a negative column — a real physical limit, now reachable by default since burial
depth drives temperature.
