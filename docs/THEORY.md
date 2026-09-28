# Theory and methods

*The statement of the method behind the HCWC Distribution Builder. The operational tabs enter
assumptions, show results and name what to check; they refer here by section number. The
paper (8.2) is the narrative version.*

## Model overview

![The model as two rows. The geological model is the prior: the element chances give P(G), the chance an accumulation is present; given an accumulation, the limits compete, the shallowest active one sets the contact and is recorded, and F(h) = P(H ≥ h | G) is the contact distribution read as an exceedance. The DHI is evidence: the evidence index gives a likelihood ratio that updates P(G), and the contact geometry reweights the same realisations; the index never moves the contact, the geometry never moves P(G), and each enters once. One weighted sample reads the histogram, the percentiles, F(h) and the chance. Each row ends in the probability of meeting the threshold, POS(h) = P(G) × F(h) and its posterior, read at the assessment minimum h_min and at the well; the benchmarks are compared with both contact distributions and never joined. The same figure with the tab each box lives on is Figure 1.0a.](figures/fig0_workflow.svg)

The model has two rows. The geological model is the prior: the accumulation chance `P(G)`
(8.1.2); the competing limits and the contact distribution given an accumulation, `HCWC | G`
(8.1.3); the reading of that distribution as a chance against a threshold, `POS(h) = P(G) × F(h)`
(8.1.4); the dependence between limits (8.1.5). The DHI is evidence: the evidence index updates
`P(G)` (8.1.6); the contact geometry updates `HCWC | G` (8.1.7); the two updated factors give the
posterior `POS(h)` from one weighted sample (8.1.8). The empirical record is compared beside both
contact distributions (8.1.9). Validation, assumptions and limitations (8.1.10) and the
references (8.1.11) close the method.

Notation. `G` is the accumulation state: the geological elements work at the crest and a
hydrocarbon column of some height exists. `H` is the column height, m; `z_apex` the apex depth,
m TVDSS; `z_HCWC = z_apex + H` the contact depth, increasing downward; `h_min` the assessment
minimum, a column height; `z_well` the well's reservoir entry depth; `s` the DHI evidence index;
`c` the contact attribution. A probability written `| G` is conditional on the accumulation.

The construction follows Beha, Christensen and Young (2012), who enumerate trapping elements
that seal or fail and collapse the result onto leak-point frequencies, and Hood (2019, 2024), who
treats the column as a competition between limits. It is run here as a continuous, correlated
Monte Carlo. The per-element depth-dependent chance (8.1.4), the likelihood form of DHI evidence
(8.1.7) and the censoring correction to the empirical record (8.1.9) are not in that literature.

## P(G): accumulation chance

Definition. `P(G)` is the probability that an accumulation is present: the geological elements
work at the crest, and there is a column of some height. It is the product of the element chances
entered on tab 2.0, each as play × conditional:

`P(G) = P(charge) × P(closure) × P(reservoir) × P(retention)`

Interpretation. `P(G)` is the first factor of every probability the tool reports and the prior the
DHI evidence updates (8.1.6). It carries no volume criterion. The threshold enters once, through
`F(h_min)` (8.1.4), and never inside `P(G)`.

Assumption. A trapping element that fails below the crest, a fault window at depth or a seal that
holds a finite column, does not reduce the chance of an accumulation; it limits the column. Such
mechanisms are limits on tab 3.0 (8.1.3), and only whether an element works at the crest belongs in
`P(G)`. Folding a limit into `P(G)` understates the chance and, because volume is conditioned on
it, overstates the volume (Beha et al. 2012).

Assumption: the element chances are conditionally independent. `P(G)` is their product, the
convention of prospect risking. Dependence between the presence probabilities, a charge and a
reservoir that stand or fall on the same seismic interpretation, a closure and a fault seal that
share a fault, is not modelled; the copula of 8.1.5 couples limit depths and capacities, not
element chances.

Element chance against limit. Each element chance answers "does the element work at the
crest"; each limit under it answers "how far does the column extend, given that it does". The
two are separate only if every input is read that way:

| element | the element chance is | the limits under it are | the double count to avoid |
|---|---|---|---|
| Charge | hydrocarbons reached the trap | charge limitation: the delivered volume fills the trap to a depth; always active, since a finite volume is always delivered | a chance that already means "enough to be worth finding" |
| Closure | a closure exists at the crest; 1.00 where a spill point is mapped | the spill point, always active; a fault-bounded geometry window with its own presence | none, once the spill is a limit and not a chance |
| Reservoir | reservoir present at the crest | a base or pinch-out limit; an effectiveness decline (5.3) that lowers the chance without moving the contact | the same reservoir loss entered as both a pinch-out and a decline |
| Retention | a seal exists at the crest and holds something | capillary capacity, always active; continuity holes, fault leakage, preservation and mechanical failure, each with a presence chance and a depth or capacity | a retention chance that already means "holds the full column"; a hole or a leak *at the crest* entered as a limit, which is a crest failure and belongs in the element chance |

