# Architecture, as it is (Phase 1, 18 September 2026)

Developer-facing. Describes the repository before the clean-up; `docs/REPO_AUDIT.md` classifies
every file, `docs/BASELINE.md` records the numbers the refactor must reproduce.

## 1 · Layers

```
app.py  (Streamlit entry: 8 tabs; tab 1, 7, 8 bodies inline; loads a prospect file)
  │
  ├── hcwc/ui/        tab modules: prospect_tab, limiters_tab (+ limit_block, sources),
  │                   results_tab (+ limit_stack, depth_risk_tab, trust_panel), dhi_tab
  │                   (+ dhi_walkthrough), empirical (+ empirical_data); numbering, theme, run
  │        │
  │        ▼
  ├── hcwc/core/      engine (Monte Carlo, exceedance, percentiles), limits, dists, correlate,
  │                   charge, seals, decompose, dhi, well, sensitivity, trust, calibration,
  │                   censoring          — no Streamlit import anywhere in core
  │        │
  │        ▼
  └── hcwc/io/        prospect (save/load), epos (import), geox and wellvolpos (exports),
                      report (one page + all figures), benchmarks and datasets (reference data)

reference/            shipped data: Edmundson 2021 CSVs, area-depth table, bias curve, examples
docs/                 THEORY.md (tab 8.1), REFERENCES.md (8.3), ARTICLE.md (8.2), manuscript,
                      post, audits, reviews, plans, figures, superseded notes
scripts/              paper_figures, post_images, workflow_figure, bias_curve, edmundson_censoring
tests/                21 files, 884 test functions; `render`-marked AppTest renders of the app
```

Dependency direction is UI → core and UI → io, with two inversions:

- `hcwc/io/report.py` imports `hcwc.ui.numbering` (the exhibit registry it reads).
- `hcwc/ui/results_tab.py` and `hcwc/ui/depth_risk_tab.py` import each other (colours, the
  shared `render` for tabs 4 and 5); `hcwc/ui/limiters_tab.py` imports `results_tab` for the
  same colours. Not a cycle at import time in practice, but a smell.

## 2 · The scientific chain, and where each step lives

```
tab 2.0  element chances (play × conditional)  ──►  P(G) = ∏   [computed inline in 8 UI places]
tab 3.0  limits: P(active), depth or column    ──►  core.limits.LimitSet
                                                     │
                                                     ▼
                                     core.engine.run(limit_set, n, seed) → EngineResult
                                       column_m (H), apex_m, contact_m = apex + H, controller,
                                       above_minimum = column ≥ h_min, exceedance(h) = F(h),
                                       percentiles (h ≥ h_min, Hazen), controlling_shares
                                                     │
        ┌────────────────────────────────────────────┼─────────────────────────────┐
        ▼                                            ▼                             ▼
 tab 4.1 results_tab: histogram, F(h),      tab 4.2 core.decompose:          tab 6 core.calibration /
 P(G)·F(h) curve, well, sensitivity         P_e(z) per element, identity      censoring, io.benchmarks
                                                     │
 tab 5.1 dhi_tab:                                    │
   evidence index s → core.dhi.StrengthModel.r_at → LR(s)
   P(G | s) = core.dhi.p_g_given_strength (simm_update)         [strength: P(G) only]
   pick, c, D(h) → core.dhi.likelihood → core.dhi.update → DhiPosterior(weights)   [geometry: HCWC | G only]
   well control → core.well.combine (same weights)
   POS = core.dhi.prospect_pos = P(G | s) × posterior.pos();  curve = prospect_pos_curve
   session_state["dhi_posterior"], ["dhi_overlay"] → tabs 5.2, 5.3, 6, 7 read the same weights
```

Canonical implementations today:

| concept | canonical | duplicates / re-implementations |
|---|---|---|
| P(G) | none in core; `∏ element_pos` | `prospect_tab` 341, `results_tab` 136, `dhi_tab` 637/735/1117/1700, `dhi_walkthrough` 57, `app.py` 520 |
| F(h) | `engine.exceedance` | inline broadcast in `ui/sources.py` 452 (capacity curve); `dhi.combination_exceedance` 1160 (superseded comparison) |
| POS(h) | `EngineResult.pos`, `dhi.prospect_pos`, `dhi.prospect_pos_curve` | `_p_g_applied * exceed(grid)` in `results_tab` 1049 (same product, written out) |
| percentiles (exceedance convention) | `engine.weighted_percentiles` (Hazen midpoint) | `np.percentile(x, 100 − p)` (linear) in `limit_block` 72/159, `sources` (10 sites), `empirical` (8), `report` 218, `geox` 120, `calibration` 105 |
| contact conversion z = apex + H | `EngineResult.contact_m`; `limits.to_depth/to_column` | depth axes drawn at `median(apex_m) + h` in `results_tab`, `dhi_tab`, `dhi_walkthrough`, `report` |
| LR(s) | `dhi.StrengthModel.r_at` | — |
| strength update | `dhi.p_g_given_strength` = `dhi.simm_update` | — |
| geometry update | `dhi.likelihood`, `dhi.update` | — |
| controlling decomposition | `EngineResult.controlling_shares`, `engine.controlling_share_by_depth`, `engine.limit_ranking` | — |
| resampling a weighted posterior | `dhi.posterior_columns` | `dhi_tab._resample` (same algorithm, private) |
| histogram + exceedance figure | — | `results_tab` 4.1.1a, `dhi_tab` 5.1.4a (two blocks), `limit_stack`, `report` |

## 3 · State

Streamlit `session_state` carries the run and the DHI result between tabs: `element_pos`,
`dhi_posterior`, `dhi_overlay` (depth grid, prior and posterior curves, weights, resampled
contacts, headline numbers), `dhi_r_applied`, `dhi_r_strength`, the exhibit registries
`_figures` / `_tables`, and every widget key (`play_*`, `cond_*`, `lim_*`, `dhi_in_*`, …) which
`io/prospect.py` allow-lists for the prospect file. Tab 4 renders before tab 5 in the script,
so the overlay tab 5.2 reads is one run old until the next rerun (documented in `dhi_tab.py`).

## 4 · Configuration currently embedded in code

| what | where |
|---|---|
| element chance defaults (play, conditional) | `ui/prospect_tab.DEFAULT_RISK` |
| evidence-index reference distributions (P1/P99) | `core/dhi.StrengthModel` defaults |
| single-channel and combined LR caps (10, 50) | `core/dhi.R_SINGLE_CHANNEL`, `R_CAP` |
| contact-attribute scores and default levels | `ui/dhi_tab.CONTACT_ATTRIBUTES`, `DEFAULT_ATTRIBUTE_LEVELS` |
| shipped c, DHI score, opening index | `ui/dhi_tab.DEFAULT_CONTACT_GIVEN_HC`, `DEFAULT_DHI_SCORE`, `OPENING_STRENGTH` |
| contact-weight ceiling 0.95 | `core/dhi.CONTACT_WEIGHT_CEILING` |
| detection defaults (h50, width, ceiling, false-positive) | `core/dhi.DetectionFunction`, `ui/dhi_tab` widgets |
| shipped prospect (Tiramisu-C4) | `ui/limiters_tab.SPECS` and `reference/example_prospect*.json` |
| benchmark families, spill weight, banded model | `io/benchmarks.py` |
| default correlation table | `ui/limiters_tab` |
| seed 20260825, n 10 000 | `core/engine.run` defaults, `ui/run.py` |
| limit colours by element | `ui/results_tab.limit_colours`, `ui/theme.PILLAR_COLOURS` |
