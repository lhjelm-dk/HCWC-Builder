# Final audit, 21 September 2026 (Phase 1, read-only)

Scope: the repository at `89497e0` (main, after #63), read against the brief *Final scientific,
code, language and paper review* of 21 Sep 2026. Nothing was modified. The DHI model is audited
as it stands; its architecture is not reopened.

Classification: **P0** mathematical or scientific error · **P1** important correctness or a
misleading interpretation · **P2** UX, maintainability, documentation · **P3** cosmetic.

## 0 · Baseline

918 test functions in 24 files. Full suite on `89497e0` with the anaconda interpreter:
green, exit 0, no failures (§12).

## 1 · Confirmed correct mathematics

Verified by reading the core and by recomputing on the shipped prospect (seed 20260825,
10 000 trials).

| claim (brief §) | where | status |
|---|---|---|
| `P(G)` is the product of the element chances and carries no threshold (A) | `core/pos.accumulation_chance` | correct; `tests/test_pos.py` |
| `F(h) = P(H ≥ h \| G)` in column space; `POS(h) = P(G) × F(h)`; `h_min` enters once through `F(h_min)` (A) | `core/engine.exceedance`, `EngineResult.pos`, `core/pos.chance_curve` | correct; `test_dhi_audit` pins headline = curve at `h_min` |
| `z_HCWC = z_apex + H` per realisation; the well reads the realised `contact_m` (G) | `EngineResult.contact_m`; `results_tab` §4 uses `engine.exceedance(result.contact_m, z, weights)` | correct |
| evidence index → `LR(s) = f(s\|HC)/f(s\|NoHC)` → `P(G\|s)` by the two-state form, capped 10 : 1 per channel (B, C) | `StrengthModel.r_at`, `p_g_given_strength` = `simm_update` | correct |
| geometry likelihood `c·D(h)·Pick + (1−c)·s`, conditional on `G`; `c` never carries `P(G)` or the index (B, D) | `dhi.likelihood`; `likelihood` takes no strength argument | correct; 22 invariants in `test_dhi_audit` |
| one weight array serves the histogram, percentiles, `F_post`, controlling shares, POS (B, I) | `DhiPosterior.weights` read by `results_tab`, `depth_risk_tab`, `report`, `export` | correct since #59 (the sheet and 5.3 were the last readers of the geological `P(G)` under the DHI label) |
| `POS_DHI(h) = P(G\|s) × F_post(h)`, no rescaling (Z) | `dhi.prospect_pos(_curve)` | correct; `test_the_identity_holds_on_the_rendered_tab` |
| absence: `1 − D(h)` within `G`; `(1−d)/(1−f·d)` on `P(G)`; the two absence systems are not silently combined (E) | `dhi.likelihood` (seen=False), `dhi.absence_ratio` | correct; the negative index and the absence observation are separate inputs and the tab does not join them |
| `p_valid` limits: `c → 0` leaves the contact untouched, `c → 1` is the pick alone; the floor `1 − c` keeps every depth in play (D) | `test_dhi` (`p_valid_zero…`, `p_valid_one…`, `depth_channel_can_never_say_more…`) | correct |
| partial conformance as a censored pick, spurious branch 1 (D) | `dhi.likelihood` | correct |
| the outcomes of a seen DHI: shares sum to one, the four on the axis to `P(G\|s)`; the split inside the band is by likelihood branch; the geological `likelihood` is bit-identical to before #63 (J) | `dhi.likelihood_branches`, `dhi.outcome_shares` | correct; seven units |
| percentiles: exceedance convention (P90 shallow), Hazen on the weighted sample, conditional on `h ≥ h_min`, one estimator everywhere a number is reported (H) | `engine.weighted_percentiles`, `DhiPosterior.percentiles`, `report.build` | correct since Phase 3 of the clean-up (`docs/REFACTOR_VALIDATION.md` §9) |
| controlling shares after the update use the posterior weights (I) | `EngineResult.controlling_shares(weights=)`, `controlling_share_by_depth` | correct |
| benchmark comparison is beside, never joined; the optional weight is a weighted quantile average (M) | `benchmarks.shrink_toward`, `ui/empirical` §"fuse" | correct as arithmetic; naming see §3 |
| censoring: filled-to-spill as right-censored seal capacity (N) | `core/censoring`, `test_censoring` | correct |
| median-apex depth axis versus the exact depth-space exceedance (G) | `pos.depth_axis` vs `engine.exceedance(contact_m, z)` | on the shipped prospect the apex spans 3.5 m (P10–P90 2 049.4–2 050.5) and the largest gap between the displayed and the exact curve is 0.002 (geological) and 0.004 (posterior); a display convention here, not an error, but see P1-3 |

The article's "realisation 64" (apex 2 050 m, spill 348, charge 263, capillary 150, leak 146,
continuity 184, fault geometry 265, absent draws 247 / 139 / 261, contact 2 196 m, controller
fault leakage 1) reproduces exactly at the current seed. It is hand-typed, not stale.