A limit's presence chance is the chance the mechanism exists below the crest; a mechanism whose
depth distribution puts substantial mass at the apex is a crest failure entered in the wrong
place, and the run checks (8.1.10) flag it.

Limitation. An element chance imported from another tool is read as the chance the element works
at the crest. If the source's definition carried a minimum volume, the threshold would be applied
twice.

## Competing limits and HCWC

Definition. A hydrocarbon column is stopped by whichever mechanism acts first: charge runs out,
the closure spills, a fault juxtaposes the reservoir against a carrier, a seal leaks at a
capillary pressure the column exceeds, a seal fails mechanically, the reservoir pinches out. Each
mechanism is a limit with two properties: a probability of being present on this prospect, and a
distribution of the depth or column height at which it acts.

Construction. In each Monte Carlo realisation every limit receives a presence draw and a depth
draw. The column is the shallowest active limit, and the limit that set it is recorded:

`H = min { h_i : limit i active }`,  `z_HCWC = z_apex + H`

The contact distribution, the controlling-mechanism share of each limit, and both as functions of
depth follow from the sample. The shape of the contact distribution is an output; on the shipped
prospect it is right-skewed with a step at the spill.

Limits are sampled, not blended. Averaging a leak into a background column-height distribution
suppresses the realisations above the leak and leaves the rest untouched, so the blended
distribution corresponds to no geology, and adding a leak can raise the apparent volume (Hood
2024). Taking the minimum keeps every realisation a column that some mechanism produces, at a depth
that mechanism reaches. Drawn on one axis, each limit's exceedance curve flattens at its
`P(active)`, and the contact curve lies below every active limit's curve — below the lowest of
them, because a column reaches a depth only where every active limit permits it. On the shipped
prospect the gap to the lowest single curve is 37 points of exceedance at a 254 m column.

Mechanism families. Structural spill is a mapped depth. Charge limitation is the depth at which
the accumulated pore volume equals the volume the basin model delivered, found by integrating the
area–depth table. Capillary seal capacity is `h_max = P_c / (Δρ · g)` with `P_c = 2γ cos θ / r`: a
column height set by the seal's largest connected pore throat, the interfacial tension and the
density contrast. Seal continuity is a hole in the seal: a channel, an erosional window, a
breaching fault tip. Fault seal is a juxtaposition window, a depth, or a leak capacity, a column.
Mechanical failure is the column at which the crest pressure reaches the minimum horizontal
stress, `H = (S_Hmin − P_p) / (grad_w − grad_h)` (Grant 2020).

A limit is not necessarily a leak point. Some mechanisms represent an escape path — structural
spill, fault leakage, seal failure — and their distribution is the depth at which hydrocarbons
leave the accumulation, conditional on the accumulation existing. Others cap the column with the
hydrocarbons staying in the trap: charge insufficient to fill higher, reservoir continuity ending
the connected pore volume. In both cases the quantity entered is the maximum column the mechanism
supports in that realisation, not the depth at which it is locally exceeded. A mechanism that gives
way while the hydrocarbon stays inside the closure does not set the contact: a base seal over a
unit that is itself closed, a fault at capacity against a dead-end juxtaposition, a four-way
closure with nowhere for the column to go. Trap style decides it, and the judgement is carried
either by the mechanism's presence probability, the share of realisations in which an escape path
exists, or by the depth stated for the limit; the minimum assumes it has been made.

Units. A limit is stated as a column below the apex or as a depth in m TVDSS; the engine converts
a depth to a column against the apex drawn in the same realisation. A capacity does not move when
the apex moves; a mapped surface does (8.1.5).

Presence. A limit with `P(active) = 0.3` applies in three realisations in ten. At least one limit
is always active, since every prospect has a spill point; a set in which the column could be
unbounded is refused.

Controlling mechanism. The index of the shallowest active limit is recorded per realisation. Its
share over the sample is the ranking on tabs 3.1 and 4.1.2: a controlling-mechanism statistic,
the frequency with which each mechanism sets the minimum, which is not a sensitivity (the
tornado of 8.1.10 is). On the worked prospect a few mechanisms dominate the share; a mechanism
with a small share is still part of the distribution. The ranking is reported over all realisations and
over those meeting the assessment minimum. A limit that usually stops the column short of the
minimum is under-represented among the realisations that meet it, because it is the most severe;
that is the selection effect of the empirical record (8.1.9) one level up. The share is not
constant down the structure; tab 4.1.2 draws it as a share of all realisations or as the
mechanism mix at each depth.

Validation. Beha et al.'s (2012) two-fault example (0.60 / 0.12 / 0.28 at three leak points) is
reproduced by the engine to Monte Carlo error (`tests/test_engine.py`). Grant (2020) publishes the
controlling-limit diagnostic as column height control statistics; Lowry et al. (2005) give chance
against column height.

