# Final validation report (Phase 6, 21 September 2026)

The closing record of the final review (`docs/FINAL_AUDIT_2026-09.md`): what changed in each
phase, what was tested, and what the numbers are afterwards. The baseline is the full suite on
`89497e0` before Phase 2 (exit 0, no failures, 918 test functions).

## 1 · What changed, by phase

| phase | PRs | change | numerical effect |
|---|---|---|---|
| 2, P1-3 | #64 | every chance-against-depth figure reads `pos.depth_exceedance` (exact on the realised contacts); h_min on a depth axis labelled as the median-apex equivalent; tab 6's DHI curve is F_post(h) from the posterior | shipped prospect: ≤ 0.004 on any curve (apex spread 3.5 m); tab 6's DHI curve no longer normalised to one at h_min |
| 2, P1-4 | #65 | Table 5.1.4c and the 8.1.6 table lose the well column | none |
| 2, P1-1, P1-2, P1-5 | #66 | `ReservoirEffectiveness` refuses one bound without the other; `apex_effect` replaces the difference of maxima; `r_dhi` shown with its definition | 5.3.3's third metric is a different quantity (largest pointwise apex effect); no other number moves |
| 2, P1-6 to P1-9 | #67 | wording: success, elicited, detectability model, benchmark blend | none |
| 2, P1-10 to P1-12 | #68 | `scripts/paper_facts.py`; article shares and ESS corrected | article: seal continuity 16 → 15 %, fault geometry 12 → 13 %, preservation 5 % added, ESS 4 871 → 4 872 |
| 3 | #69 | one dependency list; first article draft archived; figure scripts on `paper_facts` | none |
| 4 | this PR | THEORY.md rewritten as eleven sections; 210 section references remapped; `core/dhi.py` header; dated attributions out of the source | none |
| 5 | this PR | five purpose-built paper figures; article 2 336 → ~1 700 words; post 944 → 320 words | none (figures drawn from the same chain) |

No mathematical behaviour changed in any phase. The two structural changes (P1-1, P1-2) are on
inputs the tab cannot produce and on a diagnostic metric respectively.

## 2 · Tests

927 test functions after the review (918 before). Added:

| concept (brief Z) | test |
|---|---|
| depth-space exceedance equals the exceedance of the realised contacts; equals the column curve when the apex is pinned; differs by > 0.02 with a wide apex; the well reads the exact one | `tests/test_pos.py::TestDepthSpace` |
| reservoir effectiveness: one bound refused, coincident depths a step | `tests/test_decompose.py::TestReservoirEffectiveness` |
| apex effect: zero for a certain apex, grows with apex uncertainty | `tests/test_decompose.py` (carried over) |
| the article and the post quote `paper_facts` | `tests/test_app_renders.py::test_the_article_and_the_post_quote_paper_facts` |
| pyproject mirrors requirements | `tests/test_ui_imports.py::test_pyproject_mirrors_requirements` |
| the outcome table relates the posterior contact to the DHI, no well column | `tests/test_app_renders.py::test_the_outcomes_are_on_tab_5_1_4…` |
| the eleven theory sections render in order; the bibliography under 8.1.11; the walkthrough under 8.1.8 and the worked example under 8.1.9 | `tests/test_app_renders.py::TestTheArgumentsLiveInDocuments` |

The invariants of brief Z that were already pinned and still pass: competing-limit minimum,
inactive limit, charge, seal, spill, correlation, apex/contact conversion, the percentile
convention, POS = P(G) × F(h_min); for the DHI, neutral / positive / negative index, the index
only changes P(G), the geometry only changes HCWC | G, no double counting, absence, the p_valid
limits, the spurious density, partial conformance, posterior consistency, POS consistency at
h_min (headline = curve at h_min, no rescaling), controlling shares on the posterior weights.

## 3 · Numbers after the review

`python scripts/paper_facts.py` at the paper scenario (seed 20260825, 10 000 trials, h_min
120 m, evidence index +20, pick 2 250 ± 10 m, c 0.36, well 2 230 m):

| quantity | value |
|---|---|
| P(G) | 0.4082 |
| F(h_min), POS geological | 0.9874, 0.4031 |
| LR(s), P(G \| s) | 2.617, 0.6436 |
| F_post(h_min), POS given the DHI | 0.9936, 0.6394 |
| prior HCWC P90 / P50 / P10 | 2 191.3 / 2 245.9 / 2 321.6 m |
| posterior HCWC P90 / P50 / P10 | 2 198.2 / 2 249.7 / 2 297.6 m |
| P90–P10 spread, prior / posterior | 130.2 / 99.5 m |
| effective sample size | 4 872.3 |
| P(well) at 2 230 m, geological / given the DHI | 0.2335 / 0.4969 |
| controlling shares, h ≥ h_min | capillary 31.7, leakage 23.3, continuity 15.3, fault geometry 12.6, charge 9.3, preservation 4.5, spill 3.2 % |

Every value agrees with `docs/BASELINE.md` (18 Sep 2026) to the digits it prints.

## 4 · Full-suite record

`python -m pytest -q` with the anaconda interpreter on the Phase 4–6 branch (Phases 2 and 3
merged beneath it), 21 Sep 2026: exit 0, no failures, 927 test functions, about 1076 cases,
render tests included. Every phase's PR was merged on its own green run of the same suite.
