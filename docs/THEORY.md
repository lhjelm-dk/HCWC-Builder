# Theory and methods

*The single statement of the method behind the HCWC Distribution Builder. The operational tabs
enter assumptions, show results and name what to check; where a concept is not intuitive they
refer here by section number. The paper (8.2) is the long-form version; the bibliography (8.3)
carries the sources.*

![The model as two rows. The geological model is the prior: the element chances give P(G), the chance an accumulation is present; given an accumulation, the limits compete, the shallowest active one sets the contact and is recorded, and F(h) = P(H ≥ h | G) is the contact distribution read as an exceedance. The DHI is evidence: the evidence index gives a likelihood ratio that updates P(G), and the contact geometry reweights the same realisations; the index never moves the contact, the geometry never moves P(G), and each enters once. Nothing is re-simulated or rescaled: one weighted sample reads the histogram, the percentiles, F(h) and the chance. Each row ends in the probability of meeting the threshold, POS(h) = P(G) × F(h) and its posterior, read at the assessment minimum h_min and at the well; the benchmarks are compared with both contact distributions and never joined. The same figure with the tab each box lives on is Figure 1.0a.](figures/fig0_workflow.svg)

The model as one figure, and the sections that follow its boxes. The geological model is the prior: the accumulation chance `P(G)` (8.1.1); the competing limits and the contact distribution given an accumulation, `HCWC | G` (8.1.2); the reading of that distribution as a chance against a threshold, `POS(h) = P(G) × F(h)` (8.1.3). The DHI is evidence: the evidence index updates `P(G)` (8.1.4); the contact geometry updates `HCWC | G` (8.1.5); the two updated factors give the posterior `POS(h)` from the same weighted realisations (8.1.6). The empirical record is compared beside both contact distributions (8.1.7), and the validation, assumptions and limitations close the method (8.1.8). The construction is Beha, Christensen and Young's (2012) competing trapping-element logic and Hood's (2019, 2024) competition between limits, run as a continuous, correlated Monte Carlo; the per-element depth-dependent chance (8.1.3), the likelihood form of DHI evidence (8.1.5) and the censoring correction to the empirical record (8.1.7) are the parts not found in that literature.

## Accumulation chance P(G)

`G` is the accumulation state: the geological elements work at the crest and there is a hydrocarbon
column of some height. `P(G)` is its chance, the first factor of every probability the tool
reports, and the prior the DHI evidence updates (8.1.4).

The chance has two factors. `P(G)`, the geological accumulation chance, is the product of the
element chances on tab 2.0, each
elicited as play × conditional: the chance that charge arrived, that there is a closure, that
there is reservoir, that retention works, all at the crest. The second factor,
`P(column ≥ h_min | G)`, is the share of realisations whose column reaches the minimum, read off
the contact distribution (8.1.3). Their product is the prospect chance at that threshold.

The two are kept apart because they answer different questions and are moved by different
evidence. A trapping element that fails below the crest, a fault window at 2 300 m or a seal
that holds 150 m, does not reduce the chance of finding hydrocarbons at the well; it reduces the
chance of a deeper contact. Folding such a mechanism into `P(G)` understates the chance and,
because volume is conditioned on it, overstates the volume (Beha et al. 2012). Here those
mechanisms are limits on tab 3.0 and move the contact; only whether an element works at the
crest belongs in the chance.

Nowhere else does a volume criterion enter: `P(G)` is the chance an accumulation is present, of any
size, and the threshold is applied once, through `F(h_min)` (8.1.3). An element chance imported
from another tool must be read the same way, as the chance the element works at the crest and not
as a chance that already carries a minimum volume.

## Competing limits and HCWC | G

A predrill contact is usually entered as a distribution: uniform from apex to spill, or a
three-point estimate from analogues. That distribution carries no connection to the mechanisms
that limit the column, so it cannot be traced to an assumption, cannot say which mechanism a
deeper contact would require, and cannot be corrected after drilling except by moving its
parameters.

The alternative is to state the mechanisms and let the contact follow. Each limit is elicited on
its own terms, a seal as a capacity in metres of column, a spill point as a depth, and the
contact distribution is derived. Its shape is an output. On the shipped prospect it is
right-skewed with a step at the spill, and no one chose that shape.

Limits are sampled, not blended. Averaging a leak into a background column-height distribution
suppresses realisations above the leak and leaves the rest untouched, so the blended
distribution corresponds to no geology, and adding a leak can raise the apparent volume (Hood
2024). Sampling each limit and taking the minimum keeps every realisation a column some mechanism
can produce, at a depth that mechanism can reach. Drawn on one axis, each limit's exceedance
curve flattens at its `P(active)`, and the contact is the lower envelope of the active ones.

A hydrocarbon column is stopped by whichever mechanism acts first: charge runs out, the closure
spills, a fault juxtaposes the reservoir against a carrier, the top or base seal leaks at a
capillary pressure the column exceeds, the seal breaks in tension, the reservoir pinches out.
Each mechanism is a limit with two properties: a probability of being present on this prospect,
and a distribution of the depth or column height at which it acts.

The tool samples every limit in each Monte Carlo realisation, a presence draw and a depth draw,
and takes the shallowest active limit as the hydrocarbon–water contact. The mechanism that set
it is recorded. Ten thousand realisations give a contact distribution, a controlling-mechanism
share for each limit, and both as functions of depth.