## Column height, HCWC and POS

Two exceedances. `F(h) = P(H ≥ h | G)` is defined in column-height space, where the threshold
lives. `P(z_HCWC ≥ z | G)` is defined in depth space, read on the realised contacts, where a well
and any figure with a depth axis live. The two agree when the apex is pinned and differ by the
apex spread when it is not. The well reading and every chance-against-depth figure use the
depth-space exceedance; the assessment minimum is a column height, and where it is marked on a
depth axis it is drawn at the median apex and labelled as that equivalent.

Threshold. A probability of meeting an assessment criterion refers to a stated threshold. Here
the threshold is the assessment minimum `h_min`, the smallest column that would make the well a
discovery, set on tab 2.0. The prospect chance is

`POS(h_min) = P(G) × F(h_min)`

and the volume criterion enters here and nowhere else. `P(G) × F(h)` at every `h` is the chance
against threshold (tab 4.1.3); the headline is that curve at `h_min`. Every chance on the
operational tabs carries the threshold it was read at and states whether it includes `P(G)`.

The well. A well entering at `z_well` finds hydrocarbons if the accumulation is present and the
contact lies below the entry depth:

`P(well) = P(G) × P(z_HCWC ≥ z_well | G)`

`P(z_HCWC ≥ z_well | G)` alone is the location factor `r`; quoted as the chance the well finds
hydrocarbons it overstates the well by `1 / P(G)`.

Percentiles. Contact percentiles and histograms are reported as `z_HCWC`. Every percentile the
tool prints uses one estimator: Hazen plotting positions on the sorted, weighted sample, P100 the
shallowest and P0 the deepest. The percentiles the tabs headline are conditional on the assessment
minimum, taken over the realisations whose column reaches `h_min`, because a contact quoted for a
discovery is a contact given that there was one; `F(h)` itself is over every realisation
conditional on `G`. The tabs label which.

Per-element chance. Taking the shallowest active limit within each element, its group minimum,
gives `P_e(z)`, the chance that element permits a contact deeper than `z` (tab 4.2). Under
independent limits `∏_e P_e(z) = P(z_HCWC > z | G)`, and the product is checked against the
direct distribution on every run (8.1.10). WellVolPOS computes one location factor and spreads it
across the elements by a weighting rule; the derived curves say which element binds at that
depth. Reservoir enters the depth dependence twice: as a base or pinch-out
limit that moves the contact, and as an effectiveness decline (diagenesis, cementation, a
net-to-gross trend) that lowers the chance without moving it. Only the first is a competing
limit, and the consistency identity is checked over the contact-controlling elements. An element
with no limit in the model never controls the contact; its derived curve is its element chance,
unchanged with depth.

## Correlation and dependence

Copula. Limit depths and capacities can be correlated through a Gaussian copula, elicited as
rank correlations on pairs. A matrix that is not positive semi-definite is projected onto the
nearest one that is, and the projection is reported. The realised correlation of every sampled
pair, apex included, is reported in the run checks (8.1.10).

Apex and mapped depths. A spill point and the apex are picked off the same depth-converted
surface, so a depth-conversion error moves both together. Left independent, a realisation can put
the spill above the apex, and the derived closure height carries a spread that is an artefact: on
a 120 m apex uncertainty with a mapped spill, 33 m independent against 11 m at a correlation of
0.9. The same coupling inflates the published column-height regression (8.1.9), since column
height and trap height share the apex pick.

Assumption: presence is independent. Correlation applies to depths and capacities only. Whether a
limit is present is drawn independently of everything, including the presence of every other
limit. Two faults that leak at correlated depths are expressible; two faults that stand or fall
together are not. Beha et al. (2012) make the same assumption. A presence copula is not
implemented.

Assumption: calculator inputs are independent. The seal calculator's temperature, contact angle,
throat radii, densities and tension are independent uniforms, though hydrocarbon density and
temperature move together with depth; the mechanical calculator's stress and pore pressure are
independent, though their coupling is most of why fracture gradients rise with overpressure.
Independence overstates the spread of a capacity and, for the mechanical seal, the low tail of the
headroom. The correlation editor couples limits with each other and cannot reach inside a
calculator. The seal and charge calculators share a phase and not a fluid; the phase check on tab
3.0 is the whole of the coupling. A base seal entered as the top seal offset by the reservoir
thickness has identical inputs and not an identical outcome: sampled independently, the two fail
at different columns in the same realisation. Where the two are one unit the pair is correlated,
and the default correlation table lists it.

The shared apex. Every element's contact is `z_apex + h`, so in depth space the element curves are
dependent even under independent limits and their product is not the contact distribution. The
consistency test (8.1.10) is exact in column-height space and is run in both.

## DHI evidence index and the update of P(G)

