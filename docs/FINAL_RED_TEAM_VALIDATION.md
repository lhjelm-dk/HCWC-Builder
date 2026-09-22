# Final red-team validation (Phase 6, 22 September 2026)

Closes `docs/RED_TEAM_REVIEW.md`. Baseline: `385717a`, full suite 1 076 passed, no warnings,
12 min 31 s (`docs/NUMERICAL_AUDIT.md` §1).

## 1 · Changed scientific assumptions

| item | before | after | numerical effect |
|---|---|---|---|
| mechanical seal, negative headroom | clipped to a 0 m column and entered the competition as a contact at the apex when the stress and pore-pressure ranges partly overlapped | refused: `MechanicalSealInputs` rejects any overlap of the two ranges, `mechanical_column_m` rejects a negative result; the message names Retention on tab 2.0 as where the failed-trap chance belongs | none on the shipped defaults (no overlap); an overlapping input is now an error on the tab instead of an apex spike |
| the pore-throat quartic | silent outside void ratios 0.1–1.0 | `UserWarning` naming the value an extrapolation | none (the tab reaches the radius through MICP, not the quartic) |
| detection function | `ceiling / (1 + exp(−x))` | `ceiling · expit(x)` | identical values; no overflow at any column height |
| a run check | — | "Limits act below the crest": a limit whose active draws sit within 5 m of the apex is flagged as a crest failure entered as a limit | a new watch/stop; no number moves |

No other mathematical behaviour changed. `P(G)`, `F(h)`, the likelihood arithmetic, the
factorisation, the percentiles and the outcome shares are as before.

## 2 · Changed statements

| statement | was | is |
|---|---|---|
| the floor (8.1.7, article, 5.1.3, walkthrough, `dhi.likelihood`, `dhi_tab` header) | "the geometry can say at most c / (1 − c) against any contact depth" — false | `L / s ≥ 1 − c` at every depth: no depth is excluded and an attributed contact cannot become certain; the ratio between two depths is `1 + c · D · Pick_max / ((1 − c) · s)` and grows as the pick narrows (≈ 8 on the shipped prospect) |
| `p_valid` (`dhi_tab` header) | "this times the amplitude-updated P(G)" — obsolete and wrong | the contact-attribute judgement; carries no `P(G)` and nothing of the index |
| the Monigle route (5.1.3, `dhi.py`, `defaults.py`, 8.1.7, REFERENCES.md) | "calibrated on 400+ drilled DHI prospects", "their rule gives the shipped c", "calibrated ceiling" | "External reference: DHI score (Monigle et al. 2025)": their column-height weighting practice on their score, an empirical relationship in their database, not a calibration of c on this tool's inputs; the 0.95 is the ceiling both they and Hood use in practice; the default score exists only so the route opens in agreement |
| `P(active)` on every limit (tab 3.0) | "the chance the mechanism is present at all" | "the chance this mechanism exists below the crest, given the accumulation; a mechanism that fails the element at the crest belongs in the element chance on tab 2.0" |
| 8.1.2 | no statement | the element chances are multiplied as conditionally independent inputs; dependence between their presence probabilities is not modelled; a table mapping each element chance to the limits under it and the double count to avoid |
| 8.1.7 | prose | a table classing each term of `L(D \| h, G)` as convention or judgement, with what a reviewer can challenge; "`c` is held constant with column height"; the DHI's extent is not the assessment minimum (also 5.1.1) |
| 8.1.8 | "each is a Bayesian update" | "… exact conditional on an observation model that is itself the assumption" |
| 8.1.3, article | "two or three limits set the answer", "that table is the sensitivity analysis" | controlling-mechanism statistics, not a sensitivity; "a few mechanisms dominate the controlling share in this worked case" |
| 8.1.6 | "a reference relationship" | "a reference evidence relationship, not a calibration for any basin and not a measured quantity; nothing in the repository reproduces it from data" |
| 8.1.9, article | "the one openly redistributable dataset"; "it is not uninformative" unscoped | "the open dataset used here"; "for the seal-capacity interpretation the observation is right-censored" |
| gas–water tension (`seals.py`, 3.0) | "provenance unknown" | "an empirical default of unrecorded provenance, kept because measured methane–brine tension at reservoir pressure sits on it; a measured value overrides it" |
| the index slider | enabled when the anomaly is absent | disabled, with the reason |
| walkthrough | "really is the contact" | "is in fact the contact" |

## 3 · Tests

| added | file |
|---|---|
| the floor holds, the old cap is exceeded, the true bound holds, discrimination grows as the pick narrows | `tests/test_dhi.py::test_the_floor_bounds_each_depth_but_does_not_cap_discrimination` |
| mechanical seal: shipped defaults do not overlap; partial, total and touching overlap refused; a direct negative call refused; no 0 m column can come out; the three tests that pinned the clip now pin the refusal | `tests/test_seals.py::TestNegativeHeadroomIsRefusedNotClipped` and `TestTheMechanicalColumn` |
| pore-throat fit silent inside its range, warns outside | `tests/test_seals.py::TestThePoreThroatFitWarnsOutsideItsRange` |
| detection function: h50 is half the ceiling; zero and very large columns; no overflow; monotone | `tests/test_dhi.py::TestDetectionFunctionEdges` |
| crest-failure check: the reference prospect passes; a limit at the apex is flagged with the element named; the check is in the review | `tests/test_trust.py::TestCrestFailure` |

Full suite after Phase 2 (`rt-p0`) and after Phases 3–5 (`rt-p1`): see §6.

## 4 · Article numbers

`python scripts/paper_facts.py --json` regenerated on the final state: every value in
`paper/figures/facts.json` is unchanged from `docs/NUMERICAL_AUDIT.md` §2 (the only diff is the
new `burial_m` field). P(G) 0.4082; POS geological 0.4031; P(G | s) 0.6436; POS given the DHI
0.6394; prior 2 191 / 2 246 / 2 322 m; posterior 2 198 / 2 250 / 2 298 m; spreads 130 / 99.5 m;
ESS 4 872; P(well) 0.2335 / 0.4969; shares 32 / 23 / 15 / 13 / 9 / 5 / 3 %. The article and the
post quote these and a render test pins them.

## 5 · Figure provenance

`paper/figures/paper_fig1–5.png` regenerated by `scripts/paper_figures.py` from
`hcwc/plotting/paper/figures.py` at the scenario in `scripts/paper_facts.py` (seed 20260825,
10 000 trials, h_min 120 m, index +20, pick 2 250 ± 10 m, c 0.36, well 2 230 m, burial 2 500 m);
`paper/figures/MANIFEST.md` lists them with source and caption. Figure 4 is on the exact
depth-space exceedance. Nothing in the figures is typed.

## 6 · Full-suite record

`python -m pytest -q` with the anaconda interpreter, 22 Sep 2026: after Phase 2 (`rt-p0`, merged
as #72) exit 0, no failures; after Phases 3–6 (`rt-p1`, rebased on main) exit 0, no failures,
943 test functions (1 076 baseline cases plus the tests of §3), render tests included, no
warnings. Each PR merged on its own green run.
