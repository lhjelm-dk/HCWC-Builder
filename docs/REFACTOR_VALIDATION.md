# Refactor validation (Phase 8, 18–20 September 2026)

The clean-up ran on branch `refactor-01-inventory` in eight commits, one per phase, each
tested before the next. Nothing user-facing was removed; one numerical change was made, with
approval, and is quantified below.

## 1 · Files before and after

141 tracked files before, 164 after. New: `archive/` (four READMEs), `hcwc/core/pos.py`,
`hcwc/core/defaults.py`, `hcwc/core/dhi_comparison.py`, `hcwc/exhibits.py`, `hcwc/paths.py`,
`hcwc/plotting/` (five files), `hcwc/ui/concept.py`, `export.py`, `theory.py`, `markdown.py`,
`tests/test_pos.py`, `tests/test_defaults.py`, `paper/figures/MANIFEST.md`, and the documents
`docs/REPO_AUDIT.md`, `ARCHITECTURE_CURRENT.md`, `BASELINE.md`, `ASSUMPTIONS.md`,
`VALIDATION.md`, `ARCHITECTURE_FINAL.md`, this file.

## 2 · Files moved

| from | to |
|---|---|
| `docs/superseded/*.md` (5 + README) | `archive/superseded_notes/` |
| `docs/superseded/*.png` (6), `paper_figures_mpl_2026-09-17.py` | `archive/old_figures/` |
| `docs/DHI_alignment.md`, `EXPLANATION_MAP_2026-09-16.md`, `IFT_CHECK_2026-09-15.md` | `archive/development_notes/` |
| `reference/concept_full.png` (unreferenced) | `archive/old_figures/` |
| `reference/edmundson_2021_*.csv`, `bias_curve.json` | `reference/empirical/` |
| `reference/area_depth.csv`, `example_prospect*.hcwc.json`, `concept.png` | `reference/defaults/` |
| `docs/ARTICLE.md`, `ARTICLE_LONG_2026-09.md`, `LINKEDIN_POST.md` | `paper/` |
| `docs/figures/*.png`, `prospect.json` | `paper/figures/` (the two SVGs the app renders stay in `docs/figures/`) |
| `docs/post/*.png` | `paper/post/` |
| `docs/*_REVIEW.md` (5) | `docs/reviews/` |
| `hcwc/ui/limit_stack.py` | `hcwc/plotting/app/limit_stack.py` |

Every path that pointed at a moved file was repointed (docstrings, tests, scripts, documents);
`grep` for the old paths finds nothing outside `archive/` and `_private/`.

## 3 · Files archived

The three groups above under `archive/`, each directory with a README saying what it holds,
why, whether it can be ignored and what supersedes it. Nothing under `archive/` is imported;
one test checks the superseded notes still exist there and are not back on screen.

## 4 · Files deleted, with justification

`hcwc/dhi/__init__.py` and `hcwc/viz/__init__.py`: two-line empty packages nothing imported,
no content. Recorded in `docs/REPO_AUDIT.md`.

## 5 · Modules created

`hcwc/core/pos.py` (P(G), the chance curve, the depth axis) · `hcwc/core/defaults.py` (the
scientific defaults with unit, meaning, provenance and range; a REGISTER) ·
`hcwc/core/dhi_comparison.py` (scenario switch, CombinedUpdate, the three combinations) ·
`hcwc/exhibits.py` (registry keys, sort key) · `hcwc/paths.py` · `hcwc/plotting/app/colours.py`,
`limit_stack.py` · `hcwc/plotting/paper/manifest.py` · `hcwc/ui/concept.py`, `export.py`,
`theory.py`, `markdown.py`.

## 6 · Modules merged

None. `app.py` was split, not merged (800 → 182 lines).

## 7 · Scientific functions consolidated

| concept | before | after |
|---|---|---|
| P(G) = ∏ element chances | written out in 8 places | `pos.accumulation_chance`, called by all |
| F(h) exceedance | `engine.exceedance` + a broadcast in `ui/sources.py` | `engine.exceedance` |
| exceedance percentiles | `engine.weighted_percentiles` (Hazen) and `np.percentile` (linear) in 25 reporting sites | `engine.weighted_percentiles` everywhere a number is reported; `np.percentile` only for axis ranges and a widget default |
| limit colours | `results_tab.limit_colours` + a private copy in `limit_stack` | `plotting.app.colours.limit_colours` |
| registry keys / sort key | `ui/numbering` (imported by `io/report`) | `hcwc.exhibits`, re-exported by `ui/numbering` |
| the comparison constructions | inside `core/dhi.py` | `core/dhi_comparison.py`; `core/dhi.py` holds the canonical chain only |

