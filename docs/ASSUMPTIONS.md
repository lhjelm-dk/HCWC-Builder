# Assumptions (developer-facing)

Every assumption the model rests on, where it is made in the code, where it is stated to the
user, and how it is labelled. Written in Phase 7 of the clean-up (18 Sep 2026); the user-facing
statement is tab 8.1 (`docs/THEORY.md`, 8.1.8 in particular) and 5.1.7 on the DHI tab. The
defaults themselves, with unit, meaning, provenance and range, are `hcwc/core/defaults.py`.

Labels: **modelling choice** (a structural decision; changing it changes the model),
**elicited** (a number the assessor states; has no external referent in the tool),
**heuristic** (a rule offered, not applied), **convention** (a definition; no alternative is
claimed better).

## The geological model

| assumption | label | in the code | stated |
|---|---|---|---|
| `P(G)` is the chance the elements work at the crest, of any size; the threshold enters once through `F(h_min)` | convention | `core/pos.accumulation_chance`, `EngineResult.above_minimum` | 8.1.1, 8.1.3 |
| An element chance imported from another tool carries no volume criterion | convention (mapping) | `io/epos.read` | 8.1.1 |
| Limits are sampled, not blended; the shallowest active one sets the contact | modelling choice | `core/engine.run` | 8.1.2 |
| Presence draws are independent of everything, including other limits' presence | modelling choice | `core/engine.run` | 8.1.2, 8.1.8 |
| Depths and capacities may be correlated through a Gaussian copula on elicited rank correlations; an inconsistent matrix is projected to the nearest PSD and reported | modelling choice, elicited | `core/correlate` | 8.1.2 |
| Calculator inputs are independent uniforms (seal, mechanical, charge) | modelling choice | `core/seals`, `core/charge`, `ui/sources` | 8.1.2, 8.1.8 |
| The apex is shared by every element in a realisation; `z_HCWC = z_apex + H` | convention | `EngineResult.contact_m` | 8.1.3 |
| One fluid at a time; no two-phase column, no hydrodynamics, no compartments | modelling choice (limitation) | `core/seals` (physics present, not wired), `docs/PLAN_DUAL_PHASE_SEAL.md` | 8.1.8 |
| Oil–water interfacial tension 18–28 dyne/cm, flat in temperature; gas–water on a temperature line agreeing with methane–brine data | elicited / modelling choice | `core/seals` | 8.1.8, `archive/development_notes/IFT_CHECK_2026-09-15.md` |
| Percentiles are exceedance percentiles (P100 shallowest), Hazen plotting positions on the weighted sample, reported conditional on `h ≥ h_min` | convention | `core/engine.weighted_percentiles`, `EngineResult.percentiles`, `DhiPosterior.percentiles` | 8.1.3 |
| Depth axes under column-space curves sit at the median apex | convention (drawing) | `core/pos.depth_axis` and the figures | 8.1.3 |

## The DHI evidence index

| assumption | label | in the code | stated |
|---|---|---|---|
| The evidence index is a relative scale, 0 neutral, no physical units | convention | `core/dhi.StrengthModel` | 8.1.4, 5.1.2 |
| `f(s \| HC)` and `f(s \| NoHC)` are Gaussians given by P1/P99; the shipped pair is a reference relationship, not a basin calibration | elicited (defaults) | `core/defaults.EVIDENCE_INDEX_*`, `core/dhi.StrengthCase` | 8.1.4, 5.1.2 |
| `LR(s) = f(s \| HC) / f(s \| NoHC)` updates `P(G)` by the two-state form; the reference outcomes are presence, not a volume criterion | modelling choice, mapping | `core/dhi.simm_update`, `p_g_given_strength` | 8.1.4 |
| A single channel's LR is capped at 10 : 1 either way; the combined ratio at 50 | modelling choice (Simm; Kjønsberg) | `core/dhi.R_SINGLE_CHANNEL`, `R_CAP` | 8.1.4, 8.1.6 |
| The index carries no contact-depth information and never touches the weights | modelling choice | `core/dhi.likelihood` (no strength argument), `tests/test_dhi_audit.py` | 8.1.4, 8.1.6 |
| An absent anomaly updates `P(G)` through `(1 − d)/(1 − f·d)` with `f` the relative false-positive rate, tied to `d` | modelling choice, `f` elicited (0.5 maximum ignorance) | `core/dhi.absence_ratio` | 8.1.4 |

## The DHI geometry

| assumption | label | in the code | stated |
|---|---|---|---|
| The realisations are a sample from `p(h \| G)`; the update is importance weighting, nothing re-simulated | modelling choice | `core/dhi.update` | 8.1.5 |
| `D(h)` is logistic in column height with a ceiling below 1; not a seismic forward model | modelling choice | `core/dhi.DetectionFunction` | 8.1.5, 5.1.3 |
| The pick is a normal, PERT or uniform density in depth; its width is the pick plus depth-conversion error | elicited | `core/dhi.DhiObservation` | 8.1.5, 5.1.1 |
| `c = P(picked event is the contact \| G, attributes)` is conditional on `G`, independent of `h`, and never derived from the index | modelling choice, elicited (three routes: stated; geometric mean of graded attributes, heuristic; Monigle et al.'s rule, calibrated on their database) | `core/dhi.likelihood`, `contact_weight_from_score`, `ui/dhi_tab` | 8.1.5, 5.1.3 |
| A flat event that is not the contact is equally likely anywhere in the declared contact range (`s = 1/span`) | modelling choice | `core/dhi.spurious_density`, `LimitSet.contact_support_m` | 8.1.5 |
| The floor `1 − c` keeps every depth in play (Cromwell) | modelling choice | `core/dhi.likelihood` | 8.1.5 |
| Partial conformance is a censored pick: the normal cumulative at the cutoff, spurious branch 1 | modelling choice | `core/dhi.likelihood` | 8.1.5 |
| Absence within `G` reshapes the column as `1 − D(h)` | modelling choice | `core/dhi.likelihood` | 8.1.5 |
| A well penetration is independent evidence multiplied in, with a floor `1 − p_connected` | modelling choice, elicited | `core/well` | 8.1.5 |
| The two channels are one observation's two information channels; the factorisation assigns each to one factor and is not a generative model of the whole observation | modelling choice (limitation) | `core/dhi.prospect_pos` | 8.1.6, 8.1.8 |
| The outcomes of a seen DHI are named by where the contact lies relative to the indicated contact band, the P99 to P1 of the pick; the mass within the band is split by the branch of the likelihood that put it there | convention (reading of the posterior) | `core/dhi.outcome_shares`, `likelihood_branches` | 8.1.6, 5.1.4 |

## The empirical comparison

| assumption | label | in the code | stated |
|---|---|---|---|
| Benchmarks are compared beside the result and never joined; a benchmark is a prior, not a likelihood | modelling choice | `core/calibration`, `ui/empirical` | 8.1.7 |
| Filled-to-spill pools are right-censored observations of seal capacity | modelling choice | `core/censoring` | 8.1.7 |
| The record is discovery-conditioned, censored above and truncated below | limitation | `io/benchmarks`, `core/censoring` | 8.1.7, 8.1.8 |
| Imported datasets are never written to disk or sent over the network | constraint | `io/datasets` | tab 6, `CLAUDE.md` |