Two channels. One seismic observation carries two kinds of evidence, and each updates one factor
(8.1.8). Its character, how hydrocarbon-like the response looks, is evidence about whether there
are hydrocarbons at all: it is placed on the DHI evidence index and updates `P(G)`. Its geometry is
evidence about the contact given `G` (8.1.7).

Definition. The DHI evidence index `s` is a conceptual scale for the strength and polarity of the
seismic evidence: 0 is neutral, positive values increasingly positive evidence, negative values
increasingly negative evidence or a missing expected response. It has no physical units; a value
of 5 or −5 carries no absolute geophysical meaning. Two conditional densities of the index are
given, `f(s | HC)` for hydrocarbon-bearing and `f(s | NoHC)` for non-hydrocarbon outcomes, the
reference distributions; each is a Gaussian on the index specified by its 1st and 99th
percentiles. They are densities of the index given the outcome, not probabilities of the outcome
given the index.

Equation. The likelihood ratio at the observed index and the updated chance are

`LR(s) = f(s | HC) / f(s | NoHC)`

`P(G | s) = LR(s) · P(G) / (LR(s) · P(G) + 1 − P(G))`

Interpretation. `LR(s)` is the evidence weight of the observation. The reference outcomes are
hydrocarbon presence and absence, so `G` is read as an accumulation of any size; the threshold is
applied once, through `F(h_min)`, and never inside `P(G | s)`. The volume weight `LR / (LR + 1)`,
the weight the evidence alone would carry against an even prior, is reported beside `LR` and is not
a chance of anything.

Bounds. A single channel's `LR` is capped at 10 : 1 either way (Simm & Bacon 2014; Simm 2020):
one line of fluid-indicator evidence rarely exceeds 3, and a value above 10 sends the assessor back
to the inputs. The combined update is guarded above the one published measurement (8.1.8).

Assumptions. The reference distributions the tool ships with are a reference evidence
relationship, not a calibration for any basin and not a measured quantity; nothing in the
repository reproduces them from data, and they are editable on tab 5.1.2. They carry no information on contact
depth, trap height, spill point or assessment minimum: the index informs the probability of
hydrocarbon presence and does not predict the HCWC. The two channels are two information channels
from one observation, not two independent observations; their overlap is handled by the
factorisation (8.1.8) and by the bounds on each.

Absent anomaly. A response absent where one was looked for enters the chance through its own
ratio, `R_absent = P(absent | G) / P(absent | ¬G) = (1 − d) / (1 − f · d)`, with `d` the mean
detectability over the geological columns (8.1.7) and `f` the chance a barren trap shows a response
of the same class, stated relative to `d`. Tying the false-positive rate to `d` sets the behaviour
at the ends: where nothing could have shown, absence is uninformative; where a barren trap shows
as readily as a filled one, likewise; and since `f · d ≤ d` the ratio is never above one. `f` is
elicited; the shipped 0.5 is the maximum-ignorance value and no calibration is known. Within `G`
the same absence reshapes the column (8.1.7). Negative values of the index describe increasingly
negative evidence within an indexed observation; a complete absence is a separate observation and
the two are not combined.

## DHI geometry and the update of HCWC | G

Construction. The geological realisations are a sample from the prior `p(h | G)`. The contact
geometry of an observation `D` enters as a likelihood `L(D | h, G)` over those realisations, and
the posterior is the same sample with weights

`w_j ∝ L(D | h_j, G)`

This is self-normalised importance sampling and, for this sample, an exact Bayesian update:
nothing is re-simulated, each realisation keeps its controlling limit, and prior and posterior are
the same realisations, so `F_prior(h)` and `F_post(h)` are directly comparable. The DHI adds no
realisations and moves no sampled limit. Where a sample of the posterior is needed rather than a
curve, for the export, the benchmark comparison and the posterior window of Figure 5.2.1a, the
realisations are drawn by their weights with replacement.

Likelihood for a seen anomaly.

`L(D | h, G) = c · D(h) · Pick(z | z_apex + h) + (1 − c) · s`

`D(h)` is a simplified detectability model, not a seismic forward model: the chance a column of
height `h` produces a mappable anomaly, near zero below tuning thickness, rising through the
resolution limit, flat below a ceiling. It is logistic in `h` and its three parameters are exposed
as modelling assumptions. The ceiling is below 1: a function reaching certainty would make an
absent anomaly infinitely strong evidence. Being monotone it cannot represent a response that
weakens again with thickness, as a Class III sand's can when the top and base responses separate;
that is a limitation of the form.

`Pick(z | z_apex + h)` is the chance the interpreted termination lands at `z` if the contact is at
`z_apex + h`: a normal, PERT or uniform shape in m TVDSS, its width the pick error plus the depth
conversion. Partial conformance, a response bright over the crest and reliably absent below a
depth, is a censored pick: the normal cumulative where a pick's is the density, a soft constraint
on the depth of the response's edge. Both of its branches are probabilities of the event *edge
recorded above the cutoff*, so its spurious branch is 1 where the picked case's is `s`.

