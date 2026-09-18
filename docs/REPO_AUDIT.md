# Repository audit (Phase 1, 18 September 2026)

Inventory before the clean-up. Nothing was changed to produce it. Actions are proposals;
none is executed before approval. `S` scientific, `U` user interface, `T` test, `D` data, `P` paper.

## 1 · Python modules

| path | lines | purpose | sig. | imports (hcwc) | imported by | action | proposed location |
|---|---:|---|---|---|---|---|---|
| `app.py` | 800 | Streamlit entry: tab layout, tab 1, tab 7 export, tab 8 theory/paper/references, prospect load | U | core.charge, core.decompose, core.trust, io.benchmarks, io.geox, io.report, io.wellvolpos, ui.depth_risk_tab, ui.dhi_tab, ui.dhi_walkthrough, ui.empirical, ui.limiters_tab, ui.numbering, ui.prospect_tab, ui.results_tab, ui.run, ui.sources, ui.theme | - | KEEP, split | hcwc/ui/app.py or app.py thin; tab 1/7/8 bodies into hcwc/ui/concept.py, export.py, theory.py |
| `docs/superseded/paper_figures_mpl_2026-09-17.py` | 587 | the matplotlib paper figures superseded on 17 Sep | P archive | core.dhi, core.engine, core.limits | - | ARCHIVE | archive/old_figures/ |
| `hcwc/__init__.py` | 4 | package | - | - | - | KEEP |  |
| `hcwc/core/__init__.py` | 2 | package | - | - | - | KEEP |  |
| `hcwc/core/calibration.py` | 173 | prospect vs benchmark comparison: exceedance percentile, quantile pairs, corridor share | S | - | ui/empirical | KEEP | core/calibration.py |
| `hcwc/core/censoring.py` | 238 | censored (Tobit) fits of column vs closure; spill censoring; naive/filtered slopes | S | - | io/benchmarks, io/datasets, ui/empirical, ui/empirical_data, ui/sources, scripts/bias_curve, scripts/edmundson_censoring | KEEP | core/censoring.py |
| `hcwc/core/charge.py` | 360 | area-depth integration; charge-limited contact; oil/gas/mixed columns | S | - | app, ui/dhi_tab, ui/sources | KEEP | core/charge.py |
| `hcwc/core/correlate.py` | 192 | Gaussian copula: Spearman<->Gaussian, nearest PSD, correlated uniforms, realised correlation | S | - | core/engine, core/trust, ui/limiters_tab | KEEP | core/correlation.py (rename optional) |
| `hcwc/core/decompose.py` | 309 | per-element P_e(z) from group minima; consistency identity; WellVolPOS allocation comparison | S | core.engine, core.limits | app, io/wellvolpos, ui/depth_risk_tab, ui/limit_stack, ui/prospect_tab | KEEP | core/decomposition.py (rename optional) |
| `hcwc/core/dhi.py` | 1177 | DHI: detection D(h), observation, geometry likelihood, posterior weights, evidence-index model, LR, P(G|s), prospect_pos(_curve), absence, well of c rules; plus superseded CombinedUpdate, scenario_switch, combination_exceedance kept for the tab's comparison | S | core.dists, core.engine | docs/superseded/paper_figures_mpl_2026-09-17, core/sensitivity, ui/dhi_tab, ui/dhi_walkthrough, ui/empirical, ui/results_tab | KEEP, split | core/dhi.py (canonical chain) + core/dhi_comparison.py (scenario switch, CombinedUpdate, combination_exceedance: comparison only) |
| `hcwc/core/dists.py` | 241 | elicited distributions: normal_alt, beta, PERT, uniform; ppf/pdf | S | - | core/dhi, core/limits, io/benchmarks | KEEP | core/distributions.py (rename optional) |
| `hcwc/core/engine.py` | 377 | competing-limits Monte Carlo; EngineResult; exceedance; weighted_percentiles (Hazen); controlling shares | S | core.correlate, core.limits | docs/superseded/paper_figures_mpl_2026-09-17, core/decompose, core/dhi, core/sensitivity, core/trust, core/well, io/report, io/wellvolpos, ui/empirical, ui/empirical_data, ui/limit_block, ui/limit_stack, ui/limiters_tab, ui/prospect_tab, ui/results_tab, ui/run, scripts/paper_figures | KEEP | core/engine.py |
| `hcwc/core/limits.py` | 444 | Limit, LimitSet, Group, DepthDistribution; depth/column conversion; reference_prospect fixture; save/load | S | core.dists | docs/superseded/paper_figures_mpl_2026-09-17, core/decompose, core/engine, core/sensitivity, io/prospect, io/report, io/wellvolpos, ui/depth_risk_tab, ui/limit_block, ui/limit_stack, ui/limiters_tab, ui/prospect_tab, ui/results_tab, ui/run, ui/sources, scripts/paper_figures | KEEP | core/limits.py |
| `hcwc/core/seals.py` | 560 | capillary seal capacity, MICP, permeability, mechanical seal | S | - | ui/sources | KEEP | core/seals.py |
| `hcwc/core/sensitivity.py` | 262 | tornado (conditional means, geological and DHI) | S | core.dhi, core.engine, core.limits | ui/dhi_tab, ui/results_tab | KEEP | core/sensitivity.py |
| `hcwc/core/trust.py` | 381 | run checks: tail support, concentration, minimum, projection, repeatability, DHI evidence | S | core.correlate, core.engine | app, ui/results_tab, ui/trust_panel | KEEP | core/trust.py (or validation/checks.py) |
| `hcwc/core/well.py` | 167 | well control likelihood and combine with DHI weights | S | core.engine | ui/dhi_tab, ui/prospect_tab, ui/results_tab | KEEP | core/well.py |
| `hcwc/dhi/__init__.py` | 2 | empty package, nothing imports it | - | - | - | DELETE (empty; no content) |  |
| `hcwc/io/__init__.py` | 2 | package | - | - | - | KEEP |  |
| `hcwc/io/benchmarks.py` | 208 | loads Edmundson CSVs; Graham column model; NCS seal-capacity family; shrink_toward | S/D | core.censoring, core.dists | app, ui/empirical, ui/empirical_data, ui/sources, scripts/edmundson_censoring | KEEP | io/benchmarks.py; the banded model constants -> reference/benchmarks/ |
| `hcwc/io/datasets.py` | 310 | user-imported column-height dataset: read, fit, never written to disk | S/D | core.censoring | ui/empirical, ui/empirical_data | KEEP | io/datasets.py |
| `hcwc/io/epos.py` | 158 | E-POS prospect import (element chances) | U/D | - | ui/prospect_tab | KEEP | io/epos.py |
| `hcwc/io/geox.py` | 128 | 101-percentile export with provenance | U/D | - | app | KEEP | io/geox.py |
| `hcwc/io/prospect.py` | 357 | prospect file save/load with allow-list and value checks | U/D | core.limits | ui/prospect_tab | KEEP | io/prospect.py |
| `hcwc/io/report.py` | 526 | one-page report and the full figure export (reads the exhibit registry) | U | core.engine, core.limits, ui.numbering | app | KEEP | io/report.py; its dependency on hcwc.ui.numbering is a layering inversion to remove |
| `hcwc/io/wellvolpos.py` | 146 | trial table and element curves for WellVolPOS | U/D | core.decompose, core.engine, core.limits | app | KEEP | io/wellvolpos.py |
| `hcwc/ui/__init__.py` | 2 | package | - | - | - | KEEP |  |
| `hcwc/ui/depth_risk_tab.py` | 421 | tabs 4.2 / 5.3: per-element chance against depth | U | core.decompose, core.limits, ui.numbering, ui.results_tab, ui.run, ui.theme | app, ui/results_tab | KEEP | ui/results.py (sub-tab) or ui/depth_risk.py |
| `hcwc/ui/dhi_tab.py` | 1761 | tab 5.1: the DHI observation, index, c, D(h), well, headline, ESS, assumptions, diagnostics, scenario switch; builds dhi_overlay | U (+ 8 inline P(G) products) | core.charge, core.dhi, core.sensitivity, core.well, ui.numbering, ui.run, ui.sources, ui.theme | app, ui/results_tab | KEEP, trim | ui/dhi.py; inline P(G) products -> core |
| `hcwc/ui/dhi_walkthrough.py` | 318 | 8.1.6's walkthrough of the update on the live prospect | U | core.dhi, ui.numbering, ui.theme | app | KEEP | ui/theory.py or ui/dhi_walkthrough.py |
| `hcwc/ui/empirical.py` | 1281 | tab 6: benchmarks, censoring views, probit, dataset import, families | U (+ inline np.percentile) | core.calibration, core.censoring, core.dhi, core.engine, io.benchmarks, io.datasets, ui.empirical_data, ui.numbering, ui.run, ui.theme | app | KEEP, trim | ui/benchmarks.py; percentile rows -> core.engine.weighted_percentiles |
| `hcwc/ui/empirical_data.py` | 178 | tab 6 data plumbing: bias curve, empirical prior, exceedance | U/S | core.censoring, core.engine, io.benchmarks, io.datasets | ui/empirical | KEEP | ui/benchmarks_data.py or io/ |
| `hcwc/ui/limit_block.py` | 286 | one limit's elicitation block and its stats row | U (+ inline np.percentile) | core.engine, core.limits, ui.theme | ui/limiters_tab | KEEP | ui/limiters.py; stats_row -> core percentiles |
| `hcwc/ui/limit_stack.py` | 445 | Figure 4.1.2e: all limits on one axis (no streamlit; plotly only) | U/plot | core.decompose, core.engine, core.limits, ui.theme | ui/results_tab | MOVE | plotting/app/limit_stack.py |
| `hcwc/ui/limiters_tab.py` | 570 | tab 3: limit specs, correlations, ranking, checks | U | core.correlate, core.engine, core.limits, ui.limit_block, ui.numbering, ui.results_tab, ui.run, ui.sources, ui.theme | app | KEEP | ui/limiters.py |
| `hcwc/ui/numbering.py` | 304 | exhibit numbering and registry; captions | U | ui.theme | app, io/report, ui/depth_risk_tab, ui/dhi_tab, ui/dhi_walkthrough, ui/empirical, ui/limiters_tab, ui/prospect_tab, ui/results_tab, scripts/post_images | KEEP | ui/numbering.py |
| `hcwc/ui/prospect_tab.py` | 527 | tab 2: apex, spill, element chances, P(G), assessment minimum, well, examples | U | core.decompose, core.engine, core.limits, core.well, io.epos, io.prospect, ui.numbering, ui.run, ui.theme | app, ui/sources | KEEP | ui/prospect.py |
| `hcwc/ui/results_tab.py` | 1219 | tabs 4.1 / 5.2: competition figure, controller, chance against depth, well, sensitivity 2e, checks | U (+ inline P(G)) | core.dhi, core.engine, core.limits, core.sensitivity, core.trust, core.well, ui.depth_risk_tab, ui.dhi_tab, ui.limit_stack, ui.numbering, ui.run, ui.theme, ui.trust_panel | app, ui/depth_risk_tab, ui/limiters_tab | KEEP, split | ui/results.py + plotting/app/ for the figures |
| `hcwc/ui/run.py` | 85 | cached engine run keyed on the limit set | U | core.engine, core.limits | app, ui/depth_risk_tab, ui/dhi_tab, ui/empirical, ui/limiters_tab, ui/prospect_tab, ui/results_tab, ui/trust_panel | KEEP | ui/run.py |
| `hcwc/ui/sources.py` | 1137 | calculators as limit sources: charge, seal, seal-as-top, mechanical, empirical | U/S (calculator glue; inline exceedance and np.percentile) | core.censoring, core.charge, core.limits, core.seals, io.benchmarks, ui.prospect_tab, ui.theme | app, ui/dhi_tab, ui/limiters_tab | KEEP, trim | ui/sources.py; the exceedance broadcast at 452 -> engine.exceedance |
| `hcwc/ui/theme.py` | 474 | tab colours, headings, section tracking, basis tags | U | - | app, ui/depth_risk_tab, ui/dhi_tab, ui/dhi_walkthrough, ui/empirical, ui/limit_block, ui/limit_stack, ui/limiters_tab, ui/numbering, ui/prospect_tab, ui/results_tab, ui/sources, ui/trust_panel | KEEP | ui/theme.py |
| `hcwc/ui/trust_panel.py` | 96 | renders trust checks | U | core.trust, ui.run, ui.theme | ui/results_tab | KEEP | ui/trust_panel.py |
| `hcwc/viz/__init__.py` | 2 | empty package, nothing imports it | - | - | - | DELETE (empty; no content) |  |
| `scripts/bias_curve.py` | 59 | regenerates reference/bias_curve.json (errors-in-variables curve) | S/D tool | core.censoring | - | KEEP | scripts/ |
| `scripts/edmundson_censoring.py` | 66 | stand-alone censoring analysis of the Edmundson data | S tool | core.censoring, io.benchmarks | - | KEEP | scripts/ or validation/ |
| `scripts/paper_figures.py` | 156 | prospect.json and the concept sketch fig5 | P tool | core.engine, core.limits | - | KEEP | plotting/paper/ |
| `scripts/post_images.py` | 127 | exports app figures for the post and the article | P tool | ui.numbering | - | KEEP | plotting/paper/ (app exports) |
| `scripts/workflow_figure.py` | 240 | the workflow SVG, two versions, rasterised | P/U tool | - | - | KEEP | plotting/paper/workflow_figure.py |