## 2 · Genuine bugs

No P0 was found. The mathematics of §1 holds end to end.

| id | class | finding | where |
|---|---|---|---|
| P1-1 | P1 | `ReservoirEffectiveness` with `full_to_m` finite and `none_below_m = inf` returns 1 everywhere through the dead expression `np.where(z <= full_to, 1.0, 1.0)`: the input "fully effective to 2 200 m, never fails" silently means "no decline". With `full_to_m = inf` and `none_below_m` finite the constructor raises, but the message reads "cannot stop being effective (2300 m) above the depth to which it is fully effective (inf m)", which describes the wrong thing. Neither combination is reachable from the tab today (both fields are typed together), so the harm is in the API, not the app. | `core/decompose.py:66–86` |
| P1-2 | P1 | `Decomposition.apex_contribution` is `max\|residual_depth\| − max\|residual_column\|`, the difference between two maxima taken at different depths, and 5.3.3 labels it "Attributable to the apex". A difference of maxima is not an attribution: the two residual curves peak at different depths and the number can be negative, or small while the apex effect at one depth is large. The identity itself (`∏ P_e = P(contact > z)` exact in column space, apex-dependent in depth space) is right; the third metric is not. | `core/decompose.py:120–128`, `ui/depth_risk_tab.py` §3 |
| P1-3 | P1 | Every chance-against-depth figure (4.1.3a / 5.2.3a, 4.2 / 5.3 element curves, 5.1.5a, the overlay's `pos_curve`, the walkthrough) puts `F(h)` on a depth axis by adding the median apex (`pos.depth_axis`), while the well reading on the same tab uses the exact `P(z_HCWC ≥ z \| G)` from the realised contacts. On the shipped prospect the two agree to 0.004 because the apex is pinned to ±2 m; on a prospect with real depth-conversion uncertainty a curve that says 0.60 at 2 230 m and a well reading that says 0.55 at 2 230 m will sit on the same tab. The exact depth-space exceedance exists (`engine.exceedance(contact_m, z, weights)`, used by `decompose.direct_depth` and the well) but has no named home in `core/pos` and the figures do not call it. | `core/pos.depth_axis`; callers in `results_tab.py:715, 1101–1107`, `dhi_tab.py` overlay, `dhi_walkthrough.py:210`, `depth_risk_tab.py` §2 |

## 3 · Scientific and documentation inconsistencies

| id | class | finding | where |
|---|---|---|---|
| P1-4 | P1 | Table 5.1.4c carries a column "A well entering there finds" with phrases such as "hydrocarbons whenever they are present" that assume an entry depth and a criterion the table does not have. The outcome shares are about the posterior contact against the DHI band; the well belongs on 5.2.4 (brief J). | `ui/dhi_tab.py` §4 (`_rows`), `docs/THEORY.md` 8.1.6 table, last column |
| P1-5 | P1 | `r_dhi` is shown in the trust panel as "the evidence is worth R = …" with no definition, and the property's definition differs between a seen anomaly (E-POS's tall-against-short column ratio inside `G`) and an absent one (against the barren world). Neither is `LR(s)`; the panel's wording invites reading it as the evidence ratio (brief K). | `core/trust.py:333`, `core/dhi.py:548–590` |
| P1-6 | P1 | "success" is used for four different events in user-facing text: the accumulation (`G`), meeting the assessment minimum ("success cases only" in 5.2 / 6.0 / the report, "successful realisations"), the well finding hydrocarbons ("chance of success is the contact distribution read at that depth", 5.2), and the database outcome (5.1.3, "a chance of success from the seismic alone"). Brief A asks for one meaning per place; #55 fixed the DHI tab and the theory note, the rest remain (13 strings). | `ui/results_tab.py`, `ui/empirical.py`, `io/report.py:116, 182`, `ui/dhi_tab.py` (5.1.3 caption) |
| P1-7 | P1 | The reference distributions `f(s\|HC)`, `f(s\|NoHC)` are called "two elicited populations" in the article (l. 139) and "elicited (defaults)" in `docs/ASSUMPTIONS.md`; the tab calls them reference distributions. Brief C: they are reference/empirical evidence distributions, not elicited curves. | `paper/ARTICLE.md:139`, `docs/ASSUMPTIONS.md` (DHI evidence index table, row 2) |
| P1-8 | P1 | 8.1.5 says "The logistic form is a modelling choice: a Class III sand can become less visible when very thick", which reads as if the logistic represents that non-monotone behaviour; it cannot (monotone with a ceiling). 5.1.3b's caption calls the function "a modelling choice, exposed rather than hard-coded" (brief F). | `docs/THEORY.md:266–267`, `ui/dhi_tab.py:1047` |
| P1-9 | P1 | The benchmark weight on tab 6 is presented as "Weight on the benchmark" with a "fuse" key and "+ benchmark" curve label; the arithmetic is a weighted quantile average (`shrink_toward`). Nothing calls it Bayesian, but "fuse" implies more than a blend (brief M). | `ui/empirical.py:1044–1092`, `core/benchmarks.shrink_toward` |
| P1-10 | P1 | The paper scenario is not the app's opening state: the article and post use `h_min` 120 m and evidence index +20 (LR 2.62, `P(G\|s)` 0.64, POS 0.64); the app opens at `h_min` 5 m and index +5 (`P(G\|s)` 0.47). Both are legitimate, but the article says "the worked prospect" without stating the index, and no script prints the article's numbers from the code (brief P, AA). | `scripts/post_images.py:69–71` (the only place the paper state is set), `docs/BASELINE.md` §DHI, `paper/ARTICLE.md:152` |
| P2-1 | P2 | `core/dhi.py`'s module docstring opens with "POS is not a number, it is a reading… `F(z_entry − apex)`" and a history of the 14 Sep correction (what was wrong before, the 17 m shift, the scenario-switch debate). The chain it then states is right; the framing predates the `P(G) × F(h)` architecture and the module reads as a changelog (brief X.1, W). | `core/dhi.py:1–60` |
| P2-2 | P2 | `docs/THEORY.md` has eight sections (8.1.1–8.1.8); the brief asks for eleven (overview; P(G); competing limits; column height, HCWC and POS; correlation and dependence; DHI index; DHI geometry; combined posterior; benchmarks and censoring; validation; references). Correlation is inside 8.1.2, POS inside 8.1.3, references are 8.3. 8 850 words; the tone has residues ("an honest single-channel LR", "one nobody can", "which is why…", dated attributions in prose). | `docs/THEORY.md` |
| P2-3 | P2 | The dependency floors disagree: `requirements.txt` says `streamlit>=1.56` and declares `kaleido>=1.0`; `pyproject.toml` says `streamlit>=1.40` and omits kaleido. Neither states which is canonical (brief X.10). | `requirements.txt`, `pyproject.toml:12–19` |
| P2-4 | P2 | `reference/article/` (article.md, post.md, six PNGs) is gitignored, present on disk, and 179 / 59 lines of it do not appear in the canonical `paper/` files. Some of those are the earlier figure captions and the cover-image line; it has not been compared line by line (brief X.12). | `reference/article/`, `.gitignore:48` |
| P2-5 | P2 | `paper/ARTICLE_LONG_2026-09.md` (10 114 words) is referenced by name in tab 8.2's caption but not loaded; correct behaviour, worth one sentence in `paper/README` or the manifest so the intent is recorded (brief X.13). | `ui/theory.py:194` |
| P2-6 | P2 | `hcwc/plotting/paper/` holds only the manifest writer; the article's figures are app exports rasterised through AppTest (`scripts/post_images.py`). There are no purpose-built paper figures (brief S). | `hcwc/plotting/paper/`, `scripts/post_images.py` |
| P3-1 | P3 | `paper/figures/MANIFEST.md` carries the pre-#63 caption for Figure 5 ("P(G \| amplitude)", "picked contact"); regenerated by `post_images.py`. | `paper/figures/MANIFEST.md:27` |

