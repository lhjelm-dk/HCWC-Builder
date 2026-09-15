# Plan — capillary-controlled two-phase columns

*Written 7 Sep 2026, out of the Hood (2019) review. **Not started.** Lars's call on 7 Sep was to
note the gap in the app and plan it properly for later, which is what this is.*

The gap, in one sentence: **the app has no seal-capacity route to a gas–oil contact.** Every
two-phase construction it can currently reach is charge-driven, and two of the three are not wired
to any control at all.

---

## 1 · What Hood asks for

Slide 18, Case 1 — modelling dual-phase columns where both the GOC and the OWC are controlled by
capillary leak (his "Sales Class 3"):

> When both the GOC and the OWC are controlled by capillary seal limitations, the GOC will comprise
> **approximately 20 %** of the total hydrocarbon column height. This is rarely equivalent to 20 %
> of the trap (hydrocarbon-bearing) or energy-equivalent volume.

The second sentence is the reason to build it rather than to quote it. Teams take the 20 %, apply it
to *volume*, and are wrong by whatever the area–depth curve says — which on a domed closure is a
large factor, because the gas cap sits in the narrow part.

Slide 19, Case 2 — the geometric-limit variant — is a separate, cheaper item; see §7.

---

## 2 · Where the app stands today

| | State |
|---|---|
| `seals.max_column_height_m`, `sample_max_column_m` | One fluid at a time. `SealInputs.fluid` is `"Gas"` or `"Oil"` and drives both the interfacial-tension correlation and the density contrast. |
| `charge.oil_contact`, `charge.gas_contact` | Wired to the UI, via `sources.render_charge_computed`. |
| `charge.mixed_separate`, `charge.mixed_joint` | **Implemented and tested, reachable from no widget.** `sources.py:89` offers only `["Pure oil", "Pure gas"]`. |
| `ChargeResult.gas_oil_contact_m` | Exists, populated by the two mixed functions, read by nothing. |
| `limiters_tab.py:484` | Refuses a run where the charge phase and the seal fluid disagree, and tells the user to run the phases separately. Correct today; it becomes the thing to relax. |
| `sources.py` seal calculator | Carries the scope note added 7 Sep 2026 pointing here. |

So the physics is present, the plumbing for a second contact is present, and nothing connects them.

---

## 3 · The physics, derived

**This derivation is mine, not Hood's.** The deck states the 20 % as a result and does not show the
construction. It reproduces the *structure* of his claim but not the number — see §4, which is the
first thing to resolve before any code is written.

A single top seal over a trap holding gas above oil is in contact with **two different fluids in two
different places**: gas at and near the crest, oil on the flanks between the GOC and the OWC. Each
region fails on its own entry pressure, at its own worst point.

Write `a = ρ_w − ρ_g`, `b = ρ_w − ρ_o`, and `Pc_g`, `Pc_o` for the seal's entry pressure against gas
and oil (same θ and `r`, different interfacial tension).

**Oil-contacting region.** Excess pressure grows downward from the OWC and is largest at the
shallowest oil-contacting point, immediately below the GOC:

```
b · g · h_oil  ≤  Pc_o
```

**Gas-contacting region.** Excess at the crest is what the whole column has accumulated:

```
a · g · h_gas  +  b · g · h_oil  ≤  Pc_g
```

Both bind at the steady state Hood describes, giving the whole model in two lines:

```
h_oil = Pc_o / (b · g)                    the app's existing Oil answer, unchanged
h_gas = (Pc_g − Pc_o) / (a · g)           new
```

### Three consequences worth stating before anyone codes them

**(a) The gas cap fraction is scale-free.** It does not depend on pore-throat radius, contact angle,
or the absolute entry pressure — those cancel. With `k = σ_o / σ_g`:

```
gas share  =  1 / ( 1 + (a/b) · k/(1−k) )
```

Only the tension ratio and the two density contrasts. That makes it cheap to sanity-check and hard
to get subtly wrong.

**(b) A two-phase trap holds a *taller* total column than either pure phase.** Not between them —
above both. The oil leg is untouched by the gas above it (its own constraint does not involve
`h_gas`), and the gas cap is then added on top under the higher gas entry pressure. On the shipped
seal defaults at 70 °C:

| | column |
|---|---:|
| pure oil | 150.1 m |
| pure gas | 183.1 m |
| gas over oil | **276.9 m** (127 m gas + 150 m oil) |

This is counterintuitive enough that it needs a figure and a paragraph, not a number in a table. It
is also the reason the feature is worth having: an assessor running the two phases separately today
is understating a two-phase seal-limited trap by up to a third, in the direction that matters.

