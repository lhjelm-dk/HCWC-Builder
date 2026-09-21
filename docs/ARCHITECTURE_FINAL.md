# Architecture, after the clean-up (20 September 2026)

Developer-facing. `docs/ARCHITECTURE_CURRENT.md` is the before; this is the after.

## The shape

```
                    reference data / configuration
                    ─────────────────────────────
   reference/defaults/   area-depth table, shipped examples, concept sketch
   reference/empirical/  Edmundson (2021) columns and trap-fill matrix, bias curve
   hcwc/core/defaults.py the scientific defaults: name, unit, meaning, provenance, range
                                   │
                                   ▼
   UI  ──────────────────►  core scientific model  ──────────►  results  ──────────►  plotting / export
   app.py (shell)           hcwc/core/                          EngineResult           hcwc/plotting/app/
   hcwc/ui/concept          engine, limits, dists, correlate    DhiPosterior           hcwc/plotting/paper/
   hcwc/ui/prospect_tab     charge, seals, decompose            session_state          hcwc/io/ (prospect,
   hcwc/ui/limiters_tab     pos, dhi, dhi_comparison, well        (dhi_overlay,           geox, wellvolpos,
   hcwc/ui/results_tab      sensitivity, trust, calibration,      exhibit registry)       report)
   hcwc/ui/depth_risk_tab   censoring, defaults
   hcwc/ui/dhi_tab          no Streamlit anywhere in core or io
   hcwc/ui/empirical
   hcwc/ui/export
   hcwc/ui/theory (docs/THEORY.md, paper/ARTICLE.md, docs/REFERENCES.md)
```

Dependency direction: `ui → core`, `ui → io`, `ui → plotting`, `io → core`, `io → exhibits`;
nothing in `core`, `io` or `plotting.paper` imports `ui`. `plotting.app` imports `ui.theme` for
colours only.

## The chain, and its one implementation each

| step | function |
|---|---|
| P(G), the accumulation chance | `core.pos.accumulation_chance` |
| the limits and the competition | `core.limits.LimitSet`, `core.engine.run` |
| H, z_apex, z_HCWC = z_apex + H, the controller | `core.engine.EngineResult` |
| F(h) = P(H ≥ h \| G) | `core.engine.exceedance` / `EngineResult.exceedance` |
| percentiles (exceedance convention, Hazen, h ≥ h_min) | `core.engine.weighted_percentiles`, `EngineResult.percentiles`, `DhiPosterior.percentiles` |
| POS(h) = P(G) × F(h) | `core.pos.chance_curve`; `core.dhi.prospect_pos(_curve)` given the DHI |
| controlling shares, by depth, given the DHI | `EngineResult.controlling_shares`, `core.engine.controlling_share_by_depth`, `limit_ranking` |
| per-element chance against depth, the identity | `core.decompose` |
| evidence index → LR(s) → P(G \| s) | `core.dhi.StrengthModel.r_at`, `core.dhi.p_g_given_strength` |
| pick, c, D(h) → weights → HCWC \| G, evidence | `core.dhi.likelihood`, `core.dhi.update`, `core.well.combine` |
| absence: within G, on G | `core.dhi.likelihood` (1 − D), `core.dhi.absence_ratio` |
| what the DHI can turn out to have been: the outcomes by interval | `core.dhi.outcome_shares` on `core.dhi.likelihood_branches` |
| the comparison constructions (not headline) | `core.dhi_comparison` |
| benchmarks, censoring | `core.calibration`, `core.censoring`, `io.benchmarks`, `io.datasets` |

## Where things are

| question | answer |
|---|---|
| What is the model? | tab 8.1, `docs/THEORY.md` (eight sections following the overview figure) |
| Where is the science? | `hcwc/core/` |
| Where are the tests? | `tests/`; what they pin, `docs/VALIDATION.md` and `docs/BASELINE.md` |
| Where are the reference data? | `reference/`; the defaults, `hcwc/core/defaults.py` |
| Where are the plots? | the tabs' own figures in `hcwc/ui/*` and `hcwc/plotting/app/`; the article's in `paper/figures/` with `MANIFEST.md`, drawn by `scripts/` |
| Where is the paper? | `paper/ARTICLE.md` (tab 8.2), the manuscript and the post beside it |
| What is obsolete? | `archive/`, each directory with a README |
| What does the model assume? | `docs/ASSUMPTIONS.md`; the user-facing statement, 8.1.8 |