## 4 · UI wording

| id | class | finding |
|---|---|---|
| P1-4, P1-6, P1-8 | | see §3 |
| P2-7 | P2 | Section 5.1.5's two other metrics still read "P(column ≥ h \| G, pick)" beside "P(G \| s)"; consistent would be "… \| G, geometry". |
| P2-8 | P2 | 5.3.2's caption on the DHI basis now says the element curves "carry the same two updates"; 5.3.4's caption and 8.1.6 say the spread "attributes nothing". Both are true; one sentence tying them ("the index update is spread by the allocation rule; it attributes nothing") should appear once, on 5.3.2. |
| P2-9 | P2 | Widget help strings on 5.1.1–5.1.3 average four sentences; several restate the caption beneath the figure (brief 5). |
| P3-2 | P3 | The trust panel's ESS line reads "Effective sample size 4 872 of 10 000 realisations (49 %)"; fine. The post says "leaves 4 872 of the 10 000 realisations doing the work" (brief P wording). |

## 5 · AI-like and repetitive text

Counts in user-facing strings (tab text, captions, help, theory, paper):

| phrase or pattern | app strings | THEORY.md | ARTICLE.md | LINKEDIN_POST.md |
|---|---:|---:|---:|---:|
| "honest" | 4 | 1 | 1 | 1 |
| "nobody" / "nobody chose" | 0 | 1 | 1 (heading "The distribution nobody chose") | 1 |
| "the point is" | 0 | 0 | 1 | 1 |
| "receipts" | 0 | 0 | 0 | 1 |
| "Everything downstream is these two meeting" | 0 | 0 | 0 | 1 |
| "surprisingly sophisticated" | 0 | 0 | 1 | 0 |
| "magic switch" | 0 | 0 | 0 | 0 |