**(c) It degenerates correctly.** As `σ_o → σ_g` the gas cap vanishes and the answer falls back to
a pure-oil column computed at gas tension — 0.0 m gas over 488.2 m oil at `k = 1`. There is no
discontinuity to guard.

---

## 4 · The thing to settle first: Hood's 20 % is not what this gives

*Status, 15 Sep 2026.* Checked; see `docs/IFT_CHECK_2026-09-15.md`. Reading 2 holds, and the
line's provenance is unknown: Yang & Aplin (1998) is a pore-size paper and carries no tension
correlation. With a sourced oil tension of 21–25 mN/m the gas share is 16–24 %, bracketing
Hood's 20 %. The choice between replacing the line and bounding it is Lars's; the recommendation
is to replace it with an elicited, temperature-flat range.


Run the closed form on the app's own Aplin & Yang correlations and the gas share comes out at
**39–68 %**, not 20 %:

| σ_o/σ_g | gas share | |
|---:|---:|---|
| 0.27 | 50.3 % | Aplin & Yang at 90 °C |
| 0.31 | **45.5 %** | **Aplin & Yang at 70 °C — the app's shipped correlations** |
| 0.50 | 27.3 % | |
| 0.60 | **20.0 %** | **the ratio Hood's number implies** |
| 0.80 | 8.6 % | |

Inverting: Hood's 20 % needs `σ_o/σ_g ≈ 0.60` (robust across density pairs — 0.48 to 0.70 over
ρ_o 0.65–0.85 and ρ_g 0.20–0.35). That is the textbook pairing, gas–water 50 dyne/cm against
oil–water 30. The app uses Aplin & Yang (1998) for both, which gives 37.9 and 11.7 dyne/cm at
70 °C — a ratio of 0.31.

**So the two disagree about oil–water interfacial tension by a factor of about two, and everything
else follows from that.** Three possibilities, and step 1 of the build is deciding which:

1. **Aplin & Yang's oil correlation is right and Hood's 20 % is a legacy rule of thumb** carrying an
   old tension pairing. Then the app should compute the share and say plainly that it does not
   reproduce the 20 %, with this table as the reason.
2. **Aplin & Yang's oil line is being used outside its range.** It is linear and goes negative above
   132 °C, which is already guarded; 11.7 dyne/cm at 70 °C is low but defensible for *live* oil at
   reservoir conditions, where dissolved gas lowers the tension. Worth one literature check.
3. **The derivation in §3 is not Hood's construction.** Possible. His phrasing — *both* the GOC and
   the OWC controlled by capillary limitations — is what §3 formalises, but the deck shows no
   equations, and there may be a third constraint (a base seal, or a leak-rate steady state) that
   pins the split differently.

**Do not ship a "20 % rule" toggle.** If the app computes a gas share it must compute it from the
inputs on screen, and if that disagrees with a widely-quoted number it should say so and show why.
That is the tool's whole posture.

---

## 5 · Implementation

### 5.1 Core — `hcwc/core/seals.py`

New, alongside the existing single-phase functions rather than replacing them.

```python
@dataclass(frozen=True)
class TwoPhaseSealInputs:
    """One seal, two fluids. Everything except the hydrocarbon density is shared, because
    it is one seal — the temperature, the throats and the contact angle cannot differ
    between the gas cap and the oil leg of the same trap."""
    temperature_c: tuple[float, float] = (70.0, 90.0)
    contact_angle_deg: tuple[float, float] = (0.0, 30.0)
    seal_radius_um: tuple[float, float] = (0.01, 0.10)
    reservoir_radius_um: tuple[float, float] = (2.0, 3.5)
    water_density_g_cm3: tuple[float, float] = (1.00, 1.10)
    oil_density_g_cm3: tuple[float, float] = (0.70, 0.85)
    gas_density_g_cm3: tuple[float, float] = (0.15, 0.35)
    subtract_reservoir: bool = True


@dataclass(frozen=True)
class TwoPhaseColumns:
    gas_m: np.ndarray        # (n,) gas cap thickness
    oil_m: np.ndarray        # (n,) oil leg thickness
    @property
    def total_m(self) -> np.ndarray: ...
    @property
    def gas_share(self) -> np.ndarray: ...


def sample_two_phase_columns(inputs, n, seed) -> TwoPhaseColumns: ...
```

Rules the implementation must follow, each of which is a test:

- **One draw of the shared inputs per realisation.** The same `θ`, `r_seal`, `r_res`, `T` and `ρ_w`
  feed both entry pressures. Drawing them twice would let one realisation's seal be tight for gas
  and loose for oil, which is not a seal.
- **`h_gas` clamps at zero, and the clamp is a real case.** When `Pc_g ≤ Pc_o` the trap holds no gas
  cap. Return `0.0`, not a negative, and not `nan` — zero is the physical answer.
- **`h_oil` must equal today's `sample_max_column_m(fluid="Oil")` exactly** on the same draws. That
  is the regression test that the new path did not quietly change the single-phase answer.
- Reuse `capillary_entry_pressure_pa` rather than re-deriving; the two unit traps documented in
  `UNIT_TRAPS` must not get a second home.

### 5.2 Engine — how it enters as a limit

**The contact the engine distributes is the OWC, and that does not change.** The engine's
`column_m` stays the hydrocarbon–water contact; the GOC is carried alongside it.

Two competing designs, and I would take the second:

| | |
|---|---|
| **A · Two limits** — a "Top seal (gas cap)" limit and a "Top seal (oil leg)" limit, both in the argmin | Wrong. They are not competing mechanisms; they are two parts of one column, and the argmin would take the shallower and report a gas cap as *the* contact. |
| **B · One limit, one passenger array** — the top-seal limit contributes `h_gas + h_oil` to the argmin exactly as today, and `h_gas` rides alongside as a per-realisation attribute | Right. The controlling-limit bookkeeping is untouched, and the GOC is only meaningful on realisations the seal actually controlled. |

Concretely: `EngineResult` grows an optional `goc_offset_m: np.ndarray | None` — metres below the
apex at which the GOC sits, `nan` where the realisation has no gas cap or was controlled by
something other than the two-phase seal. `contact_m` is unchanged. Everything downstream that does
not know about it keeps working, which is the requirement.

**The case boundary that must be in the code comment.** This is a *seal-limited* construction. In a
trap that fills to spill, gas arriving displaces oil out through the spill point: the contact stays
at spill and only the fluid split changes. The engine's `min(seal, spill)` already resolves the
contact correctly there — but the GOC from §3 is then meaningless and must be `nan`, not carried
through. Test this explicitly: a short closure with a large seal capacity must return no GOC.

### 5.3 UI

- **Seal calculator** (`sources.py`): a third `Fluid` option, `"Gas over oil"`, which swaps the
  single HC-density slider for two. Not a separate calculator — the whole point is that it is one
  seal.
- **Replace the scope note** added 7 Sep 2026 with the real thing.
- **`limiters_tab.py:484` phase clash**: currently an error telling the user to run the phases
  separately. With `"Gas over oil"` selected and the charge calculator on a mixed case, that is no
  longer a clash. The check needs a third state, and the error text needs rewriting rather than
  deleting — it is still right for the one-fluid cases.
- **One figure, and it carries the argument**: the two single-phase columns beside the two-phase
  one, showing the total *exceeding* both. This is the exhibit that justifies the feature; without
  it the number looks like a bug.
- **A gas-share readout with the tension ratio next to it**, because §4 means the number will not be
  20 % and a reader who knows the rule of thumb will otherwise assume the tool is broken.

### 5.4 Volumes — where Hood's warning lands

His "rarely equivalent to 20 % of the trap volume" needs the area–depth table, which
`hcwc/core/charge.py` already has (`AreaDepthTable`, `_fill`). Given `h_gas` and `h_oil` and the
table, the gas *volume* fraction is a lookup. **This is the single most valuable output of the whole
feature** and should not be deferred to a later pass: the column split is a curiosity, the volume
split is what gets booked.

Expect the volume share to be well below the column share on a domed closure, and to depend on
closure shape more than on any seal parameter. Worth a small table in the app on the shipped
prospect.

### 5.5 Export and report

- `hcwc/io/geox.py`, `wellvolpos.py`: check whether either target has a GOC field. If not, export
  the OWC as today and say in the report that the gas cap is not carried — do not invent a
  mapping.
- `hcwc/io/report.py`: the two-phase figure and the volume-split table follow the existing
  `figures` / `tables` registration; no new machinery.
- `hcwc/io/prospect.py`: the two new density keys need adding to `PREFIXES`/the save allow-list, and
  the `"Gas over oil"` value to whatever enum guard covers `seal_fluid`. **This has bitten before**
  (the `calibration_basis` key, 5 Sep) — a widget key not in the allow-list saves and reloads
  silently wrong.

---

## 6 · Tests

In `tests/test_seals.py` unless noted.