Six mechanism families are modelled. Structural spill is a mapped depth. Charge limitation is the
depth at which the accumulated pore volume equals the volume the basin model delivered, found by
integrating the area–depth table. Capillary seal capacity is `h_max = P_c / (Δρ·g)` with
`P_c = 2γ cos θ / r`, a column height that depends on the seal's largest connected pore throat,
the interfacial tension and the density contrast. Seal continuity is a hole in the seal: a
channel, an erosional window, a breaching fault tip. Fault seal is a juxtaposition window, a
depth, or a leak capacity, a column. Mechanical failure is the column at which the crest pressure
reaches the minimum horizontal stress, `H = (S_Hmin − P_p) / (grad_w − grad_h)` (Grant 2020).

Each limit is stated as a column below the apex or as a depth in metres TVDSS, and the engine
converts a depth to a column against the apex drawn in the same realisation. A capacity does not
move when the apex pick moves; a mapped surface does. The distinction matters for the correlation
between apex and spill (below).

Every limit has a probability of being present. A limit with `P(active) = 0.3` applies in three
realisations in ten and is absent in the rest; its exceedance curve flattens at 0.3. At least one
limit is always active, since every prospect has a spill point; the engine refuses a set in which
the column could be unbounded.

The controlling mechanism is recorded per realisation as the index of the shallowest active limit.
Its share over the sample is the ranking on tab 3.1 and 4.1.2b: in most cases two or three limits
set the contact and the rest do not move the answer, so the elicitation effort belongs on those.
The ranking is reported over all realisations and over those meeting the minimum: a limit that
usually fails the prospect outright is under-represented among the survivors because it is the most
severe, which is the selection effect of the empirical record (8.1.7) one level up, so neither view
alone is the answer. The share is not constant down the structure. On the shipped prospect shallow
contacts are seal-controlled and deep contacts pass to fault geometry and spill; tab 4.1.2 draws
this, scaled either as a share of all realisations or as the mechanism mix at each depth.

The precedent is published. Beha et al. (2012) enumerate every combination of trapping elements
sealing or failing, weight each scenario and collapse the result onto leak-point frequencies;
their two-fault example (0.60 / 0.12 / 0.28 at three leak points) is reproduced by this engine to
Monte Carlo error, and is the one external validation the tool has. Grant (2020) publishes the
controlling-limit diagnostic as column height control statistics; Lowry et al. (2005) had chance
against column height two decades earlier. What is not found in that literature is the
continuous, correlated sampling and the per-element curves built from the controller (8.1.3).

Correlation and dependence. Limit depths and capacities can be correlated through a Gaussian
copula, elicited as rank correlations on pairs rather than as a full matrix. An elicited matrix
that is not positive semi-definite is projected onto the nearest one that is, and the projection is
reported. The realised correlation of every sampled pair, apex included, is reported on tab 4's run
checks.

The pair most worth setting is the apex to a depth-stated limit. A spill point and the apex are
picked off the same depth-converted surface, so a depth-conversion error moves both together.
Left independent, a realisation can put the spill above the apex, and the derived closure height
carries a spread that is an artefact: on a 120 m apex uncertainty with a mapped spill, 33 m
independent against 11 m at a correlation of 0.9. The same coupling inflates the published
column-height regression (8.1.7), since column height and trap height share the apex pick.

Correlation applies to depths and capacities only. Whether a limit is present is drawn
independently of everything, including the presence of every other limit. Two faults that leak at
correlated depths are expressible; two faults that stand or fall together are not, and a pair of
rare, severe mechanisms is two independent coin flips. Beha et al. (2012) make the same
assumption. A presence copula is not implemented.

Inside a calculator the inputs are independent uniforms. The seal calculator's temperature,
contact angle, throat radii, densities and tension are sampled independently, though hydrocarbon
density and temperature move together with depth; the mechanical calculator's stress and pore
pressure are independent, though pore-pressure/stress coupling is most of why fracture gradients
rise with overpressure. Independence overstates the spread of a capacity and, for the mechanical
seal, the low tail of the headroom. The correlation editor couples limits with each other and
cannot reach inside a calculator. The seal and charge calculators share a phase and not a fluid:
the seal's density and the charge's formation volume factor are separate draws, and the phase
check on tab 3 is the whole of the coupling. A base seal entered as the top seal offset by the
reservoir thickness has identical inputs and not an identical outcome: sampled independently,
the two fail at different columns in the same realisation, which claims that one shale can be
tight above and leaky below at once; where it is one unit the pair is correlated, and the
default correlation table lists it.

The elements share the apex draw. Every element's contact is `apex + h`, so in depth space the
element curves are dependent even under independent limits, and their product is not the
contact distribution. The consistency test (8.1.8) is exact in column-height space and is run in
both.

## From column height to POS

