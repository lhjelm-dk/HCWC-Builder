# Red-team review (Phase 1, read-only, 22 September 2026)

The repository at `385717a` attacked as a skeptical petroleum geoscientist would: where is the
mathematics thinner than the prose, where does the implementation differ from what the UI says,
which assumptions are stronger than the evidence, which statements sound more certain than the
model is. Nothing was modified. The test runs and the reproduced numbers are in
`docs/NUMERICAL_AUDIT.md`; that document is the evidence for every "confirmed" below.

Classes used: **confirmed bug** · **likely bug** · **scientific weakness** · **documentation
mismatch** · **UX problem** · **stylistic** · **acceptable simplification**.

## 1 · The four highest-risk attacks, answered first

### 1.1 P(G) against the limit probabilities — is retention counted twice?

The architecture separates "does an accumulation exist" (`P(G)`, four element chances at the
crest) from "how far can it fill" (limits, each with `P(active)` and a depth or capacity,
conditional on `G`). Whether that separation holds for each element, on the current defaults and
controls:

| element | element chance means (tab 2.0) | limit(s) under it (tab 3.0) mean | conditional on G? | double-count risk |
|---|---|---|---|---|
| Charge | hydrocarbons reached the trap at the crest (0.90) | charge limitation: the volume delivered fills the trap only to a depth; always active | yes, the calculator assumes a charge arrived and asks how much | **low** — but only if the element chance excludes "too little to matter"; the tab does not say so |
| Closure | a closure exists at the crest (1.00) | the spill point (always active); a fault-bounded geometry window `P(active)` 0.5 | yes | **low**; the 1.00 is right because the spill is a limit, and 8.1.2 says so |
| Reservoir | reservoir present at the crest (0.63) | none in the shipped set; a pinch-out limit is available; an effectiveness decline (5.3) scales the chance without moving the contact | yes | **low**; the effectiveness decline and a pinch-out limit could overlap if both were used for one reservoir loss — not documented |
| Retention | "whether the seal holds anything" (0.72) | top-seal capillary capacity (always), base seal, continuity holes `P(active)` 0.5, fault leakage 0.6, preservation 0.2, mechanical failure | yes | **highest** — a "continuity hole present in 50 % of realisations" at a depth the column reaches is a limit; a hole at the crest is retention failure, and the tab does not tell the assessor which the number is; a fault leak at the crest likewise; and an E-POS Retention chance imported from a workflow that already means "the seal holds the full column" double counts with the capillary limit (tab 2.0 warns about this one case only) |

Evidence in code: `core/pos.accumulation_chance` (product), `core/engine.run` (presence draws
independent, `INACTIVE` for absent limits), tab 2.0's info box (Retention sentence). Evidence in
literature: Beha et al. (2012) make the same separation and the same independence of presence.
Status: **scientific weakness (documentation)** — the arithmetic separates them; the semantics of
`P(active)` for retention limits are not stated per limit. Recommended: a "what this probability
means" line on every retention limit ("the chance this mechanism exists *below the crest*; a
mechanism that fails the seal at the crest belongs in Retention on tab 2.0"), the mapping table
above in 8.1.2/8.1.3, and a check that flags a limit whose depth distribution puts substantial
mass at the apex (that is a crest failure entered as a limit). Test: none can prove semantics;
a render test can pin the presence of the per-limit sentence.

### 1.2 The Monigle route to c

What the code does: `c = min(2 × score, 0.95)` from a typed "DHI score (Monigle et al. 2025)",
offered as the third route beside the stated value and the graded attributes, labelled
"calibrated on 400+ drilled DHI prospects" (5.1.3 help, caption, the 0.95 line on Figure 5.1.3a,
`core/defaults.DEFAULT_DHI_SCORE`, `docs/REFERENCES.md`).

What the source says (as transcribed in `docs/reviews/MONIGLE_2025_REVIEW.md` §3): "an empirical
relationship has been established between DHI score and column height weighting (Figure 8).
High DHI scores (>0.50) weight the HCWC at the rated DHI elevation to 95 % of the total trials.
Lower DHI scores weight the HCWC at the DHI elevation relative to the rating outcome (double the
DHI score)", with a figure caption that for nearly all prospects with a score above 50 the HCWC
in the success case was the DHI-evaluated HCWC.