| | Test | Why |
|---|---|---|
| 1 | `h_oil` from the two-phase path equals `sample_max_column_m(fluid="Oil")` on the same seed | the regression guard on §5.1 |
| 2 | Gas share matches the closed form `1/(1 + (a/b)·k/(1−k))` to 1e-9 | catches any drift between the sampler and the algebra |
| 3 | Gas share is invariant to `r_seal`, `θ` and `subtract_reservoir` | the scale-free property of §3(a); if this fails the constraints are wrong |
| 4 | Total two-phase column ≥ both single-phase columns, on every realisation | §3(b), the counterintuitive result, asserted rather than trusted |
| 5 | `σ_o → σ_g` gives `h_gas → 0` continuously | §3(c) |
| 6 | `Pc_g ≤ Pc_o` gives `h_gas == 0`, never negative, never `nan` | the clamp |
| 7 | A spill-limited realisation returns `nan` GOC | §5.2's case boundary — the one that will actually be got wrong |
| 8 | `EngineResult.contact_m` is bit-identical with and without the GOC passenger array | the "nothing downstream breaks" requirement |
| 9 | Save/reload round-trips the two densities and `"Gas over oil"` | §5.5, the failure mode that has already happened once |
| 10 | The gas *volume* share is below the gas *column* share on the shipped domed closure | Hood's actual warning, made into an assertion |

In `tests/test_app_renders.py`: the new figure declares its basis, the section numbers have no gaps,
and the prose budget still passes — the note in §5.3 replaces the current expander rather than
adding to it.

---

## 7 · The cheap sibling: commodity scenarios (Hood slide 19)

Separate item, much smaller, and worth doing **first** because it needs no new physics.

> Filter realisations into Oil only, Gas only, and Dual-Phase groups … Scenario chance based on
> relative proportion of realisations in each group. Note that the HWC distribution can be
> different for three commodity scenarios.

`charge.mixed_joint` already returns `nan` GOC where there is no free gas cap, so the oil-only share
is one comparison. What is missing:

1. Expose `mixed_separate` / `mixed_joint` in `sources.render_charge_computed` — the `["Pure oil",
   "Pure gas"]` selectbox at `sources.py:89` grows two options.
2. A per-realisation commodity categorical beside `controller`, from the same run.
3. Three scenario chances from the proportions, and the contact distribution split three ways.

This is Hood's "merge late" philosophy applied to the *output*, and it fits the existing argmin
bookkeeping exactly — a second categorical alongside the controlling limit, read the same way.

**Ordering.** Do §7 first; it is small, it wires up code that already exists and is tested, and it
puts a commodity split on screen that §5 can then feed with a seal-derived GOC instead of a
charge-derived one.

---

## 8 · Sequence and cost

| | Step | Cost | Blocks |
|---|---|---|---|
| 0 | **Settle §4** — decide whether the app reproduces Hood's 20 %, and if not, say why | small, but do it first | everything |
| 1 | §7 commodity scenarios from the charge path | small | — |
| 2 | `TwoPhaseSealInputs` + sampler + tests 1–6 | small | 0 |
| 3 | Engine passenger array + tests 7–8 | medium | 2 |
| 4 | UI: third fluid option, the figure, the phase-clash rewrite | medium | 3 |
| 5 | Volume split through the area–depth table + test 10 | small | 3, and this is the payoff |
| 6 | Export, report, save allow-list + test 9 | small | 4 |

Nothing here is large. Step 0 is the only one that could change the shape of the rest, which is why
it is step 0.

---

## 9 · What would make this not worth building

Stated so it can be checked rather than assumed:

- If §4 resolves to "the derivation in §3 is not Hood's construction and the real one needs a
  leak-rate model", the cost goes up by a lot and the feature should be reconsidered rather than
  half-built.
- If no realistic NCS prospect is both two-phase *and* seal-limited rather than spill-limited, the
  feature is correct and never fires. Worth a count against the shipped dataset before step 2 —
  `hcwc/io/datasets.py` knows which discoveries are filled to spill, and the two-phase ones are
  identifiable.

## References

Hood, K. C. (2019). *Hydrocarbon Column Height*, slides 18–19. Risk Coordinator Workshop #17.
See `docs/HOOD_2019_REVIEW.md`.

Aplin, A. C. & Yang, Y. (1998) — the interfacial-tension correlations in `hcwc/core/seals.py`, and
the source of the disagreement in §4.

Sales, J. K. (1997) — the trap-class scheme Hood's "Sales Class 3" refers to. Not held here; worth
obtaining before step 0, since it is where the steady-state argument originates.