## 2 · Public functions and classes (the before-inventory, §28)

- `app.py`: -
- `docs/superseded/paper_figures_mpl_2026-09-17.py`: from_the_app, save, figure_1_competing_limits, figure_2_controlling_mechanism, figure_3_survival, figure_4_dhi_update, figure_5_truncate_vs_terminate, figure_6_paper, main
- `hcwc/core/calibration.py`: exceedance_percentile, compare, quantile_pairs, exceedance_grid, corridor_share, quantile_ratios; classes: Comparison(ratio, verdict, sentence)
- `hcwc/core/censoring.py`: spill_censoring, censored_slope, censored_loglinear, naive_slope, filtered_slope; classes: CensoredFit(censored_fraction); CensoredMultiFit()
- `hcwc/core/charge.py`: oil_contact, gas_contact, mixed_separate, mixed_joint, column_height_from_contact, columns_below_apex, table_short_of_spill; classes: AreaDepthTable(apex_m, deepest_m, grv_1e6m3, capacity_1e6m3, depth_at_grv, from_csv, reference, from_top_and_thickness); ChargeResult(not_limiting, fraction_not_limiting, dry); ChargeColumns()
- `hcwc/core/correlate.py`: spearman_to_gaussian, gaussian_to_spearman, nearest_correlation_matrix, build_matrix, correlated_uniforms, realised_spearman, describe
- `hcwc/core/decompose.py`: limit_curves_at_depth, decompose, allocation_comparison; classes: ReservoirEffectiveness(active, at); Decomposition(residual_depth, residual_column, max_abs_residual_column, max_abs_residual_depth, apex_contribution, element_pos_at_depth, factorised_pos, direct_pos)
- `hcwc/core/dhi.py`: min_failures_for_r, spurious_density, likelihood, posterior_columns, update, p_g_given_strength, absence_ratio, applied_ratio, prospect_pos, prospect_pos_curve, outcome, leverage, scenario_switch, area_cross_check, containment_ok, contact_weight_from_score, simm_update, volume_weight, strength_bands, combination_exceedance; classes: DetectionFunction(at); DhiObservation(is_partial, pick_pdf, pick_ppf); DhiPosterior(effective_sample_size, exceedance, pos, percentiles, r_dhi); Outcome(); Leverage(measurable, inert); StrengthCase(mean, sd, pdf); StrengthModel(r_at, strength_at); CombinedUpdate(r_combined, posterior_pos, volume_weight)
- `hcwc/core/dists.py`: bernoulli, normal_alt, normal_alt_params, beta_general, beta_subj_params, beta_subj, pert, normal_alt_ppf, beta_general_ppf, beta_subj_ppf, pert_ppf, uniform_ppf, beta_general_pdf, pert_pdf, uniform_pdf
- `hcwc/core/engine.py`: weighted_percentiles, run, limit_ranking, controlling_share_by_depth, exceedance; classes: EngineResult(n, contact_m, above_minimum, pos, exceedance, group_minimum, realised_correlation, realised_pairs, controlling_shares, percentiles)
- `hcwc/core/limits.py`: to_depth, to_column, convert, reference_prospect, group_totals; classes: Group(); DepthDistribution(ppf, from_samples, to_dict, from_dict); Limit(always_active, is_depth, label_for, unit_label, to_dict, from_dict); LimitSet(names, correlated_names, groups, indices_in, contact_support_m, to_dict, from_dict, save, load)
- `hcwc/core/seals.py`: interfacial_tension_gas_dyne_cm, void_ratio_from_porosity, pore_throat_radius_nm, pore_throat_radius_m, porosity_from_depth, depth_from_porosity, pore_throat_radius_from_micp_um, capillary_entry_pressure_pa, buoyancy_pressure_pa, max_column_height_m, column_height_from_entry_pressure_m, entry_pressure_bar, entry_pressure_spread, sperrevik_permeability_md, manzocchi_permeability_md, max_column_height_curve, sample_max_column_m, fracture_headroom_bar, mechanical_column_m, sample_mechanical_column_m; classes: SealInputs(); MechanicalSealInputs()
- `hcwc/core/sensitivity.py`: tornado, baseline, effective_n, dhi_tornado, dhi_baseline; classes: Effect(swing, magnitude)
- `hcwc/core/trust.py`: tail_support, concentration, assessment_minimum, correlation_projection, repeatability, dhi_evidence, review, headline; classes: Check(icon)
- `hcwc/core/well.py`: likelihood, combine; classes: WellControl(proves_hydrocarbons, bracket)
- `hcwc/io/benchmarks.py`: load_edmundson, load_edmundson_matrix, graham_column_height, spill_weight, ncs_seal_capacity, shrink_toward; classes: Benchmark(n, censored_fraction)
- `hcwc/io/datasets.py`: read_csv, fit, column_height; classes: Dataset(n, usable, censored_fraction, full_model); DatasetError()
- `hcwc/io/epos.py`: read_epos_csv, read_json, read, to_json; classes: ElementPos()
- `hcwc/io/geox.py`: percentile_table; classes: PercentileExport(to_csv, provenance)
- `hcwc/io/prospect.py`: document, to_json, read
- `hcwc/io/report.py`: build, build_full; classes: Provenance()
- `hcwc/io/wellvolpos.py`: missing_for_wellvolpos, trial_table, element_curve_table, provenance
- `hcwc/ui/depth_risk_tab.py`: render
- `hcwc/ui/dhi_tab.py`: well_control, render
- `hcwc/ui/dhi_walkthrough.py`: render
- `hcwc/ui/empirical.py`: dhi_columns, render
- `hcwc/ui/empirical_data.py`: imported_label
- `hcwc/ui/limit_block.py`: stats_row, render
- `hcwc/ui/limit_stack.py`: default_window, figure
- `hcwc/ui/limiters_tab.py`: render; classes: LimitSpec()
- `hcwc/ui/numbering.py`: render_caption, theme_tag, figure_order; classes: Numbering(stem, optional, upcoming, ref, plot, table, image, markdown_table)
- `hcwc/ui/prospect_tab.py`: example_buttons, gradient_range, temperature_range, render
- `hcwc/ui/results_tab.py`: limit_colours, render, render_trust_panel
- `hcwc/ui/run.py`: run, current, repeat_of
- `hcwc/ui/sources.py`: render_charge, render_seal, render_empirical, render_charge_computed, render_empirical_computed, render_seal_computed, is_base_seal, render_seal_as_top, render_seal_as_top_computed, current_area_depth, calibration_figure, render_mechanical, render_mechanical_computed; classes: Handover()
- `hcwc/ui/theme.py`: tab_labels, subtab_marker, apply, accent, section_label, heading, subsection, subheading_markdown, subheading, evidence_basis, evidence_title, basis_banner, basis_tag, element_heading, shade_hex, rgba, element_shades
- `hcwc/ui/trust_panel.py`: stop_card, render
- `scripts/bias_curve.py`: compute
- `scripts/edmundson_censoring.py`: main
- `scripts/paper_figures.py`: from_the_app, save, figure_5_truncate_vs_terminate, main
- `scripts/post_images.py`: main
- `scripts/workflow_figure.py`: text, box, arrow, rail, lane, draw, rasterise, main