Not consolidated, by decision: the two resamplers (`dhi.posterior_columns`, seed 20260904;
`dhi_tab._resample`, seed 20260827) — unifying the seed would change the export's draws;
left as recorded technical debt (§11).

## 8 · Tests added or changed

Added: `tests/test_pos.py` (5), `tests/test_defaults.py` (6). Changed: three tests that pinned
`np.percentile` now pin `weighted_percentiles` and check agreement with numpy to 1e-3/1e-4
(`test_limit_block`, `test_geox` ×2); tests that read `app.py`'s source for tabs 7 and 8 read
`hcwc/ui/export.py` and `theory.py`; the widget-key scan now sees tabs 1, 7 and 8 and excuses
their six one-shot keys; the comparison tests import `dhi_comparison`; the superseded-notes and
reviews tests look in `archive/` and `docs/reviews/`; the maths-across-a-line-break check
covers `paper/*.md`; `THEORY_ORDER` pins the eight sections. No test was deleted.

## 9 · Baseline numerical comparison

All quantities in `docs/BASELINE.md` are reproduced exactly except the reported percentiles
that read the linear estimator before commit `03b`; the approved change moves them by the last
digit:

| quantity (shipped prospect, seed 20260825, n 10 000) | before (`np.percentile`, linear) | after (`weighted_percentiles`, Hazen) |
|---|---:|---:|
| limit Charge P90 / P10 (m) | 203.33 / 336.11 | 203.27 / 336.12 |
| limit Closure / spill point P10 | 345.37 | 345.38 |
| limit Fault geometry 1 P90 | 223.10 | 223.09 |
| limit Fault leakage 1 P90 | 137.83 | 137.82 |
| limit Top seal (capillary) P10 | 369.37 | 369.42 |
| limit Top seal (continuity) P90 / P10 | 146.81 / 274.84 | 146.76 / 274.86 |
| limit Preservation / tilt P90 / P10 | 198.53 / 321.09 | 198.52 / 321.15 |
| GeoX export P100 / P90 / P50 / P10 / P0 (truncated) | 2174.06 / 2191.34 / 2245.91 / 2321.55 / 2384.04 | 2174.02 / 2191.34 / 2245.91 / 2321.56 / 2384.09 |
| calibration quantile pairs, built, 5 points | 117.86 / 152.01 / 194.74 / 236.62 / 328.48 | 117.64 / 152.00 / 194.74 / 236.63 / 328.57 |

The contact percentiles the tabs headline (Hazen already) did not move: P90 / P50 / P10
2 191.3 / 2 245.9 / 2 321.6 m before and after. P(G), F(h_min), POS, the DHI case, the shares,
the well readings and the Beha reproduction are unchanged.

Regenerating the paper figures changed two files, `fig3_chance_against_depth.png` and
`post/06_chance_against_depth.png`, by the legend wording "h ≥ h_min" of #55 (18 Sep), not by
the refactor; every other export is byte-identical.

## 10 · Known pre-existing failures

None. The suite was green before Phase 1 and after every commit.

## 11 · Remaining technical debt

- Two resamplers with two seeds (§7); a seed change needs its own approval.
- Module names keep their `_tab` suffixes (`prospect_tab`, `results_tab`, `dhi_tab`,
  `empirical`): renaming would touch every test for no behavioural gain; a later PR if wanted.
- The histogram-plus-exceedance panel is built in three places (4.1.1a, 5.1.4a, the report)
  and the controller-by-depth bars in three; the data behind them are one function each, the
  drawing is not. Candidates for `hcwc/plotting/app/` when a figure changes next.
- `ui/dhi_tab.py` (1 760 lines), `ui/empirical.py` (1 280) and `ui/results_tab.py` (1 200) are
  long; each is one tab and reads top to bottom, but a section-per-function split would help.
- `hcwc/ui/results_tab.py` and `depth_risk_tab.py` still share a `render` for tabs 4 and 5 by
  design; the colour import between them is gone.
- The strength curves' origin beyond E-POS is not documented in the repository (R3 of the audit).
- CI cannot run until the Actions allowance resets (1 October); merges rest on the local suite.

## 12 · User-facing functionality

Every tab, control, figure, table, export and document available before the clean-up is
available after it, at the same place and number: verified by the `render` suite (every tab
renders, every exhibit registered and uniquely numbered, the documents on tab 8, the article's
numbers agree with the app) and by the widget-key scan (no key lost or added). The one visible
difference is the last digit of the percentiles listed in §9.
