# Validation (developer-facing)

What is checked, by what, and where the numbers live. Written in Phase 7 of the clean-up
(18 Sep 2026). The user-facing statement is 8.1.10; the pinned numbers are `docs/BASELINE.md`.

## The suite

`python -m pytest -q` with the anaconda interpreter: 21 files, about 900 test functions, all
green at every commit of the clean-up branch. Tests that render the whole app through
`AppTest` carry `@pytest.mark.render`; CI runs `-m "not render"` on pull requests (about two
minutes) and everything on `main`; the full suite runs locally before every merge (about twelve
minutes). Core and io import without Streamlit, so the numerical tests need no UI.

## By concept

| concept | validated by | file |
|---|---|---|
| Beha, Christensen & Young (2012), two-fault closure: 0.60 / 0.12 / 0.28 at three leak points | reproduced to Monte Carlo error; the one external validation of the engine | `tests/test_engine.py` |
| competing limits: single limit reproduces its distribution; inactive limits do not win; the contact is apex + column; the controller is the argmin; a fixed seed repeats | unit tests | `tests/test_engine.py` |
| copula: requested Spearman delivered; nearest-PSD projection; apex in the copula | unit tests | `tests/test_correlate.py`, `tests/test_engine.py` |
| charge: area–depth integration reproduces the cached column; mixed phases | unit tests against the shipped table | `tests/test_charge.py` |
| seal capacity: Aplin–Yang, pore-throat radius, entry pressure, mechanical column | unit tests against published points | `tests/test_seals.py` |
| elicited distributions hit their stated percentiles | unit tests | `tests/test_dists.py` |
| percentile convention: P100 shallowest, one estimator (Hazen) across the engine, the tabs and the export | unit tests | `tests/test_geox.py`, `tests/test_limit_block.py`, `tests/test_engine.py` |
| P(G) is the product and carries no threshold; POS(h) is the product with F(h) | equivalence tests | `tests/test_pos.py`, `tests/test_defaults.py` |
| consistency identity `∏ P_e(z) = P(contact > z)` in column space; the allocation reproduces P(well) | unit tests | `tests/test_decompose.py` |
| DHI: detection limits; the pick shapes; the floor `1 − c`; partial conformance; spurious density from the declared support; the posterior is the prior when the evidence is neutral | unit tests | `tests/test_dhi.py` |
| DHI invariants of the 14 Sep audit: the index never reaches the weights; the geometry never reaches P(G); POS(h_min) equals the curve at h_min; controlling shares after the update use the posterior weights; absence enters once on each side; the old double count reproduced on purpose | 22 tests | `tests/test_dhi_audit.py` |
| the three routes to c agree on an untouched tab; Monigle's rule and its ceiling | unit tests | `tests/test_dhi_audit.py`, `tests/test_defaults.py` |
| well control: what it refuses, the bracket, the floor | unit tests | `tests/test_well.py` |
| censoring: the artefact appears with zero physics; filtering does not remove it; the censored fit recovers the slope | synthetic data | `tests/test_censoring.py` |
| benchmarks: the banded model's spill weight matches the published Bernoulli; comparison verdicts | unit tests | `tests/test_benchmark_families.py`, `tests/test_calibration.py` |
| imported datasets: what is required, refusals, nothing touches disk or network | unit tests | `tests/test_datasets.py` |
| prospect file: round trip, allow-list covers every widget key, enumerations refused, examples load | unit and AppTest | `tests/test_prospect_io.py` |
| exports: E-POS import order, WellVolPOS column mapping, GeoX basis in the filename | unit tests | `tests/test_exports.py`, `tests/test_geox.py` |
| the app: every tab renders, figures registered and uniquely numbered, captions on every exhibit, the documents on tab 8, the article's numbers agree with the app | AppTest, `render` marker | `tests/test_app_renders.py` |
| run checks (trust): tail support, minimum at zero, projection, repeatability | unit tests | `tests/test_trust.py` |

## Audits on record

- `docs/AUDIT_2026-09-14.md`: the eleven core modules end to end; two defects fixed the same day.
- `docs/DHI_AUDIT_2026-09-16.md`: the DHI chain against 8.1.6–8.1.8; no inconsistency found.
- The conversation audit of 18 Sep 2026 (summarised in `docs/REPO_AUDIT.md` §8): P(G) is the
  accumulation chance everywhere; the threshold enters once; each channel updates one factor;
  one weight array reads every posterior quantity.

## Numerical baseline

`docs/BASELINE.md` pins the shipped prospect (P(G) 0.4082, F(h_min) 0.9874, POS 0.4031, the
percentiles and shares), the DHI case (LR 2.6172, P(G | s) 0.6436, POS 0.6394, the posterior
percentiles, ESS 4 872.3) and the core fixture. `docs/REFACTOR_VALIDATION.md` records what the
clean-up changed numerically: the percentile estimator only, by the last digit;
`docs/FINAL_VALIDATION_2026-09.md` records the final review of 21 Sep 2026, which changed no number.