## 3 · Tests

| file | tests | covers |
|---|---:|---|
| `tests/test_app_renders.py` | 138 | AppTest renders of every tab (render marker); numbering, captions, documents, prospect save |
| `tests/test_benchmark_families.py` | 5 | banded benchmark model |
| `tests/test_calibration.py` | 30 | prospect vs benchmark comparison |
| `tests/test_censoring.py` | 30 | censoring artefact and censored fits |
| `tests/test_charge.py` | 50 | area-depth integration, charge contact, mixed phases |
| `tests/test_correlate.py` | 31 | copula, nearest PSD, realised correlation |
| `tests/test_datasets.py` | 22 | imported dataset reading and fitting; no disk/network |
| `tests/test_decompose.py` | 38 | consistency identity, element curves, allocation |
| `tests/test_dhi.py` | 162 | detection, observation, likelihood, posterior, strength model, bounds, scenario switch |
| `tests/test_dhi_audit.py` | 26 | the 14 Sep audit invariants: strength never reaches the weights, POS identity, Monigle rule |
| `tests/test_dists.py` | 24 | elicited distributions |
| `tests/test_engine.py` | 84 | engine: single limit, minimum, inactive, Beha 2012 reproduction, seed, controller |
| `tests/test_exports.py` | 19 | E-POS import, WellVolPOS export |
| `tests/test_geox.py` | 22 | percentile convention and export |
| `tests/test_limit_block.py` | 9 | stats row convention |
| `tests/test_numbering.py` | 24 | exhibit numbering |
| `tests/test_prospect_io.py` | 27 | prospect file round trip, allow-list, enumerations |
| `tests/test_seals.py` | 80 | seal capacity physics |
| `tests/test_trust.py` | 15 | run checks |
| `tests/test_ui_imports.py` | 25 | UI modules import; tab numbers; LR formatting |
| `tests/test_well.py` | 23 | well control likelihood |

