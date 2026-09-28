# Numerical baseline (Phase 1, 18 September 2026; the shipped prospect re-pinned 22 September 2026)

What the refactor must reproduce, on the shipped prospect and the core fixture, with the seed
and configuration named. The shipped prospect's preservation/tilt limit was re-elicited on
22 September 2026 (PERT 200 / 350 / 375 m, from a 150–400 m span with a derived mode of 250),
which moved the contact percentiles, the shares, the spreads and the effective sample size in
the rows below; every other row is as first pinned. Produced by running the app through `AppTest` and the core directly;
no code was changed. Every value below is also pinned by a test where the table says so.

## Test suite

`python -m pytest -q` at `main` `41ecd21` (after #56) and again after every commit of the clean-up: **all passed**,
1 03x tests (884 test functions, of which the `render`-marked AppTest renders are run on `main`
and locally, and skipped on pull requests by CI). No pre-existing failures. Runtime about
12 minutes locally; ~2 minutes without the render marker.

## Shipped prospect, Tiramisu-C4 (the app's default; `docs/figures/prospect.json`)

Seed 20260825, n = 10 000, assessment minimum h_min = 5 m, element chances 0.90 × 1.00 ×
0.63 × 0.72. The minimum and the evidence index below are the app's own opening values: the paper
followed them on 28 Sep 2026, and `scripts/paper_facts.py` is where both are set.

| quantity | value | pinned by |
|---|---:|---|
| P(G) | 0.4082 | `test_app_renders`, article numbers |
| F(h_min) = P(H ≥ 5 m \| G) | 1.0000 | `test_trust`, article |
| POS geological = P(G) × F(h_min) | 0.4082 | `TestThePaperAgreesWithTheAppItDescribes` |
| contact P90 / P50 / P10, h ≥ h_min, Hazen | 2 190.6 / 2 246.5 / 2 326.7 m | article (2 191 / 2 246 / 2 327) |
| the same by `np.percentile`, all realisations | identical at this minimum | no realisation has a column under 5 m, so the two estimators see the same sample |
| controlling shares, all | top seal capillary 0.336, fault leakage 0.230, top seal continuity 0.159, fault geometry 0.133, charge 0.100, spill 0.035, preservation 0.006 | article, manuscript Figure 2 |
| controlling shares, h ≥ h_min | identical to the row above, for the same reason | `test_engine` |

## DHI on the shipped prospect (index 5, σ 10 m, pick 2 250 m, c 0.36, detection defaults)

| quantity | value | pinned by |
|---|---:|---|
| LR(s) at index 5 | 1.2719 | the paper's reading |
| LR(s) at index 20 | 2.6172 | `test_dhi` (strength model), not a reading the paper quotes |
| P(G \| s) | 0.4674 | `test_dhi_audit` |
| F_post(h_min) | 1.0000 | |
| POS given the DHI = P(G \| s) × F_post(h_min) | 0.4674 | article (41 → 47 %) |
| POS(h_min) equals the curve at h_min | true (to 1e-12) | `test_dhi_audit` identity |
| posterior P90 / P50 / P10 | 2 196.7 / 2 250.0 / 2 302.7 m | article (spread 136 → 106 m) |
| effective sample size | 4 857.1 | article and post, 4 857 |
| controlling shares given the DHI, all | top seal capillary 0.417, top seal continuity 0.204, charge 0.133, fault leakage 0.122, fault geometry 0.101, spill 0.019 | 5.2.2 |
| well at z_entry 2 230 m: P(z_HCWC > z_entry \| G), geological / given the DHI | 0.5750 / 0.7655 | article (23 → 36 % with P(G)) |

## Core fixture (`limits.reference_prospect()`, seed 20260825, n 10 000)

| quantity | value |
|---|---:|
| F(h_min) | 1.0000 |
| P90 / P50 / P10 | 2 142.0 / 2 200.5 / 2 296.3 m |

## Published validation

Beha, Christensen & Young (2012), two-fault closure: leak-point frequencies 0.60 / 0.12 / 0.28
reproduced to Monte Carlo error — `tests/test_engine.py` (Beha reproduction). Kept as is.

## Other pinned behaviour the refactor must not move

- Exceedance percentile convention: P100 shallowest, P0 deepest (`test_geox`, `test_limit_block`).
- Strength never reaches the weights; geometry never reaches P(G) (`test_dhi_audit`, 22 tests).
- Absence: `1 − D(h)` within G, `(1 − d)/(1 − f·d)` on G (`test_dhi_audit`).
- Partial conformance as a censored pick; the floor `1 − c` (`test_dhi`).
- Consistency identity `∏ P_e = P(contact > z)` in column space (`test_decompose`).
- Copula delivers the requested Spearman; nearest-PSD projection reported (`test_correlate`).
- Censored fits and the artefact (`test_censoring`); seal physics (`test_seals`); charge (`test_charge`).
- Prospect file round trip and allow-list (`test_prospect_io`); exports (`test_exports`, `test_geox`).