Four quantities, and the convention that joins them. `H` is the column height, sampled per
realisation as the shallowest active limit; `z_apex` is the apex depth, m TVDSS, sampled in the
same realisation; the contact depth is `z_HCWC = z_apex + H`, depth increasing downward; `z_well`
is the well's reservoir entry depth; `h_min` is the assessment minimum, a column height. `F(h) =
P(H ≥ h | G)` is defined in column-height space and every chance is read there; contact
percentiles and histograms are reported as `z_HCWC`, every percentile the tool prints by one
estimator (Hazen plotting positions on the sorted, weighted sample, P100 the shallowest and P0 the
deepest); the well is read in depth space against
`z_HCWC` realisation by realisation; a depth axis under a column-space curve places it at the
median apex, a drawing convention and not a second model.

A probability of success refers to a stated threshold. In this tool that threshold is the
assessment minimum: the smallest column, `h_min`, that would make the well a discovery. It is
set on tab 2.0 and every chance downstream is read at it; the volume criterion enters here and
nowhere else (8.1.1). The second factor, `F(h_min) = P(H ≥ h_min | G)`, is the share of
realisations whose column reaches the minimum, read off the contact distribution, and the
prospect chance is `POS(h_min) = P(G) × F(h_min)`.

The chance is a curve, not a number. `P(G) × P(column ≥ h | G)` at every `h` is the prospect
chance against threshold (tab 4.1.3), and the headline is that curve read at `h_min`. A chance
quoted without its threshold means nothing; every chance on the operational tabs carries the
threshold it was read at and states whether it includes the element risk.

The controller gives each element its own curve. Taking the shallowest active limit within each
element, its group minimum, gives `P_e(z)`, the chance that element permits a contact deeper
than `z` (tab 4.2). Under independent limits `∏_e P_e(z) = P(contact > z)`, and the product is
checked against the direct distribution on every run (8.1.8). WellVolPOS computes one location
factor, `r = P(z_HCWC > z_well | G)`, and spreads it across the elements by a weighting
rule; the derived curves say which element binds at that depth, which the allocation cannot.
Reservoir enters the depth dependence twice, as a base or pinch-out limit that moves the contact
and as an effectiveness decline (diagenesis, cementation, a net-to-gross trend) that lowers the
chance without moving it; only the first is a competing limit, and conflating them breaks the
consistency identity, so the identity is checked over the contact-controlling elements only.
An element with no limit in the model never controls the contact, and its derived curve is its
element chance unchanged with depth. Spreading one location factor across four elements by a
rule presents the same number differently and adds no information about charge or closure;
the allocation reproduces `P(well)` whatever rule is chosen, and the derived curves can disagree
with it because they carry which element binds at that depth. `r` quoted as a chance of success
overstates the well by `1 / P(G)`.

The contact percentiles the tabs print are conditional on the assessment minimum: they are
taken over the realisations whose column reaches `h_min`, with the same weights as
everything else, because a contact quoted for a discovery is a contact given that there was
one. `F(h)` itself is over every realisation conditional on `G`. The two are one weighted
sample read under two conditions, and the tabs label which.

A well entering at `z_entry` reads three numbers off the same curves: `P(well)`, the chance it
finds hydrocarbons at its entry depth, including the element risk; the geological chance at the
assessment minimum; and their ratio, the location factor.

## DHI evidence index update

One seismic observation carries two kinds of evidence, and each updates one factor (8.1.6). Its
character, how hydrocarbon-like the amplitude looks, is evidence about whether there are
hydrocarbons at all: it is placed on the DHI evidence index and becomes a likelihood ratio on `G`,
which updates `P(G)`. Its geometry is evidence about the contact given `G` (8.1.5).

The DHI evidence-strength model. The DHI evidence index `s` is a conceptual scale used to
represent the strength and polarity of the seismic evidence: 0 is neutral, positive values
increasingly positive evidence, negative values increasingly negative evidence or a missing
expected response. Its numerical values are relative rather than physical; the index has no
units, and a reading of 5 or −5 has no absolute geophysical meaning. The evidence model uses
separate conditional density functions for hydrocarbon-bearing and non-hydrocarbon outcomes,
`f(s | HC)` and `f(s | NoHC)`, the hydrocarbon-bearing and non-hydrocarbon reference
distributions, each a Gaussian on the index given by its 1st and 99th percentiles. They are
conditional densities of the index given the outcome, not probabilities of the outcome given the
index. Their ratio at the observed index is the likelihood ratio, the evidence weight,

Assumptions and limitations of the evidence-strength model. The reference outcomes are
hydrocarbon-bearing and non-hydrocarbon, so `G` is read as an accumulation of any size at the
crest, and a success criterion that carried a volume threshold would be a different quantity;
the tool applies its threshold once, through `F(h_min)`, and never inside `P(G | s)`. The
reference relationship carries no information on contact depth, trap height, spill point or
assessment minimum: the evidence-strength model informs the probability of hydrocarbon presence
and does not predict the HCWC. The depth of the contact is updated only through the
prospect-specific contact geometry (8.1.5). The two channels are two information channels from
one seismic observation, not two independent observations; their overlap is handled by the
factorisation (8.1.6), each channel updating the one factor it is evidence about, and by the
bounds on each.

The likelihood ratio is capped at 10 : 1 either way, Simm's ceiling for one line of fluid-indicator
evidence (Simm & Bacon 2014; Simm 2020): an honest single-channel `LR` rarely exceeds 3, and a
value above 10 sends the assessor back to the inputs. The geometry channel is bounded by its floor
(8.1.5), and the combined update by a guard above the one published measurement (8.1.6).

The volume weight `LR / (LR + 1)`, the weight the amplitude alone would carry against an even
prior, is reported beside `LR` and is not a chance of anything.

An absent anomaly, where one was looked for, enters the chance through its own ratio,
`R_absent = P(absent | G) / P(absent | ¬G) = (1 − d) / (1 − f·d)`, with `d` the mean detectability
over the geological columns (8.1.5) and `f` the chance a barren trap shows an anomaly of the same class,
stated relative to `d`. Tying the false-positive rate to `d` is a modelling choice made for the
behaviour at the ends: where nothing could have shown absence is uninformative, where a barren
trap shows as readily as a filled one likewise, and since `f·d ≤ d` the ratio is never above one.
`f` is elicited; the shipped 0.5 is the maximum-ignorance value and no calibration is known. On
the shipped prospect absence takes the chance from 40 % to 11 %. Within `G` the same absence
reshapes the column (8.1.5).

## DHI geometry update

The geological realisations are a sample from the prior `p(h | G)`. The contact geometry of a seismic observation `D`
enters as a likelihood `L(D | h)` over those realisations, and the posterior is the same sample
with weights `w_j ∝ L(D | h_j)`. That is self-normalised importance sampling and, for this
sample, an exact Bayesian update: nothing is re-simulated, each realisation keeps its controlling
limit, and the prior and posterior are the same realisations, so `F_prior(h)` and `F_post(h)` are
directly comparable. The DHI adds no realisations and moves no sampled limit. Where a sample of
the posterior is needed rather than a curve, for the export, the benchmark comparison and the
posterior window of Figure 5.2.1a, the realisations are drawn by their weights with
replacement: each drawn realisation is one of the run's, limits and controller intact, and a
realisation the evidence favours is drawn often. A scenario mixture, a contact from the pick
with chance `c` and from the geology otherwise, is a different construction: it lets the pick
set a contact the limits would not allow and cannot let the geology revise `c`; it is kept as a
comparison (8.1.6).

The geometry likelihood for a seen anomaly has two factors and a floor:

`L(D | h, G) = c · D(h) · Pick(z | apex + h) + (1 − c) · s`

`D(h)` is the detection function: the chance a column of height `h` produces a mappable anomaly,
near zero below tuning thickness, rising through the resolution limit, flat below a ceiling. The
ceiling is below 1 on purpose; a function reaching certainty would make an absent anomaly
infinitely strong evidence. The logistic form is a modelling choice: a Class III sand can become
less visible when very thick, as the top and base responses separate. `Pick(z | apex + h)` is the
chance the interpreted termination lands at `z` if the contact is at `apex + h`: a normal, PERT
or uniform shape in metres TVDSS, its width the pick error plus the depth conversion, the second
usually larger. Partial conformance, an anomaly bright over the crest and reliably absent below
a depth, is a censored pick: the normal cumulative where a pick's is the density. It is a soft,
censored constraint on the depth of the anomaly's edge and not a forward model of the amplitude
response; both of its branches are probabilities of the event *edge recorded above the cutoff*,
so its spurious branch is the constant 1 where the picked case's is the density `s`, which is
the highest floor the mixture can have and the conservative choice.

`c` is `P(the picked event is the contact | G, contact attributes)`. A flat event can be
lithology, a diagenetic front, fizz gas read as pay or a processing artefact; Roden, Forrest &
Holeywell (2012) list the base or edge of a channel, a low-angle fault, a diagenetic boundary and
a processing artefact as what is most often misread as a flat spot. Monigle et al. (2025) grade
five DHI attributes: anomaly strength, lateral amplitude contrast, fit to structure, amplitude
terminations and the fluid-contact reflection. This tool reads the first two as body attributes,
which bear on whether hydrocarbons are present and are what the evidence index carries, and the last
three as contact attributes, which bear on whether the picked event is the base of the column;
the split is this tool's, not theirs, since their five feed one score. The evidence index of
8.1.4 is where the first two are read. `c` is the second group and carries nothing
of the first: it is conditional on hydrocarbons being present, because every realisation it
weights was drawn on that assumption, and no expression built from the amplitude strength can
supply it. The tab offers it three ways: stated, opening at 0.36; as the geometric mean of
three graded attributes, a heuristic and not a calibration, opening at 0.25 so the two are seen
to differ; or from a DHI score in Monigle et
al.'s (2025) sense through their rule `w = min(2 × score, 0.95)`, calibrated on 400+ drilled DHI
prospects in their database and not on any one basin, and on their five-attribute score rather
than on this tool's evidence index. That rule is the one externally calibrated number on this
quantity, and its ceiling is shared: Hood's (2019) high-confidence contact weight, from the same
company, also stops at 0.95, and the slider's anchors name it. `c` is taken independent of `h`: one number
weights the mixture for every realisation, and the chance that the picked event is the contact
is not made to depend on how tall the column is; the column height enters the valid branch
through `D(h)` only. `s` is the density of a spurious event over the
model's declared contact range, one over the support width, a property of the model and not of
the sample.

The floor is the point of the mixture. Since `Pick ≥ 0`, `L / s ≥ 1 − c`, so the depth channel can
say at most `c / (1 − c)` against any contact depth, however sharply the pick is drawn; at the
shipped 0.36 that is 0.56 : 1. It is Cromwell's rule made operational: a bounded pick shape would
otherwise assign zero below its deepest bound, and no later evidence can revive a zero. Under a
pick the geology considers implausible the posterior median follows the pick while the model
supports it and then falls back to the prior, with the effective sample size returning to the
full count; the model has concluded that the event is probably not a contact rather than that
the contact is where the pick says. Dropping the floor moves the exceedance curve by up to 19
points on the shipped prospect; replacing `D(h)` by a constant moves it by nothing, because every
column above the minimum sits on the ceiling.

An absent anomaly enters within `G` as `1 − D(h)`, largest at small `h`: where the detection
threshold falls inside the geological columns, absence reshapes the contact toward the short
columns that would not have shown. What absence says about the chance is a separate ratio on
`G` (8.1.4).

A well penetration enters the same way. Hydrocarbons proven to `z_hc` and water at `z_w` give
`L = p_connected · [Φ((z − z_hc)/σ) + Φ((z_w − z)/σ) − 1] + (1 − p_connected)`: one tie error
between the well's depths and the mapped surface, and a floor of `1 − p_connected` for the chance
that the well samples a different accumulation. The pick and a penetration are multiplied as
independent evidence.

The effective sample size, Kish's `(Σw)² / Σw²`, reports how many of the realisations the
posterior rests on. A low value does not mean the interpretation is wrong; it means the answer
depends heavily on it and should be presented as such. The ESS reports the geometry channel only:
the character channel updates one number and discards nothing.

The evidence moves the depth distribution, and only through it the mechanism mix. Drawn as
shares of all realisations, the controlling mechanism by depth differs visibly between the
geological and the updated result, because the evidence moves which depths are reached; drawn
as the mix within each depth bin, the two are near-identical, because normalising a bin
conditions on contact depth, which is almost all a DHI knows. The amplitude says roughly where
the contact is, and some mechanisms explain that depth better than others; it is not evidence
about which element failed.

## Combined DHI result

The realisations are conditional on `G`, so a likelihood over them can redistribute probability
among column heights and cannot say whether `G` holds. The model is therefore factorised in two
stages (8.1.4, 8.1.5), and this is a modelling decision rather than a theorem: the geometry is
updated by likelihood weighting within the realisations, all of them conditional on `G`, while the
DHI character provides the separate update to `P(G)`. Each stage is a Bayesian update of the
quantity it names. The whole seismic observation is not modelled generatively across `G` and `h`
together; in such a model the valid-contact branch of the geometry likelihood, which exists only
when `G` holds, would carry some evidence about `G` as well. The tool assigns that evidence to the
character channel and uses the geometry conditionally within `G`, once. A second likelihood ratio
on `P(G)` built from the geometry would count the observation twice.

The prospect chance at a threshold is the product of the two updated factors,
`POS(h_min) = P(G | character) × P(h ≥ h_min | G, geometry)`, and the depth curve
`P(G | character) × F_post(h)` passes through it by identity. Each piece of evidence enters once,
in the factor it is evidence about; there is no blending parameter, and the apparent dependence
between the two channels does not arise in the arithmetic. The dependence that remains is between
the two judgements at elicitation. The characteristics that grade `c`, conformance to structure,
sharp terminations and a fluid-contact reflection, are also the characteristics the published
drilled-prospect rankings put first for finding hydrocarbons: amplitude conformance to structure
first, flat spots among the most definitive (Roden, Forrest & Holeywell 2012; Nixon, Hallam &
Constantine 2018). In this model that evidence about `G` enters through the evidence index, so an
event graded high on `c` is usually placed higher on the index too.
Simm (2020) draws the same line from the other side: a high-grade DHI, with characteristics
consistent with the trap and indicative of a fluid contact, warrants an uplift to the chance; an
amplitude or AVO anomaly without them generally does not. Tab 5.1.3 draws the two judgements
against each other (Figure 5.1.3a) with that pairing as a band, a judgement and not a
calibration, and names the pairings outside it.

Strong evidence does not make the contact certain. The evidence index moves `P(G)`, and at
its cap takes 0.41 to 0.87; it does not touch the weights, so the contact keeps the spread the
pick, the depth conversion, the contact attribution and the detection assumptions leave it.
Hydrocarbon presence can become highly likely while the contact distribution keeps a finite
width, and the two readings are reported apart so that this is visible.

The one published measurement of a combined ratio is Kjønsberg et al. (2010), who invert
prestack AVO for the joint lithology–fluid distribution by Markov chain Monte Carlo at three
locations offshore Norway and report prior and posterior hydrocarbon probabilities: a prior of
0.53 from their facies model, 0.76 at a well, 0.97 at the prospect centre and 0.44 at the
outskirts, so implied ratios of 2.8, 28.7 and 0.70. The strongest bought a factor of 29, against
this tool's guard on the combined ratio of 50, and that location found gas in two layers; the
negative at the outskirts bought 0.70, a factor of 1.4 against where the positive was 29 for.
Their number carries amplitude and geometry together, since the fluid contacts are part of what
their chain samples, so it bounds the whole update rather than one channel, and it shows the
asymmetry: absence is much weaker evidence than presence. Their inversion separates hydrocarbon
from brine far better than one hydrocarbon from another: oil sand and gas sand overlap in
acoustic impedance and Vp/Vs, and at the prospect centre the posterior put 0.03 on wet and then
0.45 on gas alone against 0.46 on gas and oil, with the oil and gas volumes strongly
anti-correlated, the seismic pinning the total and trading the split. The consequence for the
pick is that a flat spot may be a gas–oil contact rather than a hydrocarbon–water contact; the
tool assumes the latter, and on a two-phase prospect the amplitude alone does not settle which.

A DHI reshapes the chance curve rather than lifting it: the pick raises the chance at
thresholds near and above the picked contact and lowers it below, and the curves cross where
that changes. The posterior median lands on the pick, because an amplitude termination is an
estimate of the contact and not a floor under it, so the chance read there is about half the
one read at the assessment minimum.

A DHI cannot re-attribute risk between elements. Two controlling-mechanism readings are reported:
what controls the contact under the geological prior, and which mechanisms are more frequent among
the realisations the evidence favours. The second is not the DHI saying which element failed; it is
which mechanisms are more consistent with the contact depths the evidence favours. Given the
prospect failed, which element failed, a fluid indicator cannot say; the element chances on tab 2.0
are untouched by the update (Monigle et al. 2025: the adequacy of source is determined by the
geologic factors alone). Given it worked and the contact is where the amplitude says, which
mechanism stopped it there, the DHI can answer, because the controlling limit is coupled to the
contact depth. That is why the controller is recorded. The well reading given the DHI is the
same product read at the entry depth, `P(well) = P(G | s) × P(z_HCWC > z_well | G, geometry)`,
on tab 5.2.4 and tab 5.3.4 alike; where tab 5.3.4 shows it per element, the update of `P(G)`
by the index is spread over the elements by the allocation rule (8.1.3), a presentation that
attributes nothing.

Why a well at the picked contact does not read `P(G | s)`. A success rate is a count of one
event, and `P(G | s)` counts hydrocarbons present in the trap: a well at the crest finds them
whenever they are there, so at the crest the two numbers agree. A well 180 m down structure
needs a second thing, a column at least 180 m tall, and the chance of that is not one. On the
shipped prospect, evidence index +5 and `c = 0.36`, `P(G | s)` is 0.467 and a well at 2 230 m,
20 m above the 2 250 m pick, reads 0.361. Of a thousand such prospects, 533 have no
hydrocarbons, 107 have hydrocarbons with the contact above 2 230 m, and 361 have hydrocarbons
at the well. The 107 are the prospects on which the flat event was not the contact and the
real contact sits where the geology alone put it, above 2 230 m in 43 % of the geological
realisations. Their number is set by `c`: the pick alone puts 0.98 on a contact below 2 230 m
and the geology 0.57, and the posterior sits between them at 0.77, the mixture at the
posterior attribution of 0.49 (the pick lands where the geology expected a contact, which
raises 0.36 to 0.49). With `c = 0.99` the 107 become 10 and the well reads 0.458, the pick's
own 2 % above 2 230 m accounting for the rest. A database success rate for prospects with this
prior and this evidence is therefore compared with `P(G | s)` if its wells were drilled where a
column of any size is found, and with `P(G | s) × F_post` at the entry depth if they were
drilled at the flat event; the one number cannot serve both. The pairing matters as well: an
event known to be the contact is a fluid-contact reflection, which is strong evidence of
hydrocarbons and belongs high on the index, so a marginal index with `c` near one is the
off-band pairing Figure 5.1.3a marks.

The scenario switch, `IF(DHI valid, DHI contact, geological contact)`, is the older method and
Hood's rule: merge late, never blend into the input distribution. It moves the contact and not
the chance, cannot narrow the distribution, and reports no mechanism. Its one parameter, whether
the picked event is the contact, was an unlabelled parameter of a model never written down; the
likelihood form writes it down as the floor (8.1.5) and needs two numbers a geophysicist can
state instead of one nobody can. Tab 5.1's diagnostics compare the two on the same value, since
a comparison run on a different one would be a comparison against something else.

Monigle et al. (2025) integrate a DHI score with a geological prior by the same Bayesian update
used for the character channel, and treat an absent anomaly as negative evidence. What is not
found in that work is the likelihood defined over column height, which is what makes the
evidence reshape the contact distribution and the depth-dependent risk rather than only the
chance.

The walkthrough below takes the update apart one term at a time on the current prospect's
numbers. Nothing on it changes a result.

## Empirical benchmarks and censoring

The one openly redistributable dataset relating column height to closure height is Edmundson et
al. (2021): 242 NCS discoveries, each with an apex and a spill point picked from depth-converted
maps, published under CC-BY. A search for a second (28 August 2026) found none, for a structural
reason: closure height needs an apex and a spill picked off 3D per field, months of interpretation
rather than a database query. The earlier compilations report column-height distributions with
no trap geometry. A prospect outside the NCS is therefore compared against Norwegian rock, and
the import path, a company's own trap-fill database, is the response.

The published regression measures the wrong quantity. What a predrill model needs is seal capacity
`S`, the column the seal could hold; what is measured is `C = min(S, H)`, with `H` the closure
height. Underfilled pools observe `S`. Pools filled to spill, 111 of 242, observe only `S ≥ H`:
they are right-censored, and the seal's capacity was never tested. Hood (2019) states the geology,
pools controlled by geometric limits "document the minimum column that the seal can support but not
the upper limit"; the statistical consequence had not been carried into the published estimators.
Fitted as a Type-I Tobit, the closure-height elasticity falls and the burial-depth elasticity
roughly doubles, the direction physics expects since seals compact and strengthen with depth;
censoring hid the depth signal because deep closures fill to spill more often. Dropping the
censored points does not help: conditioning on `S < H` manufactures the same positive relationship
by truncation. Simulated with seal capacity independent of closure height and 242 points to match,
naive OLS returns a slope of 0.580, OLS after dropping the filled-to-spill points 0.543, and the
censored MLE −0.009 against a truth of zero, at every correlation tested
(`tests/test_censoring.py`). The corrected model reproduces the observed fill-to-spill rate band by
band, which is what validates its form: in the 242 discoveries 45.9 % fill to spill, and drawing a
column for every discovery at its own closure height and burial depth the corrected fit predicts
47.2 % and the published fit 32.1 %, both given the same spread so that only the mean function
differs. The published estimator overstates the closure-height elasticity, 0.880 against 0.701
corrected, so its family fans out too far and goes the opposite way at the two ends: at 2 500 m
burial it under-fills small closures (P50 82 m of a 100 m closure against 100 m corrected, 37 %
filling to spill against 59 %) and over-fills the largest (514 m of an 800 m closure against 490
m). Graham et al.'s (2015) global 40 % fill-to-spill rate is a population average over closures
below 250 m, not a value at 250 m; on the same basis the NCS gives 54 %, a regional difference
rather than a discrepancy, since the NCS is charge-rich, which is Graham's own warning against
global benchmarks without trap-specific geology.

The published regression's crossing of the 1:1 line is an artefact of fitting a straight line
to a quantity bounded by `C ≤ H`: it predicts, at small closures, a column the data cannot
contain, and its intercept says a closure of zero height holds a column. Forcing the line
through the origin fixes the bound and leaves the wrong model, because a line through the origin
says the fill fraction is constant, and in the data the median fill fraction declines with
closure height. The observed column is `min(S, H)`, a minimum of two things, one of which is the
x-axis, and no straight line represents a minimum; the censored fit is a different model rather
than a tidied regression, and the declining fill fraction is the signature of capacity growing
more slowly than closure, the `h^0.70` in the corrected line. The corrected line's own crossing
is a prediction: above it the model says the closure fills, and the observed fill-to-spill rate
changes there. A second bias remains: column height and trap height share the apex pick, so
a depth-conversion error manufactures a relationship no censored estimator can see. The
corrected elasticity of about 0.70 is an upper bound.

A benchmark is a prior, not a likelihood. A prior and a likelihood are the same kind of object,
functions of the unknown; a likelihood is a use, and to act as one the data must have been
observed on this prospect. The record's outcomes were what they were before this prospect was
mapped. Conditioning the record on the prospect's relief and burial gives a likelihood in form,
but the model was built out of relief and burial, the spill point is the relief, so multiplying
it in conditions on the geometry twice. The two are combined by a stated weight, defaulting to
zero, as quantiles rather than densities, so the result lies between them. Where a likelihood does
live in the dataset is its outcomes as evidence about the parameters the prospect shares with the
population, the seal-capacity relationship, which is the shrinkage prior on the top-seal limit:
empirical Bayes on a shared parameter, not an update of one prospect with other prospects'
answers. The fit is used against burial depth alone. Its trap-height term is real in the data,
but a capacity that depended on closure size would put geometry into a capillary property, and
the engine already takes `min(capacity, spill)`; compaction closing pore throats is the part
with a physical reason to track burial.

The benchmarks cannot be conditioned on a DHI. Graham et al. (2015) state in their opening
sentence that their synthesis is for column-height modelling "in the absence of direct
hydrocarbon indicators (DHIs) or known fill controls"; Edmundson's discoveries carry no DHI flag
and, being discoveries, are partly selected by other people's amplitudes, enriched in long
columns because that is what detectability does. A posterior judged against them counts the DHI
twice. The geological curve is the like-for-like comparison; the updated one reads as
displacement.

A benchmark is used as a curve for a closure of the prospect's size: relief is the family
parameter, and the axis carries the column, so each curve answers, given a closure of this
relief, how likely is a column of at least `x`. Relief on the axis would collapse each curve to a
point, and the built prospect could not be drawn on it. The vertical drop at the right-hand end
of every curve is the filled-to-spill probability mass, a point mass rather than a tail; no
smooth distribution typed into a volumetrics package has one, and squashing it into a lognormal
is the censoring error arriving one step later in the workflow. The families are kept separate
rather than merged into one empirical prior: they are conditioned differently and disagree
informatively, and a benchmark that agrees with the others carries less information than one
that does not. Combined with the model, the two are averaged as quantiles rather than mixed as
densities, so the answer lies between them rather than coming out as two humps.

The comparison is a sanity check, not a score. A prospect can be optimistic on good grounds: a
better seal than the average NCS closure, or a charge system that fills reliably, is a defensible
belief where the evidence for it can be named. Every benchmark is conditioned on discovery, so part
of "optimistic against the record" is a statement about which wells were written down. Every trap
in the record had hydrocarbons in it, so the record can inform where a contact sits and never the
chance of having one. Two selection effects remain uncorrected in every analysis: discovery-only
conditioning, and left-truncation at the well's reservoir entry, which removes the small-column
tail. Stacked, the record is truncated below and censored above, and both push it to look better
filled than reality.

Base rates are shown beside the model and not merged. Edmundson's §5.2 recommends base-rate
figures integrated with the geological assessment, citing Milkov (2017), and gives no method;
the part of that recommendation that carries no risk is their matrix for a prospect of the same
dimensions beside what the limits produced. The matrix is `P(trap fill | discovery)`: used
against the chance it would condition on success, and moving a chance would need a dataset
containing dry holes. A cell of a few dozen discoveries is a thin basis, and letting it reshape
a ten-thousand-realisation mechanistic model would be a strong move on weak evidence; a
disagreement points back to the limit that causes it. Of the paper's own claims, the dataset,
closure height as a control, the message that one predrill distribution does not fit all
prospects, and the band-by-band calibration stand; burial depth as the weaker control does not,
the magnitude of the closure-height control is overstated and still an upper bound, and the
four trap-fill bins cannot be read together as a column-height distribution, since the 100 %
bin is a censoring rate and not a fill outcome like the other three. Used as a predrill prior
the record is optimistic at both ends. The rule usually attached to base-rate
neglect, `b·q / (b·q + (1−b)(1−q))`, is symmetric in its two inputs, which no Bayesian update is,
and moves the number when the two already agree: it is a Fagan nomogram with the base rate
entered on the axis meant for a test's accuracy. Milkov's (2017) finding stands; the arithmetic
does not.

The worked example below shows, on the current prospect, what multiplying the record in as a
likelihood would do: a spread tighter than the model's own after consulting a vaguer source,
which says the two are not independent evidence.

## Validation, assumptions and limitations

The run checks on tab 4 concern the arithmetic, not the geology. They report whether the
assessment minimum is zero, so that every realisation counts as a success; whether the count of
successes behind a tail number is enough to quote it; whether a rerun on a different seed moves
the percentiles; how concentrated the control is on one limit; whether an elicited correlation
matrix was projected, and what was realised against what was asked for; and, when a DHI update
exists, the effective sample size behind it and whether the posterior is one interaction behind
the run. A watch means the number needs a sentence beside it when it travels.

The decomposition is tested on every run: the product of the element curves against the direct
contact distribution, in column-height space where the identity is exact and in depth space
where the shared apex makes it approximate. A residual near zero says the elements behave
independently and the derived per-element chances are consistent with the contact they came
from.

The tornado asks how much each elicited number moves the mean, a different question from how often
the limit controls the contact: a limit can set the contact in most realisations and be worth no
effort, because it always applies at nearly the same depth. Each bar is a conditional mean, the
average outcome with that input in its top tenth against its bottom tenth, sliced from the joint
sample so the bars respect the correlations. A limit has two kinds of bar, where it applies and
whether it is present, and the longer says whether the question is a depth or a probability. The
mean rather than the median, because a volume is built from the mean and a median can sit still
while the tail moves. After a DHI update the sensitivity keeps two kinds of input apart. The
geology varies realisation by realisation and is sliced as before, with the means weighted by
likelihood; the DHI's own numbers are single typed values, so their influence is found by moving
each one and recomputing, the pick sigma halved and doubled, the picked contact by half a sigma,
the detection parameters across the span an assessor cannot pin down. Each variation is a new set
of weights on the same realisations, with no second Monte Carlo. Where a typed DHI number moves the
answer further than the geology does, the posterior is a statement about the seismic assumptions
rather than about the prospect; the pick sigma and the detection ceiling are usually the least
defensible numbers. Reweighting also changes which limits the answer is sensitive to, so the
geological ranking after the update can differ from the one before it. The sensitivity figures
state their support. A tornado bar resting on fewer than a hundred effective realisations is
reported as thin rather than drawn as though it were as well supported as the rest.

The engine reproduces the one published case, Beha et al.'s (2012) two-fault closure, to Monte
Carlo error. The numerical audit of 14 September 2026 (`docs/AUDIT_2026-09-14.md`) probed the
core end to end: the copula delivers the correlation asked for, the derived element chance
reproduces the direct one, the DHI chain's two factors are updated once each, and every finding
is fixed and tested or recorded as acceptable. The paper's numbers are regenerated from the
engine by script and tested against the prospect they were drawn from.

Judgements with no external referent in the tool: the DHI evidence index, read against the two
reference distributions the tool ships with, themselves editable; `c`, the contact-attribute
judgement, typed or from three graded attributes by a heuristic rule; the relative false-positive
rate for an absent anomaly; the oil–water interfacial tension, 18–28 dyne/cm, flat in temperature;
the well's connection chance.

Modelling choices: the detection function is logistic in column height; a flat event that is
not the contact is equally likely at any depth in the model's contact range; the pick and a
penetration are independent evidence; the floors `1 − c` and `1 − p_connected` keep every depth
in play; the barren trap's chance of showing is tied to the filled trap's; the gas–water tension
follows a temperature line of unknown provenance that agrees with methane–brine data.

Things the model does not do. One fluid at a time: seal capacity depends on the density contrast,
so a gas column and an oil column under the same seal differ in height, and a mixed-phase prospect
needs the gas cap and the oil leg limited by different capacities with a gas–oil contact between
them; phases are run as separate cases. A separate-case answer is not a two-phase answer, and the
difference is not conservative: a single seal sees gas at the crest and oil on the flanks between
the two contacts, the oil leg is unchanged by the gas above it, and the total column is taller than
either single-phase answer rather than between them. On the shipped defaults that is roughly 150 m
of oil under 130 m of gas, against 150 m pure oil or 183 m pure gas; spill and every other limit
still apply. The numbers follow from the physics in `hcwc/core/seals.py`; the tool does not compute
them, and the charge-driven route to a gas–oil contact in `hcwc.core.charge` is not wired to a
control either (docs/PLAN_DUAL_PHASE_SEAL.md). No hydrodynamics or tilted contacts; the contact is
hydrostatic and horizontal, and remigration and hydraulic reconfiguration are absent for the same
reason (Grant 2020 includes the gradient). No compartmentalisation; a compartmentalised trap needs
a contact per compartment. Presence draws are independent (8.1.2). Calculator inputs are
independent (8.1.2). The empirical record is discovery-conditioned, censored above and truncated
below (8.1.7). The seismic likelihoods are elicited, not calibrated, which is why the effective
sample size and the sensitivity to each seismic input are reported: when a typed assumption moves
the contact further than the geology does, that is a finding about the assumption. A proven column
in the closure makes the prospect a discovery, which is a larger statement than one about depth;
the tool uses the depth only and does not change the element chances.