`c = P(the picked event is the contact | G, contact-geometry attributes)`. A flat event can be
lithology, a diagenetic front, fizz gas or a processing artefact (Roden, Forrest & Holeywell
2012). Monigle et al. (2025) grade five DHI attributes; this tool reads anomaly strength and
lateral amplitude contrast as DHI character attributes, which bear on presence and are what the
evidence index carries, and fit to structure, amplitude terminations and the fluid-contact
reflection as contact-geometry attributes, which bear on whether the picked event is the base of
the column. The split is this tool's. `c` is conditional on `G`, because every realisation it
weights was drawn on that assumption, and carries nothing of the index. It is offered two ways:
stated, or as the geometric mean of three graded attributes, a heuristic. Beside them, as a
comparison and not a source,
the tab shows what Monigle et al.'s (2025) column-height weighting practice
`w = min(2 × score, 0.95)` gives from a typed DHI score in their sense: an empirical
relationship reported for their drilled-prospect database on their five-attribute score and in
a scenario construction, not a calibration of `c` on this tool's inputs. The ceiling of 0.95 is
the one Hood (2019) and Monigle et al. use in practice. `c` is taken independent of `h`; column height enters the
valid branch through `D(h)` only.

`s` is the density of a spurious event over the model's declared contact range, one over the
support width.

What in the likelihood is physics and what is judgement. None of the terms is a measured
physical relationship; the arithmetic is exact given them, and they are the assumption:

| term | class | what a reviewer can challenge |
|---|---|---|
| `c` | elicited (stated, graded by a heuristic, or an external practice) | held constant with column height; independent of the pick width and of `D(h)` |
| `D(h)` | modelling convention with elicited parameters | logistic and monotone; `h50` identified with tuning thickness by heuristic; no weakening with thickness |
| `Pick(z)` | elicited | pick and depth-conversion errors folded into one width; the depth conversion is shared with the apex pick and that is not carried |
| `s` | modelling convention | a spurious event equally likely at any depth in the declared range; the floor's height depends on that range |
| partial conformance | modelling convention | the spurious branch set to 1, a bound rather than a derivation |
| absence: `1 − D(h)` and `f` | modelling convention; `f` elicited at 0.5 by ignorance | the false-positive rate tied to `d` for the behaviour at the ends |
| independence of the terms | modelling convention | one interpreter grades all of them |
| the well factor | a likelihood for depth evidence; `σ` and `p_connected` elicited | its depth conversion is the DHI's; the two are multiplied as independent |

`c` is held constant with column height in the current model. Whether a flat event becomes a
more plausible contact as the column thickens, and whether `c` should move with the pick width
or with `D(h)`, are not modelled.

The DHI's extent is not the assessment minimum. The geometry is evidence about the contact and
the column; the assessment minimum is a separate criterion set on tab 2.0. A DHI that covers a
large area does not make the minimum met, and a column that meets the minimum need not show.

