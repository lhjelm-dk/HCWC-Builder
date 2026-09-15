# Open questions, 15 September 2026

Everything asked for this week is on `main`. What remains is a set of decisions that are Lars's
rather than the code's. Each item: the question, what was found, a suggested answer, and the cost
of acting on it. Numbers are from the shipped defaults unless stated.

## 1 · The well's connection chance opens at 0.60. Is that the intended default?

**Found.** The likelihood floor under a penetration is `1 − p_connected`. At 0.60 the floor is
0.40, and a 40 m hydrocarbon–water bracket from a well narrows the contact's P90–P10 from 155 m
(prior) to 108 m, against 109 m for the water depth alone: the bracket adds almost nothing. At
0.95 the same bracket gives 52 m. A reader who enters a bracket at the default will see the well
do little, and the reason is the slider, not the bracket.

**Suggestion.** Keep 0.60 if it is the elicited caution for an offset well of unknown
connectivity; the floor is the point of the mixture. Add a live caption beside the slider that
states what the floor costs on this prospect ("at 0.60 this bracket narrows the contact to 108 m;
at 0.95, 52 m"), so the choice is visible where it is made. Small. If the default is meant for a
well *in* the closure, 0.90 is the better opening value.

## 2 · Tofte North runs its seal on gas tension with oil densities

**Found.** The shipped worked example sets the seal calculator's fluid to Gas with hydrocarbon
density 0.70–0.85 g/cm³. The app's own check fires on it ("an oil density against a gas
interfacial tension … the most generous combination the calculator can produce"). The charge on
that example is typed, so the phase-clash refusal does not catch it.

**Suggestion.** Decide what Tofte North is. If oil: set the seal fluid to Oil; with the elicited
18–28 dyne/cm its capacity falls to about 0.6× the present value and the controlling shares shift
toward the seal. If gas: set the density to 0.20–0.35. Either is a one-line edit to the example
file plus a re-read of the numbers tab 1 and the paper quote for it. Small.

## 3 · Should c take Monigle's calibrated rule as a third route?

**Found.** Monigle et al. (2025) calibrate the contact weight on drilled outcomes:
`w = min(2 × DHI score, 0.95)`. That is the app's `c`, measured rather than elicited. The app
offers `c` typed (default 0.36) or from three graded attributes by geometric mean, and says the
combination rule is a heuristic. The shipped 0.36 corresponds to a Monigle score of 0.18.

**Suggestion.** Offer a third source beside the slider and the attributes: a DHI score in
Monigle's sense, mapped by their rule, labelled as calibrated on their database and not on this
basin. It is the one external referent the tab has, and the tab says it lacks one. Small; the
question is whether their score is elicitable by a reader who does not have their scheme.

## 4 · The gas–water tension line: keep as a line, or elicit it like oil?

**Found.** `91.657·exp(−0.0126 T)` sits where methane–brine data sit, but its provenance is as
unknown as the oil line's was. It is applied per realisation from the temperature draw; the reader
cannot see or override it.

**Suggestion.** Keep the line as the default and expose it: a slider "Gas–water interfacial
tension (dyne/cm)" that opens on the line's value at the prospect's temperature, so a measured
value overrides it and the two fluids are handled the same way. Small. Alternatively replace it
with Firoozabadi & Ramey (1988), which needs the paper (paywalled).

## 5 · Commodity scenarios and the two-phase seal: go, and in which order?

**Found.** Step 0 of `PLAN_DUAL_PHASE_SEAL.md` is closed: with a sourced oil tension the
derivation reproduces Hood's 20 % gas share from the inputs. The commodity-scenario slice (Hood
slide 19) needs a per-realisation commodity carried into the engine, and the engine draws each
limit from a quantile table by its own uniform, so the calculator's realisation identity is not
carried today. That is the "engine passenger array" step of the plan, and it is the design
question, not the arithmetic.

**Suggestion.** Rank-match: the charge calculator hands the engine, beside the quantile table, the
commodity (oil only / gas only / dual) of the calculator sample at each rank, and the engine reads
it at the uniform it drew for that limit. It is exact where commodity is monotone in fill depth
and approximate otherwise, which is a stated limitation. Medium. Do it before the two-phase seal,
as the plan says; the seal then feeds a capillary GOC into the same passenger.

## 6 · Lowry et al. (2005): buy the PDF before the manuscript cites it

**Found.** `docs/LOWRY_2005_REVIEW.md` is written from the abstract. Whether their risk array is
derived from competing mechanisms or stated band by band decides whether it is prior art for the
engine or for the level above it. USD 40 on your side; the review lists the four things to check.

## 7 · Two audit items left as acceptable

P2-5, computed limits enter as 101-point quantile tables bounded at the sampled extremes (tails
beyond the 20 000-draw min and max unreachable, 1 % resolution); P2-6, the core fixture states the
spill as a column where the app states it as a depth, so the depth-stated spill with apex coupling
is tested through the UI only (P2-2's test now covers part of it). **Suggestion.** Leave both;
201 points and a core depth-stated fixture are each an hour if ever wanted.

## 8 · Tab 6's estimator defence: leave folded, or move to tab 8?

**Found.** Plan item A2 wanted the three argument sections (why the published regression measures
the wrong thing, whether the corrected model fits, the second bias) off tab 6. The tone pass
restated them and they sit folded, since their figures are computed from the data and a static
copy would lose them.

**Suggestion.** Leave them. Moving live figures to a document loses the calibration plot and the
bias curve, which are the evidence; the fold already keeps them out of a first pass.

## 9 · Merges land without a green check

**Found.** The repository has no required status check, so `gh pr merge --auto` merges at once
and the "merge when green" discipline is a watcher in this session rather than a rule on the
repository. Branch protection needs GitHub Pro or a public repository.

**Suggestion.** Keep the watcher (it has held for every code PR) and, if the repository goes
public with the paper, require the test workflow on `main` at that point. Nothing to do now.

## 10 · Hood's confidence annotation on every input

**Found.** `docs/HOOD_2019_REVIEW.md` §3 records that Hood puts a `Confidence*` grade on every
box of his slide 8, tracked for calibration, and the app carries no confidence field on any
input.

**Suggestion.** Defer. It is a real recommendation and a large one; a per-limit confidence grade
touches the limit block, the save format, the export and the report. Worth a plan of its own
after the paper, not a slot in this list.