## 4 · Non-Python files

| path | purpose | action |
|---|---|---|
| `.gitattributes` | line endings | KEEP |
| `.github/workflows/ci.yml` | CI: not-render on PRs, all on main | KEEP |
| `.gitignore` | ignores _private/, reference/private/ | KEEP |
| `.streamlit/config.toml` | theme | KEEP |
| `CLAUDE.md` | working instructions: tone, structure, numbering, constraints | KEEP (developer-facing) |
| `LICENSE` | MIT | KEEP |
| `README.md` | STALE: says Phase 6, points at a plan in _private/ | KEEP, rewrite |
| `pyproject.toml` | pytest config, render marker | KEEP |
| `requirements.txt` | runtime deps | KEEP |
| `requirements-dev.txt` | dev deps | KEEP |
| `runtime.txt` | python version for Streamlit Cloud | KEEP |
| `docs/ARTICLE.md` | the short article (8.2), protected | KEEP -> paper/ARTICLE.md (app.py and tests point at docs/; move with them) |
| `docs/ARTICLE_LONG_2026-09.md` | the long manuscript, protected | KEEP -> paper/ |
| `docs/LINKEDIN_POST.md` | the post draft | KEEP -> paper/ |
| `docs/THEORY.md` | tab 8.1, the single statement of the method | KEEP |
| `docs/REFERENCES.md` | tab 8.3 bibliography | KEEP |
| `docs/DHI_alignment.md` | signed working note, 25 Aug, superseded in parts by the 14 Sep audit; §0 records the corrected chain | ARCHIVE candidate: developer note; keep as history (archive/development_notes/) |
| `docs/AUDIT_2026-09-14.md` | numerical audit of the core | KEEP -> docs/VALIDATION.md source or archive/development_notes/ |
| `docs/DHI_AUDIT_2026-09-16.md` | DHI mathematical audit | KEEP -> same |
| `docs/EXPLANATION_MAP_2026-09-16.md` | where each explanation lives | ARCHIVE (superseded by tab 8's map) |
| `docs/IFT_CHECK_2026-09-15.md` | interfacial-tension check | ARCHIVE (development note) |
| `docs/OPEN_QUESTIONS_2026-09-15.md` | open decisions | KEEP (developer-facing) |
| `docs/NEXT_PLAN.md` | what to build next | KEEP (developer-facing) |
| `docs/PLAN_DUAL_PHASE_SEAL.md` | parked design | KEEP (developer-facing) |
| `docs/BEHA_2012_REVIEW.md` | paper review | KEEP -> docs/reviews/ (developer-facing) |
| `docs/HOOD_2019_REVIEW.md` | paper review | KEEP -> docs/reviews/ |
| `docs/LOWRY_2005_REVIEW.md` | paper review from the abstract | KEEP -> docs/reviews/ |
| `docs/MONIGLE_2025_REVIEW.md` | paper review; names the source the user-facing text must not | KEEP -> docs/reviews/ (developer-facing only) |
| `docs/SEAL_CAPACITY_REVIEW.md` | seal physics review | KEEP -> docs/reviews/ |
| `docs/figures/prospect.json` | the worked prospect the figures are drawn from | KEEP -> paper/figures/ |
| `reference/area_depth.csv` | shipped area-depth table | KEEP -> reference/defaults/ |
| `reference/bias_curve.json` | errors-in-variables curve | KEEP -> reference/empirical/ |
| `reference/concept.png` | tab 1 concept sketch | KEEP -> reference/defaults/ or docs/figures |
| `reference/concept_full.png` | unused? check | ARCHIVE if unused |
| `reference/edmundson_2021_ncs_columns.csv` | Edmundson 2021 CC-BY data | KEEP -> reference/empirical/ |
| `reference/edmundson_2021_trapfill_matrix.csv` | Edmundson 2021 trap-fill matrix | KEEP -> reference/empirical/ |
| `reference/example_prospect.hcwc.json` | shipped example, seal-limited | KEEP -> reference/defaults/ |
| `reference/example_prospect_spill.hcwc.json` | shipped example, spill-limited | KEEP -> reference/defaults/ |
| `docs/figures/*.png, *.svg` (10) | the article's figures, app exports and the workflow SVG | KEEP -> paper/figures/ |
| `docs/post/*.png` (11) | the post's images | KEEP -> paper/post/ |
| `docs/superseded/*.md` (5 + README) | theory notes absorbed into THEORY.md on 16 Sep | ARCHIVE -> archive/superseded_notes/ |
| `docs/superseded/*.png` (6) | the raster workflow figure and the matplotlib paper figures | ARCHIVE -> archive/old_figures/ |

## 5 · Duplicated scientific logic

Same formula, several copies; no two copies were found to implement different definitions
of the same quantity except the percentile estimator (R2).

| concept | canonical | copies | proposed |
|---|---|---|---|
| P(G) = ∏ element chances | none in core | `ui/prospect_tab.py:341`, `ui/results_tab.py:136`, `ui/dhi_tab.py:637, 735, 1117, 1700`, `ui/dhi_walkthrough.py:57`, `app.py:520` | one function `core.pos.accumulation_chance(element_pos)` (or a `Prospect` value object); callers redirected; equivalence test |
| F(h) exceedance | `core.engine.exceedance` | `ui/sources.py:452` (broadcast for the capacity curve); `core.dhi.combination_exceedance:1160` (superseded comparison) | redirect the first; the second moves with the comparison module |
| exceedance percentiles | `core.engine.weighted_percentiles` (Hazen midpoint, since audit P3-4) | `np.percentile(x, 100 − p)` (linear) at `ui/limit_block.py:72,159`, `ui/sources.py` (ten sites), `ui/empirical.py` (eight), `io/report.py:218`, `io/geox.py:120`, `core/calibration.py:105,128` | **R2**: same convention, different estimator; consolidating changes the last digit of printed limit and capacity percentiles. Decision needed. |
| POS(h) = P(G) × F(h) | `EngineResult.pos` × P(G) in callers; `core.dhi.prospect_pos(_curve)` | `ui/results_tab.py:1049` writes the product out; `ui/dhi_tab.py:1702` too | a `core.pos.chance_curve(p_g, exceedance)` used by all |
| resampling a weighted posterior | `core.dhi.posterior_columns` (seed 20260904, columns) | `ui/dhi_tab._resample` (seed 20260827, contacts) | **R4**: one function; the export's sample changes draw-for-draw if the seed is unified. Decision needed. |
| depth axis under a column-space curve | convention `median(apex) + h` | `results_tab` (4.1.1a, 4.1.3a), `dhi_tab` (5.1.4a, overlay), `dhi_walkthrough`, `io/report.py:120, 261` | one helper `core.engine.depth_axis(result, h)`; or the optional exact form (audit of 18 Sep, "optional change") |
| limit colours | `ui/results_tab.limit_colours` from `theme.PILLAR_COLOURS` | `docs/superseded/paper_figures_mpl…COLOURS` (archive) | keep one, in `plotting/` |
| histogram + exceedance figure | — | `results_tab` 4.1.1a right panel, `dhi_tab` 5.1.4a (two blocks), `limit_stack`, `report` | one figure builder in `plotting/app/contact.py` |
| controlling shares by depth figure | `engine.controlling_share_by_depth` (data) | drawn in `results_tab` 4.1.2a, 4.1.3a, `dhi_tab` | one builder in `plotting/app/controller.py` |

## 6 · Duplicated or overlapping explanatory text

| where | overlap | proposed |
|---|---|---|
| `docs/THEORY.md` (tab 8.1) vs `docs/ARTICLE_LONG_2026-09.md` | the manuscript restates 8.1.2 to 8.1.6 at length with its own numbers | keep both: the manuscript is protected; note in the manuscript's header that 8.1 is authoritative for the tool's current wording |
| `docs/THEORY.md` vs `docs/DHI_alignment.md` | the signed note's §0 states the corrected chain, its later sections the pre-14-Sep construction | archive as a development note with a header pointing at 8.1.4–8.1.6 |
| `docs/superseded/*.md` | absorbed into THEORY on 16 Sep | archive |
| `docs/EXPLANATION_MAP_2026-09-16.md` | superseded by tab 8's map paragraph and CLAUDE.md | archive |
| `docs/AUDIT_2026-09-14.md`, `docs/DHI_AUDIT_2026-09-16.md` | the two audits; their findings are in tests and 8.1.8 | keep, referenced from `docs/VALIDATION.md` |
| `CLAUDE.md`, `README.md` | README is stale (Phase 6, a private plan) | README rewritten from ARCHITECTURE_FINAL; CLAUDE.md stays the working instruction |
| tab captions vs 8.1 | every tab says "Method: see 8.1.x"; no page of theory remains on a tab | fine |
| `docs/LINKEDIN_POST.md` captions | still use "strength" for the index (images 7–10) | align in Phase 8 |

## 7 · Scientific content inventory (§29)

| concept | implementation | documentation | tests | final location |
|---|---|---|---|---|
| accumulation chance P(G); element chances | `ui/prospect_tab` (∏), `io/epos` import | 8.1.1 | `test_app_renders`, `test_exports` | `core/pos.py` |
| competing limits; shallowest active wins; controller | `core/engine.run` | 8.1.2 | `test_engine` | unchanged |
| charge limitation; area–depth; mixed phases | `core/charge` | 8.1.2, `SEAL_CAPACITY_REVIEW` | `test_charge` | unchanged |
| spill / closure | `core/limits` (always-active spill), `ui/prospect_tab` | 8.1.2 | `test_engine` | unchanged |
| fault seal (geometry, leakage) | `ui/limiters_tab.SPECS`, `core/limits` | 8.1.2 | `test_engine` | reference/defaults |
| capillary seal capacity; MICP; pore throat | `core/seals` | 8.1.2, `SEAL_CAPACITY_REVIEW` | `test_seals` | unchanged |
| seal continuity; mechanical seal | `core/limits`, `core/seals.mechanical_column_m` | 8.1.2 | `test_seals` | unchanged |
| reservoir; pinch-out; effectiveness decline | `core/limits`, `core/decompose.ReservoirEffectiveness` | 8.1.2, 8.1.3 | `test_decompose` | unchanged |
| correlations; copula; apex pairing | `core/correlate`, `core/engine.run` | 8.1.2 | `test_correlate`, `test_engine` | `core/correlation.py` |
| HCWC, column height H, contact depth z_HCWC | `EngineResult.column_m`, `contact_m` | 8.1.3 | `test_engine` | unchanged |
| assessment minimum h_min; F(h); POS(h) | `EngineResult.above_minimum`, `.pos`, `.exceedance` | 8.1.3 | `test_trust`, `test_engine` | + `core/pos.py` |
| depth-dependent risk per element | `core/decompose` | 8.1.3 | `test_decompose` | `core/decomposition.py` |
| controlling mechanism; by depth; given the DHI | `EngineResult.controlling_shares`, `engine.controlling_share_by_depth`, `limit_ranking` | 8.1.2, 8.1.5 | `test_engine`, `test_dhi_audit` | unchanged |
| DHI evidence index; reference densities; LR(s) | `core/dhi.StrengthModel`, `StrengthCase` | 8.1.4 | `test_dhi` | unchanged; defaults → reference/defaults |
| strength update P(G \| s) | `core/dhi.p_g_given_strength`, `simm_update` | 8.1.4 | `test_dhi_audit` | unchanged |
| DHI geometry: pick, attribution c, detection D(h), partial conformance, spurious density | `core/dhi.DhiObservation`, `DetectionFunction`, `likelihood`, `spurious_density` | 8.1.5 | `test_dhi`, `test_dhi_audit` | unchanged |
| c's three routes; Monigle rule; ceiling 0.95 | `ui/dhi_tab` (routes), `core/dhi.contact_weight_from_score` | 8.1.5 | `test_dhi_audit`, `test_prospect_io` | attribute scores → reference/defaults |
| DHI absence: within G and on G | `core/dhi.likelihood` (1 − D), `absence_ratio`, `applied_ratio` | 8.1.4, 8.1.5 | `test_dhi_audit` | unchanged |
| posterior HCWC; ESS; percentiles conditional on h_min | `core/dhi.update`, `DhiPosterior` | 8.1.5 | `test_dhi` | unchanged |
| posterior POS(h) = P(G \| s) × F_post(h); identity | `core/dhi.prospect_pos`, `prospect_pos_curve` | 8.1.6 | `test_dhi_audit` | unchanged |
| well control | `core/well` | 8.1.5 | `test_well` | unchanged |
| scenario switch; CombinedUpdate; pooled/Bayes combinations | `core/dhi.scenario_switch`, `CombinedUpdate`, `combination_exceedance` | 8.1.6 (comparison) | `test_dhi` | `core/dhi_comparison.py` |
| sensitivity (tornado, leverage) | `core/sensitivity`, `core/dhi.leverage` | 8.1.8 | `test_dhi` | unchanged |
| run checks (trust) | `core/trust` | 8.1.8 | `test_trust` | `validation/` or unchanged |
| empirical benchmarks; families; banded model | `io/benchmarks`, `core/calibration`, `ui/empirical(_data)` | 8.1.7 | `test_benchmark_families`, `test_calibration` | data → reference/empirical |
| filled-to-spill censoring; Tobit fits | `core/censoring`, `scripts/edmundson_censoring.py`, `reference/bias_curve.json` | 8.1.7 | `test_censoring` | unchanged |
| imported datasets (never written) | `io/datasets` | 8.1.7 | `test_datasets` | unchanged |
| Beha 2012 validation | `tests/test_engine.py` | 8.1.2, 8.1.8, `BEHA_2012_REVIEW` | `test_engine` | + `docs/VALIDATION.md` |
| WellVolPOS export; GeoX export; E-POS import; prospect file; report | `io/wellvolpos`, `io/geox`, `io/epos`, `io/prospect`, `io/report` | tab 7 | `test_exports`, `test_geox`, `test_prospect_io`, `test_app_renders` | unchanged |
| exhibit numbering | `ui/numbering`, `ui/theme` | CLAUDE.md | `test_numbering` | unchanged |

## 8 · Risks found (report, not fixed)

- **R1 — none of the stop conditions on P(G), the threshold, double counting or the weights
  fired.** Audit of 18 Sep 2026 in the conversation record: P(G) is the accumulation chance
  everywhere; the threshold enters through `F(h_min)` only; strength updates P(G) only; the
  geometry updates the weights only; posterior HCWC, POS and controlling shares read one
  weight array.
- **R2 — two percentile estimators.** The engine and the posterior use Hazen midpoints
  (`weighted_percentiles`); limit blocks, calculators, the benchmark tab, the report's limit
  table and the GeoX export use `np.percentile`'s linear order statistics. Same exceedance
  convention, last-digit differences (shipped P50: 2 245.9 vs 2 244.8 m). Consolidating is a
  numerical change and needs approval; leaving it needs a sentence in 8.1.3.
- **R3 — the strength curves' provenance.** The app's reference distributions are the E-POS
  defaults (P1/P99 −50…100, −100…50). Their origin beyond E-POS is not documented in this
  repository. The stop condition on documenting provenance is met by *not* documenting it in
  user-facing text (done in #55); the developer note `docs/MONIGLE_2025_REVIEW.md` and the
  archived `DHI_alignment.md` name the source and stay developer-facing.
- **R4 — two resamplers with two seeds** (`dhi.posterior_columns`, `dhi_tab._resample`).
  Unifying changes the export's sample draw-for-draw, not its distribution.
- **R5 — the article prints ESS 4 871 once and 4 872 elsewhere**; the baseline is 4 872.3.
- **R6 — `io/report.py` imports `hcwc.ui.numbering`**: a layering inversion; the registry
  belongs to a neutral module.
- **R7 — the README is stale** (Phase 6; a plan in `_private/`).
- **R8 — `hcwc/dhi/` and `hcwc/viz/` are empty packages**; nothing imports them.
- **R9 — CI cannot run** (Actions minutes) until 1 October; merges rest on the local suite.