The floor. Since `Pick ≥ 0`, `L / s ≥ 1 − c` at every depth: no depth's likelihood falls below
`1 − c` times the flat alternative, so no depth is excluded, and the posterior share of any
region of the prior cannot fall below `(1 − c) · s / L_max` of its prior share. An attributed
contact therefore cannot become certain, however sharply the pick is drawn. The floor does not cap
how strongly the geometry discriminates between two depths. The likelihood ratio
between the best-supported depth and any other is at most `1 + c · D · Pick_max / ((1 − c) · s)`,
which grows as the pick narrows; on the shipped prospect (`c` 0.36, σ 10 m) it is about 8, and
at `c` 0.9 and σ 2 m about 600. A bounded pick shape without the floor would assign zero below
its deepest bound, and no later evidence can revive a zero (Cromwell's rule). Under a pick the
geology considers implausible, the posterior median follows the pick while the model supports
it and then returns to the prior, with the effective sample size returning to the full count:
the model concludes that the event is probably not the contact, rather than that the contact is
where the pick says.

Absent anomaly. Within `G`, absence enters as `1 − D(h)`, largest at small `h`: where the detection
threshold falls inside the geological columns, absence reshapes the contact toward the short
columns that would not have shown. What absence says about `P(G)` is the separate ratio of 8.1.6.

Well penetration. Hydrocarbons proven to `z_hc` and water at `z_w` give
`L = p_connected · [Φ((z − z_hc)/σ) + Φ((z_w − z)/σ) − 1] + (1 − p_connected)`: one tie error
between the well's depths and the mapped surface, and a floor of `1 − p_connected` for the chance
that the well samples a different accumulation. A pick and a penetration are multiplied as
independent evidence.

Effective sample size. Kish's `(Σw)² / Σw²` reports how much of the original geological ensemble
the posterior rests on. A low value does not mean the interpretation is wrong; it means the result
is strongly dependent on a relatively small part of that ensemble, which is worth knowing when the
result is quoted. It reports the geometry channel only; the index channel updates one number and
discards no realisations.

Mechanism mix. The evidence moves the depth distribution and, only through it, the mechanism mix.
Drawn as shares of all realisations, the controlling mechanism by depth differs between the
geological and the updated result, because the evidence moves which depths are reached; drawn as
the mix within each depth bin, the two are near-identical. The DHI reweighting changes the
relative frequency of mechanisms within the contact-depth ensemble it favours; it is not
evidence about which element failed.

## Combined DHI posterior and POS

Factorisation. The realisations are conditional on `G`, so a likelihood over them redistributes
probability among column heights and cannot say whether `G` holds. The model is therefore
factorised: the index updates `P(G)` (8.1.6) and the geometry updates `HCWC | G` (8.1.7). Each is
a Bayesian update of the quantity it names, exact conditional on an observation model that is
itself the assumption (8.1.6, 8.1.7). The factorisation is a modelling decision. The whole observation is
not modelled generatively across `G` and `h` together; in such a model the valid-contact branch of
the geometry likelihood would carry some evidence about `G` as well. The tool assigns that evidence
to the index channel and uses the geometry within `G`, once. A second likelihood ratio on `P(G)`
built from the geometry would count the observation twice.

Equation. The prospect chance at a threshold and the chance against depth are

`POS(h) = P(G | s) × P(H ≥ h | G, geometry)`

`P(well) = P(G | s) × P(z_HCWC ≥ z_well | G, geometry)`

and the curve passes through the headline at `h_min` by identity. Each piece of evidence enters
once, in the factor it is evidence about; there is no blending parameter and no rescaling. Where
tab 5.3 shows the well per element, the update of `P(G)` is spread over the elements by the
allocation rule (8.1.4), a presentation that attributes nothing.

Dependence between the judgements. The characteristics that grade `c` are also the
characteristics the published drilled-prospect rankings put first for finding hydrocarbons:
conformance to structure first, flat spots among the most definitive (Roden, Forrest & Holeywell
2012; Nixon, Hallam & Constantine 2018). In this model that evidence about `G` enters through the
index, so an event graded high on `c` is usually placed higher on the index too. Simm (2020)
draws the same line: a high-grade DHI with characteristics consistent with the trap and indicative
of a fluid contact warrants an uplift to the chance; an amplitude or AVO anomaly without them
generally does not. Tab 5.1.3 draws the two judgements against each other (Figure 5.1.3a) with
that pairing as a band, a judgement and not a calibration.

Strong evidence does not make the contact certain. The index moves `P(G)`, at its cap from 0.41
to 0.87 on the shipped prospect; it does not touch the weights, so the contact keeps the spread the
pick, the depth conversion, `c` and the detectability assumptions leave it. Presence can become
highly likely while the contact distribution keeps a finite width, and the two are reported apart.

Guard on the combined ratio. The one published measurement of a combined update is Kjønsberg et
al. (2010), who invert prestack AVO for the joint lithology–fluid distribution at three locations
offshore Norway: a prior of 0.53 from their facies model, posteriors of 0.76, 0.97 and 0.44, so
implied ratios of 2.8, 28.7 and 0.70. Their number carries amplitude and geometry together, so it
bounds the whole update; the tool's guard is 50. It also shows the asymmetry: absence is much
weaker evidence than presence. Their inversion separates hydrocarbon from brine far better than one
hydrocarbon from another, so a flat spot may be a gas–oil contact rather than a hydrocarbon–water
contact; the tool assumes the latter.

Shape of the update. A DHI reshapes the chance curve rather than lifting it: the pick raises the
chance at thresholds near and above the indicated contact and lowers it below. The posterior
median lands on the pick, because an amplitude termination is an estimate of the contact and not
a floor under it, so the chance read there is about half the one read at the assessment minimum.
The element chances on tab 2.0 are untouched by the update (Monigle et al. 2025: the adequacy of
source is determined by the geologic factors alone).

What the DHI can turn out to have been. A DHI is an indication: a seismic response consistent
with hydrocarbons, whose cause is not known until a well is drilled. Its depth is the indicated
contact, carried with the pick and depth-conversion uncertainty of tab 5.1.1; the band between
the P99 and the P1 of that uncertainty is the indicated contact band. The indication can fail as
a hydrocarbon indicator (the trap is dry) or as a contact indicator (hydrocarbons are present and
the response is not their base); the index governs the first, `c` the second. Where the contact
turns out to lie, relative to the band, names the outcome:

| DHI / contact relation | the posterior contact is | the DHI was |
|---|---|---|
| no hydrocarbons | — | a false hydrocarbon indicator |
| above the indicated contact | shallower than the band | not the contact; the response lies in the water leg |
| at the indicated contact, because of it | within the band, the response being its base | the contact |
| at the indicated contact, by coincidence | within the band, the geology having put it there | not the contact |
| below the indicated contact | deeper than the band | not the contact; the response lies inside the column, possibly a gas–oil contact |

The four outcomes on the axis share `P(G | s)` and are read off the updated contact distribution
(5.1.4). The two within the band are separated by the two branches of the likelihood: the first
puts mass in the band because that is what the pick says, the second because the geology by
itself may put the contact near the indicated depth. A well that finds the contact within the band
confirms the DHI in proportion to the first branch's share, which the model reports. The mirror
case, a response absent over a trap that holds hydrocarbons, is the false negative and belongs to
the absent-amplitude observation. The table relates the posterior contact to the observation; what
a well finds depends on its entry depth and is the chance against depth (5.2.4). The difference
between `P(G | s)` and `P(well)` is the mass of the outcomes the well enters beneath, set by `c` and
the geology, not by the index: strong evidence of hydrocarbons raises every outcome on the axis
together and does not move the contact.

Comparison constructions. Two alternative combinations are kept for comparison and teaching, not
as models. The scenario switch, `IF(DHI valid, DHI contact, geological contact)`, moves the
contact and not the chance, cannot narrow the distribution, reports no mechanism, lets the pick
set a contact the limits would not allow, and cannot let the geology revise `c`. The pooled
update, the prior times the pick alone, omits the detectability term. Tab 5.1's diagnostics draw
both beside the headline on the same inputs. Monigle et al. (2025) integrate a DHI score with a
geological prior by the same update used for the index channel; the likelihood defined over
column height, which makes the evidence reshape the contact distribution, is not in that work.

The walkthrough below takes the update apart one term at a time on the current prospect's
numbers. Nothing on it changes a result.

## Empirical benchmarks and censoring

Data. The open dataset used here relating column height to closure height is
Edmundson et al. (2021): 242 NCS discoveries, each with an apex and a spill point picked from
depth-converted maps, published under CC-BY. Earlier compilations report column-height
distributions with no trap geometry. A prospect outside the NCS is compared against Norwegian
rock; the import path for a company's own trap-fill database is the response.

Censoring. A predrill model needs seal capacity `S`, the column the seal could hold; what is
measured is `C = min(S, H)`, with `H` the closure height. Underfilled pools observe `S`. Pools
filled to spill, 111 of 242, observe only `S ≥ H`: the column reached the structural limit, and
the seal's capacity was not tested. For the seal-capacity interpretation the observation is right-censored,
lower-bound information; it is not uninformative. Hood (2019) states the geology: pools controlled by geometric limits
document the minimum column the seal can support and not the upper limit.

Estimator. Fitted as a Type-I Tobit, the closure-height elasticity falls from the published 0.880
to 0.701 and the burial-depth elasticity roughly doubles, the direction physics expects since
seals compact and strengthen with depth; censoring hid the depth signal because deep closures fill
to spill more often. Dropping the censored points does not help: conditioning on `S < H`
manufactures the same positive relationship by truncation. Simulated with seal capacity
independent of closure height, naive OLS returns a slope of 0.580, OLS without the filled-to-spill
points 0.543, and the censored MLE −0.009 against a truth of zero (`tests/test_censoring.py`).
The corrected model reproduces the observed fill-to-spill rate band by band: 45.9 % in the 242
discoveries, 47.2 % predicted by the corrected fit against 32.1 % by the published one, both with
the same spread. The published line's crossing of the 1:1 line is an artefact of fitting a
straight line to a quantity bounded by `C ≤ H`; the observed column is a minimum of two things,
one of which is the axis, and no straight line represents a minimum. A second bias remains: column
height and trap height share the apex pick, so a depth-conversion error manufactures a
relationship no censored estimator can see. The corrected elasticity of about 0.70 is an upper
bound. Graham et al.'s (2015) global 40 % fill-to-spill rate is a population average over closures
below 250 m; on the same basis the NCS gives 54 %, a regional difference, the NCS being
charge-rich.

Use. A benchmark is a prior, not a likelihood. A likelihood is a use, and to act as one the data
must have been observed on this prospect; the record's outcomes were what they were before this
prospect was mapped. Conditioning the record on the prospect's relief and burial gives a
likelihood in form, but the model was built out of relief and burial, so multiplying it in
conditions on the geometry twice. Benchmarks are therefore shown beside the model and never joined.
Where the record is used as a likelihood is on the parameter the prospect shares with the
population, the seal-capacity relationship, as the shrinkage prior on the top-seal limit: empirical
Bayes on a shared parameter. The fit is used against burial depth alone: compaction closing pore
throats has a physical reason to track burial, and a capacity that depended on closure size would
put geometry into a capillary property the engine already handles through `min(capacity, spill)`.

Benchmark blend. An optional weight on tab 6 pulls the model's column distribution toward a
benchmark, quantile by quantile (Vincentization), so the result lies between the two rather than
coming out as two humps. It is a blend and not an update; its default is zero.

Presentation. A benchmark is used as a curve for a closure of the prospect's size: relief is the
family parameter and the axis carries the column. The vertical drop at the right-hand end of every
curve is the filled-to-spill probability mass, a point mass rather than a tail; no smooth
distribution typed into a volumetrics package has one. The families are kept separate: they are
conditioned differently and disagree informatively.

Limitations. The benchmarks cannot be conditioned on a DHI: Graham et al. (2015) state that their
synthesis is for column-height modelling in the absence of direct hydrocarbon indicators, and
Edmundson's discoveries carry no DHI flag and are partly selected by amplitudes. The geological
curve is the like-for-like comparison; the updated one reads as displacement. Every benchmark is
conditioned on discovery, so the record can inform where a contact sits and never the chance of
having one. Two selection effects are uncorrected: discovery-only conditioning, and left-truncation
at the well's reservoir entry, which removes the small-column tail. Stacked, the record is
truncated below and censored above, and both make it look better filled than reality.

Base rates. Edmundson's §5.2 recommends base-rate figures integrated with the geological
assessment, citing Milkov (2017), and gives no method; the part of that recommendation that carries
no risk is their matrix for a prospect of the same dimensions beside what the limits produced. The
matrix is `P(trap fill | discovery)`; moving a chance would need dry holes. The rule usually
attached to base-rate neglect, `b · q / (b · q + (1 − b)(1 − q))`, is symmetric in its two inputs,
which no Bayesian update is, and moves the number when the two already agree; Milkov's (2017)
finding stands, the arithmetic does not. The worked example below shows, on the current prospect,
what multiplying the record in as a likelihood would do.

## Validation, assumptions and limitations

Run checks (tab 4). The checks concern the arithmetic: whether the assessment minimum is zero;
whether the count of realisations behind a tail number is enough to quote it; whether a rerun on
a different seed moves the percentiles; how concentrated the control is on one limit; whether an
elicited correlation matrix was projected, and what was realised against what was asked; and, when
a DHI update exists, the effective sample size and whether the posterior is one interaction behind
the run. A watch means the number needs a sentence beside it when it travels.

Consistency test. The product of the element curves is tested against the direct contact
distribution on every run, in column-height space where the identity is exact and in depth space
where the shared apex makes it approximate. The largest apex effect, the depth-space residual less
the column-space one at one depth, is reported with the two residuals.

Sensitivity. The tornado asks how much each elicited number moves the mean, a different question
from how often a limit controls the contact. Each bar is a conditional mean, the outcome with that
input in its top tenth against its bottom tenth, sliced from the joint sample so the bars respect
the correlations. After a DHI update the geology is sliced with likelihood-weighted means, and the
DHI's typed numbers are varied one at a time as new sets of weights on the same realisations. A bar
resting on fewer than a hundred effective realisations is reported as thin.

Reproduction. The engine reproduces Beha et al.'s (2012) two-fault closure to Monte Carlo error.
The paper's numbers are generated from the engine by `scripts/paper_facts.py` and tested against
the article. The numerical baseline is `docs/BASELINE.md`; the tests are described in
`docs/VALIDATION.md`.

Elicited judgements (no external referent in the tool): the DHI evidence index read against the
reference distributions; `c`; the relative false-positive rate for an absent anomaly; the pick
width; the detectability parameters; the oil–water interfacial tension, 18–28 dyne/cm, flat in
temperature; the well's connection chance.

Modelling choices: limits are sampled and the minimum taken; presence draws are independent;
calculator inputs are independent; `D(h)` is logistic in column height; a spurious event is
equally likely at any depth in the declared contact range; a pick and a penetration are
independent evidence; the floors `1 − c` and `1 − p_connected` keep every depth in play; the barren
trap's chance of showing is tied to the filled trap's; the two DHI channels are factorised; the
gas–water tension follows a temperature line that agrees with methane–brine data.

Limitations. One fluid at a time: seal capacity depends on the density contrast, so a gas column
and an oil column under the same seal differ in height; a mixed-phase prospect is run as separate
cases, and a separate-case answer is not a two-phase answer (a single seal sees gas at the crest
and oil between the two contacts, and the total column is taller than either single-phase answer).
No hydrodynamics or tilted contacts; the contact is hydrostatic and horizontal. No
compartmentalisation. The empirical record is discovery-conditioned, censored above and truncated
below. The seismic likelihoods are elicited, not calibrated; the effective sample size and the
sensitivity to each seismic input are reported for that reason. A proven column in the closure
makes the prospect a discovery, a larger statement than one about depth; the tool uses the depth
only and does not change the element chances.

## References

The bibliography follows, grouped by subject. Full records, with access notes, are in
`docs/REFERENCES.md`.