Production-code comments naming "Lars" with a date: 96 across 23 files (`dhi_tab.py` 12,
`empirical.py` 11, `results_tab.py` 11, `depth_risk_tab.py` 7, `theme.py` 7). These are the
development history the brief (W) wants in git and `docs/`, not in the source. Docstrings that
narrate abandoned approaches: `core/dhi.py` module header, `DhiPosterior.r_dhi`,
`dhi.likelihood` ("What this replaced, and why"), `dhi_tab._resample`, `core/dhi_comparison.py`.

Repetition: the sentence "the chance and the contact distribution are read off the same
weighted realisations" appears on 5.1.4, 5.1.5, 5.3.2 and in 8.1.6; "P(G) is the element chance
from tab 2.0" on 4.1.3, 4.1.4, 5.2.3, 5.2.4, 7.4 and the sheet. Once each, plus "Method: see
8.1.x", is the brief's target.

## 6 · Article and post

| id | class | finding |
|---|---|---|
| P1-11 | P1 | The controlling-share table lists six mechanisms summing to 95 % without saying so (brief Q). |
| P1-12 | P1 | "rests on an effective 4 871 of the 10 000 realisations" — the baseline value is 4 872.3, and the wording is the one brief P asks to replace with "effective sample size". The post has "4 872 … doing the work". |
| P1-7 | | "two elicited populations", see §3. |
| P2-10 | P2 | Length: ARTICLE.md 2 336 words against 1 400–1 700; LINKEDIN_POST.md 944 words (with its development notes) against 250–350. |
| P2-11 | P2 | The hand-typed "One realisation, step by step" section (l. 71–95) is correct today (§1) and will be wrong the first time a default moves. Brief O: delete, or generate. |
| P2-12 | P2 | Beha, Christensen & Young (2012) is cited in the article (l. 44) as the precedent; the heading "The distribution nobody chose" and "What this is" still read as a novelty claim. |
| P2-13 | P2 | Flagged phrases (§5): one heading, "surprisingly sophisticated" (l. 21), "the honest number" (l. 154), "The point is" (l. 204); the post carries all five. |
| P2-14 | P2 | The article's structure follows the app's tab order rather than the ten-point story of brief O; the censoring section ("A reality check, not a score") is proportionate already. |

