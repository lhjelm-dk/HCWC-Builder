# Numerical baseline (Phase 1, 18 September 2026)

What the refactor must reproduce, on the shipped prospect and the core fixture, with the seed
and configuration named. Produced by running the app through `AppTest` and the core directly;
no code was changed. Every value below is also pinned by a test where the table says so.

## Test suite

`python -m pytest -q` at `main` `41ecd21` (after #56) and again after every commit of the clean-up: **all passed**,
1 03x tests (884 test functions, of which the `render`-marked AppTest renders are run on `main`
and locally, and skipped on pull requests by CI). No pre-existing failures. Runtime about
12 minutes locally; ~2 minutes without the render marker.

## Shipped prospect, Tiramisu-C4 (the app's default; `docs/figures/prospect.json`)

Seed 20260825, n = 10 000, assessment minimum h_min = 120 m, element chances 0.90 × 1.00 ×
0.63 × 0.72.

| quantity | value | pinned by |
|---|---:|---|
| P(G) | 0.4082 | `test_app_renders`, article numbers |
| F(h_min) = P(H ≥ 120 m \| G) | 0.9874 | `test_trust`, article |
| POS geological = P(G) × F(h_min) | 0.4031 | `TestThePaperAgreesWithTheAppItDescribes` |
| contact P90 / P50 / P10, h ≥ h_min, Hazen | 2 191.3 / 2 245.9 / 2 321.6 m | article (2 191 / 2 246 / 2 322) |
| the same by `np.percentile`, all realisations | 2 190.6 / 2 244.8 / 2 321.2 m | — (the linear estimator; see risk R2) |
| controlling shares, all | top seal capillary 0.320, fault leakage 0.230, top seal continuity 0.156, fault geometry 0.124, charge 0.094, preservation 0.045, spill 0.032 | article, manuscript Figure 2 |
| controlling shares, h ≥ h_min | 0.317 / 0.233 / 0.153 / 0.126 / 0.093 / 0.045 / 0.032 | `test_engine` |

## DHI on the shipped prospect (index 20, σ 10 m, pick 2 250 m, c 0.36, detection defaults)

| quantity | value | pinned by |
|---|---:|---|
| LR(s) at index 20 | 2.6172 | `test_dhi` (strength model) |
| P(G \| s) | 0.6436 | `test_dhi_audit` |
| F_post(h_min) | 0.9936 | |
| POS given the DHI = P(G \| s) × F_post(h_min) | 0.6394 | article (40 → 64 %) |
| POS(h_min) equals the curve at h_min | true (to 1e-12) | `test_dhi_audit` identity |
| posterior P90 / P50 / P10 | 2 198.2 / 2 249.7 / 2 297.6 m | article (spread 130 → 99 m) |
| effective sample size | 4 872.3 | article says 4 871 in one place and 4 872 in another (risk R5) |
| controlling shares given the DHI, all | top seal capillary 0.388, top seal continuity 0.193, charge 0.124, fault leakage 0.118, fault geometry 0.091, preservation 0.069, spill 0.016 | 5.2.2 |
| well at z_entry 2 230 m: P(z_HCWC > z_entry \| G), geological / given the DHI | 0.5719 / 0.7721 | article (23 → 50 % with P(G)) |

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