Assessment. The rule *is* about column-height weighting, so the attack "it is a COS calibration
misused as a contact weight" does not land as stated. What does land: (i) the score is their
five-attribute COS-oriented score trained on drilling outcomes, and the tool has no way to place
its own evidence index or its graded attributes on that score, so a user types a number on a
scale the tool cannot check; (ii) "calibrated" overstates "an empirical relationship has been
established" — the paper reports their weighting practice and a look-back that supports it, not
a fitted probability with an uncertainty; (iii) their weight is a *scenario* weight in a
substitution construction (Hood's), and its use as `c` inside a likelihood mixture is this tool's
mapping (event definition F of §37); (iv) the 0.95 ceiling is their practice, shared with Hood
(2019), not a measured maximum. Status: **documentation mismatch** ("calibrated", "their rule
gives the shipped c") and **scientific weakness** (mapping across constructions). Recommended:
keep the route, relabel it "Monigle et al.'s (2025) column-height weighting practice, on their
score; an external reference, not a calibration of c on this tool's inputs"; drop "calibrated"
everywhere it refers to this rule; move the default `DEFAULT_DHI_SCORE = 0.18` out of `defaults`
(it exists only to make the route agree with 0.36) or state that that is all it is. Whether the
route stays canonical is the author's call; the safer default is comparison-only.

### 1.3 The DHI geometry likelihood — the most modelled part

`L(D | h, G) = c · D(h) · Pick(z | z_apex + h) + (1 − c) · s`, with the absent form `1 − D(h)`, the
partial form `c · D(h) · Φ((z_off − z)/σ) + (1 − c)`, and a well factor multiplied in. Each term
classified (brief §12, §37):

| term | what it is | class | weakest sentence a reviewer would pick |
|---|---|---|---|
| `c` | P(the indicated event is the contact \| G, contact attributes) | elicited (stated / graded heuristic / external rule) | "held constant with column height" — a thick column makes a conformable flat event more plausibly its base; not modelled (§13) |
| `D(h)` | logistic in h, ceiling < 1 | modelling convention with elicited parameters (h50 ≈ tuning, width, ceiling) | monotone; cannot weaken with thickness; h50 as "tuning thickness" is a heuristic identification |
| `Pick(z)` | normal / PERT / uniform in depth, σ = pick + depth-conversion error | elicited | the two errors are folded into one σ; depth conversion is spatially correlated with the apex pick and that is not carried |
| `s` | uniform over the declared contact range | modelling convention | "a spurious event is equally likely at any depth" is a choice; a lithology event is more likely where the stratigraphy dips, and the support (apex to deepest contact) is set by the model, so the floor's *height* is a property of the model's own range |
| partial conformance | censored pick, spurious branch = 1 | modelling convention | the branch value 1 is a bound, chosen conservative, not derived |
| absence `1 − D(h)` within G; `(1 − d)/(1 − f d)` on P(G) | modelling convention; `f` elicited, 0.5 by ignorance | "tying the false-positive rate to d" is a convenience for the end behaviour |
| independence of `c`, `D`, `Pick`, `s` | modelling convention | none is coupled to another; the same interpreter grades all of them |
| the well factor | a likelihood for depth evidence with one tie error and a floor | modelling convention, elicited σ and `p_connected` | "independent of the DHI geometry" — the same depth conversion underlies both |
| the two-channel factorisation | modelling decision (8.1.8) | convention | the valid branch carries evidence about G that is assigned to the index channel by fiat |

None of this is hidden in 8.1.7 / 8.1.10 today, but the classes are not labelled term by term
on the tab, and the Theory calls the whole "an exact Bayesian update" (true for the sample,
given the observation model) without the sentence that the observation model is the assumption.
Status: **acceptable simplification**, **documentation mismatch** in emphasis. Recommended: the
table above, in 8.1.7 and as a fold on 5.1.3 ("what in this likelihood is physics, what is
judgement"); one sentence in 8.1.8 that the Bayesian arithmetic is exact conditional on an
observation model that is itself the assumption.

### 1.4 The mechanical seal's zero-metre column

`fracture_headroom_bar` says a negative headroom "is a failed trap, not a short column";
`mechanical_column_m` then clips it to 0 m; `MechanicalSealInputs` refuses only total overlap
of the stress and pressure ranges. A partly overlapping pair (probed: 7.1 % negative draws) puts
those realisations into the competition as a contact at the apex — the spike the engine refuses
for a depth-stated limit, in the engine's own words. Status: **confirmed inconsistency** (code
does what its comment says it must not). Intended semantics: a realisation in which the aquifer
alone satisfies the fracture criterion is a failure of retention, `¬G`, not a 0 m column.
Representing it per realisation inside `F(h)` double counts with Retention on tab 2.0.
Recommended: refuse any overlap (`s_hmin_bar[0] <= pore_pressure_bar[1]`) with a message that
names the failed-trap share and says to carry it as Retention risk; alternatively sample only the
non-negative-headroom region and report the excluded share beside the calculator as "share of
the input range in which the trap fails before any column: enter as Retention risk on tab 2.0".
The first is simpler and cannot double count. Tests: overlap refused; the shipped defaults do not
overlap; a range with a zero-headroom corner does not produce a 0 m spike.

### 1.5 The `c / (1 − c)` statement

False, as shown numerically in `docs/NUMERICAL_AUDIT.md` §3.1 (ratio 8.4 where the text says
0.56; 591 where it says 9). It appears in 8.1.7, the article, the 5.1.3 caption
(`p_valid / (1 − p_valid) : 1 against any contact depth`), the module comment in `ui/dhi_tab.py`,
the docstring of `dhi.likelihood` and the walkthrough. The true statement: the floor bounds every
depth's likelihood from below at `(1 − c)` times the flat alternative, so no depth is excluded
and the posterior share of any prior region cannot fall below `(1 − c) · s / L_max` of its prior
share; the ratio between two depths is `1 + c · D · Pick_max / ((1 − c) · s)` and grows as the
pick sharpens. What `c` controls is that an attributed contact cannot become infinitely certain,
not a universal cap on discrimination. Status: **confirmed bug (documentation)**. Test required:
the ratio between depths exceeds `c / (1 − c)` on the shipped prospect; the floor holds.

## 2 · Stale or wrong scientific documentation (brief §3)

| where | text | status |
|---|---|---|
| `hcwc/core/dhi.py` module docstring | rewritten on 21 Sep (#70): the current chain A / B / C; "F(h_DHI)" and "POS is a reading" are gone | closed |
| `hcwc/core/dhi.py` `likelihood` docstring | "What this replaced, and why" (the 14 Sep form) and the false `p_valid / (1 − p_valid)` sentence | **documentation mismatch** |
| `hcwc/ui/dhi_tab.py:50–61` module comment | "`p_valid` is this times the amplitude-updated `P(G)`" — obsolete since 14 Sep and scientifically wrong; "lets the pick say at most 0.56 : 1" — false | **documentation mismatch** |
| `hcwc/core/dhi.py` `DhiObservation` docstring | the history of `p_valid` before 14 Sep, kept as explanation | acceptable, could be shortened |
| `hcwc/core/dhi.py` `r_dhi` | rewritten (#66) | closed |
| `hcwc/core/dhi.py` `R_SINGLE_CHANNEL` comment | "the strength slider alone moved the prospect chance from 1.4 % to 97.2 %" — history | stylistic |

## 3 · The peer-attack table (brief §36)

| priority | claim / calculation | what a skeptic attacks | evidence in code | evidence in literature | status | recommended action | test required |
|---|---|---|---|---|---|---|---|
| P1 | P(G) = ∏ element chances | conditional independence of charge, closure, reservoir, retention; one seismic interpretation feeds several | `pos.accumulation_chance` | standard practice (Rose; E-POS) — a convention, not a finding | scientific weakness, undocumented | 8.1.2 limitation sentence: "element chances are multiplied as conditionally independent inputs; dependence between their presence probabilities is not modelled"; not the copula's job | render test pins the sentence |
| P1 | P(G) vs limit probabilities | same uncertainty twice (§1.1) | `engine.run`, tab 2.0 info | Beha et al. 2012 | scientific weakness (semantics) | per-limit meaning line; mapping table in 8.1.3; crest-mass check | render test |
| P1 | charge limitation | the calculator's volume is an integral of an area–depth table times a delivered volume; the delivered volume's uncertainty is elicited; "always active" | `core/charge` | Lowry et al. 2005 (chance against column) | acceptable simplification | say that `P(active) = 1` means "the volume is finite", not "charge is certain" | none |
| P1 | capillary seal limitation | `h = (Pc_seal − Pc_res) / (Δρ g)`: same γ and θ in both terms; throat radius from a quartic in void ratio fitted over e 0.1–1.0 (porosity 9–50 %); porosity from Hansen (1996) depth line; independent uniforms inside the calculator | `core/seals` (the quartic has no range check; `depth_from_porosity` checks its own domain) | Aplin & Yang 1998; Hansen 1996; Purcell 1949 | scientific weakness: extrapolation unwarned; gas–water tension line of unknown provenance | enforce or warn on the quartic's range; label the tension line "empirical default, provenance not established" or make it an input (§16); state fluid-phase assumptions once | unit test that out-of-range void ratio warns |
| P0 | mechanical seal | negative headroom clipped to a 0 m column (§1.4) | `seals.mechanical_column_m` | Grant 2020 eq. 7–8 | confirmed inconsistency | refuse overlap; carry as Retention risk | overlap refused; no apex spike |
| P1 | fault leakage / continuity | `P(active)` semantics (crest vs down-dip) | `engine.run` | Beha 2012 | scientific weakness (semantics) | as §1.1 | render test |
| P1 | depth-space conversion | figures shifted F(h) by one apex | `pos.depth_exceedance`, all depth figures (#64) | — | closed | — | `test_pos.TestDepthSpace` (exists) |
| P1 | DHI evidence-index construction | "+5 has no meaning"; the Gaussians from P1/P99 are the shipped defaults with no dataset; who says the two curves cross at 0 | `StrengthModel`, `defaults.EVIDENCE_INDEX_*` | E-POS's construction; no calibration in the repository | acceptable simplification, provided it is labelled | 5.1.2: "reference evidence distributions; the shipped pair is a reference relationship, editable, not a basin calibration; nothing in the repository reproduces it"; never "elicited curves"; axis "density", never "probability" (5.1.2 already says density) | render test on the wording |
| P1 | LR cap 10 : 1 per channel, 50 combined | why 10, why 50 | `R_SINGLE_CHANNEL`, `R_CAP` | Simm & Bacon 2014; Simm 2020; Kjønsberg 2010 (29) | acceptable simplification, sourced | none | exists |
| P1 | DHI contact attribution c | constant in h; independent of σ and D; three routes disagree (0.36 / 0.25 / 0.36) | `DhiObservation.p_valid`, 5.1.3 | Roden 2012; Monigle 2025 (practice) | scientific weakness (§13) | state "c is held constant with column height"; the three routes' status per route | none |
| P1 | detection function | logistic, monotone, ceiling; h50 "tuning" | `DetectionFunction` | none (convention) | acceptable simplification; edge overflow at h ≪ 0 | wording already fixed (#67); `expit` for the edge; tests on h = 0, large h, ceiling, steepness | unit tests |
| P1 | spurious-event model | uniform over the model's own range | `spurious_density` | none | acceptable simplification, must be labelled | label as convention; note the floor's height depends on the declared range | none |
| P1 | partial conformance | censored pick, branch 1 | `likelihood` | none | acceptable simplification | label | exists |
| P1 | absence | `1 − D(h)`; `(1 − d)/(1 − f d)`; slider still enabled when absent | `applied_ratio` | Monigle 2025 (absence as negative evidence) | acceptable; UX | disable the index slider when absent; one sentence "negative index ≠ absence" (8.1.6 has it) | render test |
| P1 | index / geometry factorisation | the valid branch carries evidence about G | `prospect_pos` | none (modelling decision) | acceptable, stated in 8.1.8 | add "conditional on the observation model" | exists |
| P1 | well control | one tie error shared; independence from DHI geometry; floor | `well.likelihood` | none | acceptable, document as a likelihood model for depth evidence | one sentence on the shared depth conversion | exists |
| P1 | benchmark weighting | "fuse" / "blend" | `benchmarks.shrink_toward`, tab 6 | Vincentization | closed (#67): "benchmark blend", "a blend, not an update" | — | exists |
| P1 | censoring | "the one openly redistributable dataset"; "measures the wrong quantity" | `core/censoring` | Edmundson 2021; Hood 2019 | stylistic (absolute) | "the open dataset used here"; "for the seal-capacity interpretation the filled-to-spill observations are censored" | article test |
| P1 | controlling shares | called "the sensitivity analysis" in the article; "two or three limits set the answer" generalised | `EngineResult.controlling_shares`; the tornado is the perturbational sensitivity (4.1.5) | Grant 2020 | documentation mismatch | "controlling-mechanism statistics"; "a few mechanisms dominate the controlling share in this worked case" | article test |
| P1 | empirical claims | elasticities, fill-to-spill rates | `tests/test_censoring.py` | Edmundson 2021; Graham 2015 | sourced and tested | soften the absolutes | — |
| P1 | Monigle score route | §1.2 | `contact_weight_from_score` | Monigle 2025 Fig. 8 | documentation mismatch + mapping | relabel; demote or keep by decision | wording test |

## 4 · Other findings

- **Element independence** is nowhere stated (brief §8): **documentation mismatch**.
- **DHI area versus the assessment minimum** (brief §24): the tab has an optional anomaly area
  used for a cross-check; nothing says that the DHI-supported area is not the assessment
  minimum. One sentence in 8.1.7 and on 5.1.1: **documentation gap**.
- **"Bayesian"** (brief §38): used for the LR update (yes), the importance weighting (yes,
  conditional on the observation model — add the clause), and denied for the blend (correct).
  Kjønsberg's title is a citation. No misuse found.
- **Gas–water tension** `91.657 exp(−0.0126 T)`: the docstring says the attribution to Aplin &
  Yang is unsupported and the source unknown; it is the default in the gas case. Status:
  **unsupported empirical relation as a default**. Options per brief §16: label it an
  empirical default with the methane–brine cross-check as its only support (B), and make it
  editable (C) — it already is (`gas_tension_dyne_cm` overrides it).
- **Pore-throat quartic** (brief §18): no range enforcement; callers pass void ratios from the
  Hansen porosity line, which stays in range for burial depths above ~150 m; a typed porosity
  can leave it. **Likely bug (silent extrapolation)**.
- **Percentiles** (brief §22): "conditional on the assessment minimum" everywhere since #67;
  the histogram convention is stated on 5.1.4 and 4.1.1. Closed.
- **Language** (brief §39): after #71 the tabs are clean of the listed words; the article keeps
  one closing line; the Theory keeps none. Remaining: "the one openly redistributable dataset"
  (THEORY 8.1.9, article), "That table is the sensitivity analysis", "Two or three limits set
  the answer" (article), "in most cases two or three limits set the contact" (8.1.3).
- **Warnings**: none in the suite; `RuntimeWarning` is an error by configuration.

## 5 · "Do not change" list

Sound as they stand, by reading and by reproduction:

- `P(G) × F(h_min)` with the threshold entering once; `pos.accumulation_chance`, `chance_curve`.
- The competing-limit engine: presence and depth draws, the minimum, the controller kept;
  Beha's two-fault case reproduced.
- `pos.depth_exceedance` and its use in every depth figure and the well reading.
- The percentile convention (Hazen, weighted, exceedance, conditional on h_min).
- `LR(s) = f(s | HC) / f(s | NoHC)` → `P(G | s)`, the two caps.
- The likelihood arithmetic itself, `dhi.likelihood`, and the floor `L / s ≥ 1 − c` (the
  arithmetic is right; its description is wrong).
- One weight array for histogram, percentiles, F_post, controlling shares, POS; no rescaling;
  the identity headline = curve at h_min.
- `absence_ratio` and `applied_ratio` (no double count of index and absence).
- `well.likelihood`.
- The outcome shares and the posterior attribution.
- The censored (Tobit) estimator and its tests.
- `ReservoirEffectiveness` (since #66).

## 6 · Proposed order (for approval)

Phase 2, P0: (a) the `c / (1 − c)` statement replaced everywhere with the correct one and a test
that the ratio between depths exceeds it; (b) the mechanical seal: refuse overlap, message, tests;
(c) the obsolete `p_valid` comment in `ui/dhi_tab.py` and the "what this replaced" block in
`dhi.likelihood`.

Phase 3, P1: the P(G)/limit mapping (per-limit meaning line, 8.1.2/8.1.3 table, element
independence sentence); the Monigle relabel (and the author's decision on demotion); the
geometry-likelihood classification table (8.1.7 and a 5.1.3 fold); c constant in h; the
gas–water tension label; the pore-throat range warning; "sensitivity analysis" and "two or three
limits"; the DHI-area sentence; the absent-anomaly slider; the Bayesian clause.

Phase 4: language; Phase 5: article and figures on the corrected statements (the article's
`c/(1−c)` sentence and "sensitivity analysis"); Phase 6: `docs/FINAL_RED_TEAM_VALIDATION.md`.