## 7 · Stale numerical content

| item | in the text | from the code | status |
|---|---|---|---|
| ESS | 4 871 (article), 4 872 (post) | 4 872.3 | article off by rounding |
| DHI case | 40 → 64 %, 130 → 99 m | index 20: P(G\|s) 0.6436, POS 0.6394; spreads 130.3 / 99.8 m (`docs/BASELINE.md`) | agrees; the index is not stated in the article |
| prior percentiles | 2 191 / 2 246 / 2 322 | 2 191.3 / 2 245.9 / 2 321.6 | agrees |
| controlling shares | 32 / 23 / 16 / 12 / 9 / 3 % | `docs/BASELINE.md` | agrees; sum 95 % unlabelled |
| realisation 64 | as typed | reproduces | agrees; fragile |
| MANIFEST.md Figure 5 caption | pre-#63 wording | — | stale text, not numbers |

`tests/test_app_renders.py` already checks that the article's headline numbers agree with the
app; the ESS rounding passes because the test compares to 0 decimals.

## 8 · Plots

| id | class | finding |
|---|---|---|
| P1-3 | | depth axes by median apex, see §2. |
| P2-6 | | no purpose-built paper figures, see §3. |
| P2-15 | P2 | Axis labels: the column-space figures say "column height (m)" or "Column (m)" in four spellings; depth axes say "Depth (m TVDSS)" / "Contact depth (m TVDSS)" / "m TVDSS". Brief G asks for `Hydrocarbon column height h (m)`, `HCWC depth z (m TVDSS)`, `Well entry depth z_well (m TVDSS)`. |
| P2-16 | P2 | `h_min` is drawn on depth axes as "assessment minimum" at `apex_med + h_min` (4.1.3a, 5.1.4a, 5.2.3a, the report's SVG) without saying it is the median-apex equivalent (brief G). |
| P2-17 | P2 | The article's Figure 1 is the app's 4.1.2 limit stack, Figure 2 the controlling-by-depth bars, Figure 4 the 5.1.4a histogram, Figure 5 the 5.1.5a chance curves: each answers its question, but they carry app legends, chip colours and tab captions. Brief S wants five figures drawn for the page: competing limits with the resulting minimum; the controlling mechanism with its share by depth; the DHI update with the indication and the prior still visible; POS against depth on the exact depth-space exceedance with the well and `h_min`; an optional empirical check with the censoring inset. |
| P3-3 | P3 | Captions in `paper/figures/MANIFEST.md` are the app captions verbatim (up to eight sentences with "Method: see"); brief T wants two to four sentences and one-sentence alt text. |

## 9 · Repository clean-up

| id | class | finding |
|---|---|---|
| ok | | no `__pycache__` is tracked (0 files); `archive/` holds no caches. |
| P2-3 | | dependency floors and kaleido, see §3. |
| P2-4 | | `reference/article/` legacy copies, see §3. |
| P2-18 | P2 | `hcwc/plotting/app/` holds two files and the tabs still draw the histogram-plus-exceedance panel in three places and the controller-by-depth bars in three (`docs/REFACTOR_VALIDATION.md` §11); candidates for `plotting/app/` when the figures are touched for P1-3 and P2-15. |
| P2-19 | P2 | `scripts/paper_figures.py`, `post_images.py`, `workflow_figure.py` each set the paper scenario in their own way (`from_the_app()`, session-state keys, none). One `scripts/paper_facts.py` with the scenario as data and the numbers as output (brief AA) would be the single source; the figure scripts import it. |
| P2-20 | P2 | Two resamplers with two seeds (`dhi.posterior_columns` 20260904, `dhi_tab._resample` 20260827, `dhi.posterior_indices` 20260904); a technical-debt item already on record. Unifying changes the export's draws by resampling noise only; needs its own approval. |

## 10 · Single source of truth (brief Y)

| concept | canonical | duplicates found |
|---|---|---|
| `P(G)` | `pos.accumulation_chance` | none |
| `F(h)` | `engine.exceedance` | none |
| `POS(h)` | `pos.chance_curve`, `dhi.prospect_pos_curve` | none |
| contact depth | `EngineResult.contact_m` | none |
| DHI LR | `StrengthModel.r_at` | none |
| index update | `dhi.p_g_given_strength` | none |
| geometry update | `dhi.likelihood`, `dhi.update` | none |
| posterior HCWC | `DhiPosterior.weights` + `percentiles` | none |
| controlling mechanism | `EngineResult.controlling_shares`, `engine.controlling_share_by_depth` | none |
| percentiles | `engine.weighted_percentiles` | `np.percentile` for axis ranges only (by decision) |
| assessment minimum | `LimitSet.min_column_m`, `EngineResult.above_minimum` | none |
| exact depth-space exceedance | `engine.exceedance(contact_m, z, w)` called ad hoc in four places | needs a name in `core/pos` (P1-3) |
| the index update spread over elements | `decompose.element_pos_given_index` | none |

## 11 · Proposed implementation order

Phase 2 — P0/P1 (one PR each unless trivial):
1. P1-3: `pos.depth_exceedance(result, z, weights)`; every chance-against-depth figure and the overlay's `pos_curve` / `prior_curve` read it; `h_min` on depth axes labelled "assessment minimum (median-apex equivalent)"; axis labels per brief G; tests that the curve at the well depth equals the well reading, and that a run with a wide apex shows the difference.
2. P1-4: Table 5.1.4c and the 8.1.6 table lose the well column; the well's interval stays on 5.2.4.
3. P1-1, P1-2: `ReservoirEffectiveness` validation and messages; `apex_contribution` replaced by the two residual maxima side by side with the sentence that the difference is the apex's effect only where the peaks coincide, or dropped from 5.3.3.
4. P1-5: `r_dhi` labelled "geometry discrimination ratio" with the seen / absent definition shown; trust-panel line rewritten.
5. P1-6, P1-7, P1-8, P1-9: wording — "success" to one meaning per place; reference distributions never "elicited"; detection "a simplified detectability model; the logistic parameters are exposed as modelling assumptions", Class III sentence made a limitation; "benchmark blend".
6. P1-10, P1-11, P1-12: `scripts/paper_facts.py` (scenario as data: seed, trials, `h_min`, index, σ, c, well depth; prints every number the article uses); the article's six-row table labelled and totalled; ESS wording.

Phase 3 — repository: P2-3 (one canonical dependency list; kaleido declared), P2-4 (line-by-line comparison of `reference/article/`, unique content into `archive/superseded_notes/`, then remove), P2-5, P2-19 (figure scripts import `paper_facts`), P2-18 where P1-3 touches the figures, P2-20 recorded and left.

Phase 4 — text: P2-1 (`core/dhi.py` header rewritten as the current chain), the 96 dated comments (kept where they explain a calculation, moved to `docs/reviews/DEVELOPMENT_HISTORY.md` otherwise), P2-2 (THEORY.md to the eleven sections, rewritten as definition / equation / interpretation / assumptions / limitation / reference; 8.3 becomes 8.1.11), P2-7, P2-8, P2-9, §5 repetition.

Phase 5 — paper: P2-6 / P2-17 (five figures in `hcwc/plotting/paper/`, drawn from `paper_facts`), P2-10 to P2-14 (article to 1 400–1 700 words on the ten-point story; the realisation section generated or removed; post to 250–350 words), P3-3, P3-1.

Phase 6 — `docs/VALIDATION.md` and `docs/BASELINE.md` updated; a final full-suite record.

## 12 · Baseline run

`python -m pytest -q` on `89497e0`, anaconda interpreter, 21 Sep 2026: exit 0, no failures,
918 test functions (about 1 070 parametrised cases), render tests included. This is the
baseline every later phase is measured against.
