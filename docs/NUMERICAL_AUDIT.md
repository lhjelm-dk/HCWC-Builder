# Numerical audit (red team, Phase 1, 22 September 2026)

Read-only. Everything here was run on `385717a` (main after #71) with the project's documented
environment, the anaconda interpreter (`C:/Users/lhjel/anaconda3/python.exe`, Python 3.12.3).
Nothing was changed. `docs/BASELINE.md` and the earlier "green" records were not taken on trust;
the numbers below were regenerated.

## 1 · Test runs

### 1.1 The full suite, as documented

`python -m pytest -p no:cacheprovider -rw`, 22 Sep 2026:

| | |
|---|---|
| collected | 1 076 cases (927 test functions, 24 files) |
| render-marked (AppTest renders of `app.py`) | 188 |
| non-render | 888 |
| passed / failed / errors | 1 076 / 0 / 0 |
| warnings | none reported (`filterwarnings = error::RuntimeWarning`, so a RuntimeWarning would have failed a test) |
| runtime | 751 s (12 min 31 s) |

Streamlit and `AppTest` run in this environment; the UI suite did pass here.

### 1.2 The core numerical suite, independent of Streamlit

Run with `sys.modules["streamlit"] = None` before pytest, so any `import streamlit` raises,
`-m "not render"`, on the eighteen core-facing test files:

| | |
|---|---|
| passed | 744 |
| failed | 10, every one a `ModuleNotFoundError` on `import streamlit` raised from `hcwc/ui/theme.py`, `results_tab.py` or `dhi_tab.py` — tests that deliberately reach into the UI layer (limit colours, the tab constants, the calculator registry); not core tests |
| deselected | 13 (the same kind, in `test_charge.py` and `test_defaults.py`, excluded up front) |
| runtime | 136 s |

Conclusion: `hcwc/core` and `hcwc/io` carry no Streamlit dependence; every numerical test passes
with Streamlit unavailable. `tests/test_limit_block.py` imports a UI module at collection and was
excluded.

## 2 · Reproduced results

`python scripts/paper_facts.py` (seed 20260825, 10 000 trials, h_min 120 m, evidence index +20,
pick 2 250 ± 10 m, c 0.36, well 2 230 m), against `docs/BASELINE.md` (18 Sep 2026):

| quantity | regenerated | baseline | agree |
|---|---|---|---|
| P(G) | 0.4082 | 0.4082 | yes |
| F(h_min) geological | 0.9874 | 0.9874 | yes |
| POS geological | 0.4031 | 0.4031 | yes |
| LR(s) at +20 | 2.617 | 2.6172 | yes |
| P(G \| s) | 0.6436 | 0.6436 | yes |
| F_post(h_min) | 0.9936 | — | — |
| POS given the DHI | 0.6394 | 0.6394 | yes |
| prior HCWC P90 / P50 / P10 | 2 191.3 / 2 245.9 / 2 321.6 | same | yes |
| posterior HCWC P90 / P50 / P10 | 2 198.2 / 2 249.7 / 2 297.6 | same | yes |
| P90–P10 spread prior / posterior | 130.2 / 99.5 m | 130.3 / 99.8 m | to the digit printed |
| effective sample size | 4 872.3 | 4 872.3 | yes |
| P(well) at 2 230 m, geological / DHI | 0.2335 / 0.4969 | — | — |
| controlling shares, h ≥ h_min | 31.7 / 23.3 / 15.3 / 12.6 / 9.3 / 4.5 / 3.2 % | same | yes |

The article and the post now carry these numbers (ESS 4 872 in both; the earlier 4 871 / 4 872
disagreement was closed in #68). A render test pins every quoted number to `paper_facts()`.

## 3 · Probes run for the red-team questions

### 3.1 The "c / (1 − c)" claim (brief §4)

The seen-pick likelihood is `L(h) = c · D(h) · Pick(z | h) + (1 − c) · s`. The floor is
`L / s ≥ 1 − c`. The claim in 8.1.7, the article, the 5.1.3 caption and the walkthrough that "the
depth channel can say at most `c / (1 − c)` against any contact depth" was tested on the shipped
prospect by computing the largest ratio of likelihoods between two depths:

| pick σ | c | min L/s (floor 1 − c) | max L/s | max / min ratio between depths | claimed cap c/(1−c) |
|---:|---:|---:|---:|---:|---:|
| 10 m | 0.36 | 0.640 | 5.36 | **8.4** | 0.56 |
| 10 m | 0.90 | 0.100 | 11.9 | **119** | 9.0 |
| 5 m | 0.36 | 0.640 | 10.1 | **15.7** | 0.56 |
| 2 m | 0.90 | 0.100 | 59.1 | **591** | 9.0 |

The claim is false. The floor bounds the likelihood from below relative to the spurious
baseline; it does not bound the ratio between two depths, which is
`1 + c · D · Pick_max / ((1 − c) · s)` and grows without limit as the pick sharpens. What `c` does
guarantee: no depth's likelihood falls below `(1 − c)` times the flat alternative, so no depth is
excluded and the posterior mass of any prior region cannot fall below `(1 − c) · s / L_max` times
its prior share. Confirmed bug in the documentation, not in the arithmetic (`tests/test_dhi.py`
already pins the true statement, `L / s ≥ 1 − c`).

### 3.2 Reservoir effectiveness bounds (brief §5)

`ReservoirEffectiveness(full_to_m=2200)` and `ReservoirEffectiveness(none_below_m=2300)` both
raise `ValueError("… needs both depths …")` since #66; coincident depths are a step; both
infinite is inactive; an inverted pair is refused. Tests exist for each. The dead
`np.where(z <= full_to, 1.0, 1.0)` branch the brief cites is gone. Closed.

### 3.3 Mechanical seal, negative headroom (brief §6)

`MechanicalSealInputs` refuses only the case where every realisation has `S_Hmin ≤ P_p`
(`s_hmin_bar[1] <= pore_pressure_bar[0]`). A partly overlapping pair is accepted:
`s_hmin (220, 330)`, `pore (215, 240)` gives negative headroom in 7.1 % of draws, and
`mechanical_column_m` clips those to a 0 m column. Those realisations then enter the competition
as a contact at the apex, count against `F(h_min)` and appear in the contact histogram as a spike
at the apex — the construction the engine refuses for a depth-stated limit above the apex
("a clipped negative column would put a spike of realisations exactly at the apex, which reads
as a geological result and is not one", `engine.run`). Confirmed inconsistency: the engine's own
rule is not applied to the mechanical calculator's output. The shipped defaults (crest × gradients,
±10 / ±5 bar) do not overlap, so the app does not show it on arrival.

### 3.4 Capillary seal, negative column

`SealInputs` refuses seal and reservoir throat ranges that overlap, so the subtracted entry
pressure cannot go negative through the calculator (probed: `ValueError` at construction). A
column limit typed directly with a negative P1 is not refused by `Limit`; only depth-stated limits
above the apex are refused by the engine. Likely gap, low exposure (the tab's distribution
editors bound columns at 0).

### 3.5 Detection function edges (brief §14)

`D(0) = 0.038` (ceiling 0.90, h50 25 m, width 8 m); `D(10⁶ m) = 0.90`; steepness 0 is refused.
`D(−10⁴ m)` raises `RuntimeWarning: overflow in exp` (which the test configuration turns into an
error). The engine never produces a negative column, so it is unreachable from the app; a
`scipy.special.expit` form would remove the edge. Low.

### 3.6 Absence versus a negative index (brief §15)

`dhi.applied_ratio` returns `LR(s)` for a seen anomaly and `absence_ratio` for an absent one;
the index is ignored when the anomaly is absent. The two cannot be applied to the same
observation. The index slider stays enabled when "absent" is selected, which invites the reader
to think it matters; a UX point, not a double count.

### 3.7 Well likelihood (brief §23)

`Φ((z − z_hc)/σ) + Φ((z_w − z)/σ) − 1` is exact for one shared tie error ε ~ N(0, σ) between the
well's depths and the mapped surface (it is `Φ(b) − Φ(a)`); the clip at zero handles a contact far
outside the bracket, and the floor `1 − p_connected` keeps every depth in play. Consistent with
its docstring.

### 3.8 The shipped element chances against the limit presence probabilities (brief §7)

Reference prospect: Charge element 0.90 and a charge limit present in 100 % of realisations
(the calculator delivers a finite volume every time); Closure 1.00 and the spill always active;
Reservoir 0.63 and no reservoir limit; Retention 0.72 with top-seal capacity always present,
continuity 0.5, fault leakage 0.6, preservation 0.2. Numerically separable; the scientific
question of whether the same uncertainty is counted twice is in `docs/RED_TEAM_REVIEW.md` §7.

## 4 · What was not reproduced

The Monigle et al. (2025) rule `w = min(2 × score, 0.95)` and the Simm & Bacon 10 : 1 cap rest on
sources not in the repository; their transcription is in `docs/reviews/MONIGLE_2025_REVIEW.md`
and `docs/REFERENCES.md`. The reference distributions of the evidence index are the shipped
defaults and have no dataset in the repository to reproduce them from.
