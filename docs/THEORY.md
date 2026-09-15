# Theory and methods

*The single statement of the method behind the HCWC Distribution Builder. The operational tabs
enter assumptions, show results and name what to check; where a concept is not intuitive they
refer here by section number. The paper (8.2) is the long-form version; the bibliography (8.3)
carries the sources.*

## The model in one page

A hydrocarbon column is stopped by whichever mechanism acts first: charge runs out, the closure
spills, a fault juxtaposes the reservoir against a carrier, the top or base seal leaks at a
capillary pressure the column exceeds, the seal breaks in tension, the reservoir pinches out.
Each mechanism is a limit with two properties: a probability of being present on this prospect,
and a distribution of the depth or column height at which it acts.

The tool samples every limit in each Monte Carlo realisation, a presence draw and a depth draw,
and takes the shallowest active limit as the hydrocarbon–water contact. The mechanism that set
it is recorded. Ten thousand realisations give a contact distribution, a controlling-mechanism
share for each limit, and both as functions of depth.

Probability of success is a reading of that distribution at a threshold: the assessment minimum,
the smallest column that counts as a discovery. `POS = P(G) × P(column ≥ h_min | G)`, where
`P(G)` is the chance the geological elements work at the crest and the second factor is read off
the contact distribution. Chance and volume come off the same curve.

Evidence about the contact, a seismic amplitude with a picked termination or a well penetration,
enters as a likelihood over the realisations and reweights them. The amplitude's character
updates `P(G)`; its geometry updates the contact distribution. Nothing is re-simulated, the
controlling-mechanism bookkeeping survives, and the effective sample size says how far the
evidence displaced the geology.

The construction is Beha, Christensen and Young's (2012) competing trapping-element logic and
Hood's (2019, 2024) competition between limits, run as a continuous, correlated Monte Carlo. The
per-element depth-dependent chance (8.1.3), the likelihood form of DHI evidence (8.1.5) and the
censoring correction to the empirical record (8.1.7) are the parts not found in that literature.

## Why HCWC is an output, not a generic distribution

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

## Competing geological limits

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
between apex and spill (8.1.4).

Every limit has a probability of being present. A limit with `P(active) = 0.3` applies in three
realisations in ten and is absent in the rest; its exceedance curve flattens at 0.3. At least one
limit is always active, since every prospect has a spill point; the engine refuses a set in which
the column could be unbounded.

The controlling mechanism is recorded per realisation as the index of the shallowest active
limit. Its share over the sample is the ranking on tab 3.1 and 4.1.5: in most cases two or three
limits set the contact and the rest do not move the answer, so the elicitation effort belongs on
those. The share is not constant down the structure. On the shipped prospect shallow contacts
are seal-controlled and deep contacts pass to fault geometry and spill; tab 4.1.2 draws this,
scaled either as a share of all realisations or as the mechanism mix at each depth.

The precedent is published. Beha et al. (2012) enumerate every combination of trapping elements
sealing or failing, weight each scenario and collapse the result onto leak-point frequencies;
their two-fault example (0.60 / 0.12 / 0.28 at three leak points) is reproduced by this engine to
Monte Carlo error, and is the one external validation the tool has. Grant (2020) publishes the
controlling-limit diagnostic as column height control statistics; Lowry et al. (2005) had chance
against column height two decades earlier. What is not found in that literature is the
continuous, correlated sampling and the per-element curves built from the controller (8.1.3).

## HCWC, column height and POS

A probability of success refers to a stated definition of success. In this tool that definition
is the assessment minimum: the smallest column, or the deepest contact, that would make the well
a discovery. It is set on tab 2.0 and every chance downstream is read at it.

The chance has two factors. `P(G)` is the product of the element chances on tab 2.0, each
elicited as play × conditional: the chance that charge arrived, that there is a closure, that
there is reservoir, that retention works, all at the crest. The second factor,
`P(column ≥ h_min | G)`, is the share of realisations whose column reaches the minimum, read off
the contact distribution. Their product is the prospect chance at that threshold.

The two are kept apart because they answer different questions and are moved by different
evidence. A trapping element that fails below the crest, a fault window at 2 300 m or a seal
that holds 150 m, does not reduce the chance of finding hydrocarbons at the well; it reduces the
chance of a deeper contact. Folding such a mechanism into `P(G)` understates the chance and,
because volume is conditioned on it, overstates the volume (Beha et al. 2012). Here those
mechanisms are limits on tab 3.0 and move the contact; only whether an element works at the
crest belongs in the chance.

The chance is a curve, not a number. `P(G) × P(column ≥ h | G)` at every `h` is the prospect
chance against threshold (tab 4.1.3), and the headline is that curve read at `h_min`. A chance
quoted without its threshold means nothing; every chance on the operational tabs carries the
threshold it was read at and states whether it includes the element risk.

The controller gives each element its own curve. Taking the shallowest active limit within each
element, its group minimum, gives `P_e(z)`, the chance that element permits a contact deeper
than `z` (tab 4.2). Under independent limits `∏_e P_e(z) = P(contact > z)`, and the product is
checked against the direct distribution on every run (8.1.8). WellVolPOS computes one location
factor, `r = P(contact > z_entry | success)`, and spreads it across the elements by a weighting
rule; the derived curves say which element binds at that depth, which the allocation cannot.
Reservoir enters the depth dependence twice, as a base or pinch-out limit that moves the contact
and as an effectiveness decline that lowers the chance without moving it; only the first is a
competing limit.

A well entering at `z_entry` reads three numbers off the same curves: `P(well)`, the chance it
finds hydrocarbons at its entry depth, including the element risk; the geological chance at the
assessment minimum; and their ratio, the location factor.

## Correlation and dependence

Limit depths and capacities can be correlated through a Gaussian copula, elicited as rank
correlations on pairs rather than as a full matrix. An elicited matrix that is not positive
semi-definite is projected onto the nearest one that is, and the projection is reported. The
realised correlation of every sampled pair, apex included, is reported on tab 4's run checks.

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

## DHI updating

The geological realisations are a sample from the prior `p(h | G)`. A seismic observation `D`
enters as a likelihood `L(D | h)` over those realisations, and the posterior is the same sample
with weights `w_j ∝ L(D | h_j)`. That is self-normalised importance sampling and, for this
sample, an exact Bayesian update: nothing is re-simulated, each realisation keeps its controlling
limit, and the prior and posterior are the same realisations, so `F_prior(h)` and `F_post(h)` are
directly comparable.

The realisations are conditional on `G`, so a likelihood over them can redistribute probability
among column heights and cannot say whether `G` holds. The observation carries two kinds of
evidence, and each updates one factor:

- Character, how hydrocarbon-like the amplitude looks, is a likelihood ratio on `G`. It updates
  `P(G)` through the two-state form `P(G | s) = R·P(G) / (R·P(G) + 1 − P(G))` (Simm 2016; E-POS).
  `R` is the ratio of two elicited curves on a strength axis, a hydrocarbon-bearing and a
  non-hydrocarbon population, read at the prospect's placing. The axis has no units; what carries
  meaning is where the prospect sits relative to the two populations as drawn.
- Geometry, where the picked event terminates, is a likelihood over `h` within `G`. It updates
  the contact distribution (8.1.6).

The prospect chance at a threshold is the product of the two updated factors,
`POS(h_min) = P(G | character) × P(h ≥ h_min | G, geometry)`, and the depth curve
`P(G | character) × F_post(h)` passes through it by identity. Each piece of evidence enters once,
in the factor it is evidence about; there is no blending parameter, and the apparent dependence
between the two channels does not arise in the arithmetic. The dependence that remains is between
the two judgements at elicitation, since body and contact attributes both improve with impedance
contrast (Monigle et al. 2025).

Each channel is bounded. The character ratio is capped at 10 : 1 either way, Simm's ceiling for
one line of fluid-indicator evidence: an honest single-channel `R` rarely exceeds 3, and a value
above 10 sends the assessor back to the inputs. The geometry channel is bounded by its floor
(8.1.6). The one published measurement of a combined ratio is Kjønsberg et al. (2010), who invert
prestack AVO by Markov chain Monte Carlo at three locations offshore Norway: the strongest bought
a factor of 29 and that location found gas; the negative at the outskirts bought 0.70. Their
number carries amplitude and geometry together, so it bounds the whole update rather than one
channel, and it shows the asymmetry: absence is much weaker evidence than presence.

The effective sample size, Kish's `(Σw)² / Σw²`, reports how many of the realisations the
posterior rests on. A low value does not mean the interpretation is wrong; it means the answer
depends heavily on it and should be presented as such. The ESS reports the geometry channel only:
the character channel updates one number and discards nothing.

A DHI cannot re-attribute risk between elements. Given the prospect failed, which element
failed, a fluid indicator cannot say; the element chances on tab 2.0 are untouched by the update
(Monigle et al. 2025: the adequacy of source is determined by the geologic factors alone). Given
it worked and the contact is where the amplitude says, which mechanism stopped it there, the DHI
can answer, because the controlling limit is coupled to the contact depth. That is why the
controller is recorded.

The scenario switch, `IF(DHI valid, DHI contact, geological contact)`, is the older method and
Hood's rule: merge late, never blend into the input distribution. It moves the contact and not
the chance, cannot narrow the distribution, and reports no mechanism. Its one parameter, whether
the picked event is the contact, lives inside the likelihood here as the floor (8.1.6). Tab 5.2's
diagnostics compare the two.

Monigle et al. (2025) integrate a DHI score with a geological prior by the same Bayesian update
used for the character channel, and treat an absent anomaly as negative evidence. What is not
found in that work is the likelihood defined over column height, which is what makes the
evidence reshape the contact distribution and the depth-dependent risk rather than only the
chance.

The walkthrough below takes the update apart one term at a time on the current prospect's
numbers. Nothing on it changes a result.

## Detection, contact attribution and absence

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
a depth, is a censored pick: the normal cumulative where a pick's is the density.

`c` is `P(the picked event is the contact | G, contact attributes)`. A flat event can be
lithology, a diagenetic front, fizz gas read as pay or a processing artefact. Monigle et al.
(2025) separate DHI attributes into body attributes, anomaly strength and lateral contrast, which
bear on whether hydrocarbons are present and are what the strength axis grades, and contact
attributes, fit to structure, terminations and the fluid-contact reflection, which bear on
whether the picked event is the base of the column. `c` is the second group and carries nothing
of the first: it is conditional on hydrocarbons being present, because every realisation it
weights was drawn on that assumption, and no expression built from the amplitude strength can
supply it. The tab offers it typed, opening at 0.36, or as the geometric mean of three graded
attributes, a heuristic and not a calibration. `s` is the density of a spurious event over the
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
columns that would not have shown. On the chance it enters through its own ratio,
`R_absent = P(absent | G) / P(absent | ¬G) = (1 − d) / (1 − f·d)`, with `d` the mean detectability
over the geological columns and `f` the chance a barren trap shows an anomaly of the same class,
stated relative to `d`. Tying the false-positive rate to `d` is a modelling choice made for the
behaviour at the ends: where nothing could have shown absence is uninformative, where a barren
trap shows as readily as a filled one likewise, and since `f·d ≤ d` the ratio is never above one.
`f` is elicited; the shipped 0.5 is the maximum-ignorance value and no calibration is known. On
the shipped prospect absence takes the chance from 40 % to 11 %.

A well penetration enters the same way. Hydrocarbons proven to `z_hc` and water at `z_w` give
`L = p_connected · [Φ((z − z_hc)/σ) + Φ((z_w − z)/σ) − 1] + (1 − p_connected)`: one tie error
between the well's depths and the mapped surface, and a floor of `1 − p_connected` for the chance
that the well samples a different accumulation. The pick and a penetration are multiplied as
independent evidence.

## Empirical benchmarks and censoring

The one openly redistributable dataset relating column height to closure height is Edmundson et
al. (2021): 242 NCS discoveries, each with an apex and a spill point picked from depth-converted
maps, published under CC-BY. A search for a second (28 August 2026) found none, for a structural
reason: closure height needs an apex and a spill picked off 3D per field, months of interpretation
rather than a database query. The earlier compilations report column-height distributions with
no trap geometry. A prospect outside the NCS is therefore compared against Norwegian rock, and
the import path, a company's own trap-fill database, is the response.

The published regression measures the wrong quantity. What a predrill model needs is seal
capacity `S`, the column the seal could hold; what is measured is `C = min(S, H)`, with `H` the
closure height. Underfilled pools observe `S`. Pools filled to spill, 111 of 242, observe only
`S ≥ H`: they are right-censored, and the seal's capacity was never tested. Hood (2019) states the
geology; the statistical consequence had not been carried into the published estimators. Fitted
as a Type-I Tobit, the closure-height elasticity falls and the burial-depth elasticity roughly
doubles, the direction physics expects since seals compact and strengthen with depth; censoring
hid the depth signal because deep closures fill to spill more often. Dropping the censored points
does not help: conditioning on `S < H` manufactures the same positive relationship by truncation.
The corrected model reproduces the observed fill-to-spill rate band by band, which is what
validates its form. A second bias remains: column height and trap height share the apex pick, so
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

The benchmarks cannot be conditioned on a DHI. Graham et al. (2015) state that their synthesis
is for the case without direct hydrocarbon indicators; Edmundson's discoveries carry no DHI flag
and, being discoveries, are partly selected by other people's amplitudes, enriched in long
columns because that is what detectability does. A posterior judged against them counts the DHI
twice. The geological curve is the like-for-like comparison; the updated one reads as
displacement.

The comparison is a sanity check, not a score. Every benchmark is conditioned on discovery, so
part of "optimistic against the record" is a statement about which wells were written down.
Every trap in the record had hydrocarbons in it, so the record can inform where a contact sits
and never the chance of having one. Two selection effects remain uncorrected in every analysis:
discovery-only conditioning, and left-truncation at the well's reservoir entry, which removes the
small-column tail. Stacked, the record is truncated below and censored above, and both push it to
look better filled than reality.

Base rates are shown beside the model and not merged. The rule usually attached to base-rate
neglect, `b·q / (b·q + (1−b)(1−q))`, is symmetric in its two inputs, which no Bayesian update is,
and moves the number when the two already agree: it is a Fagan nomogram with the base rate
entered on the axis meant for a test's accuracy. Milkov's (2017) finding stands; the arithmetic
does not.

The worked example below shows, on the current prospect, what multiplying the record in as a
likelihood would do: a spread tighter than the model's own after consulting a vaguer source,
which says the two are not independent evidence.

## Validation and numerical checks

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

The sensitivity figures state their support. A tornado bar resting on fewer than a hundred
effective realisations is reported as thin rather than drawn as though it were as well supported
as the rest.

The engine reproduces the one published case, Beha et al.'s (2012) two-fault closure, to Monte
Carlo error. The numerical audit of 14 September 2026 (`docs/AUDIT_2026-09-14.md`) probed the
core end to end: the copula delivers the correlation asked for, the derived element chance
reproduces the direct one, the DHI chain's two factors are updated once each, and every finding
is fixed and tested or recorded as acceptable. The paper's numbers are regenerated from the
engine by script and tested against the prospect they were drawn from.

## Assumptions and limitations

Elicited judgements, which have no external referent in the tool: the strength axis and the two
populations on it; `c`, the contact-attribute judgement, typed or from three graded attributes by
a heuristic rule; the relative false-positive rate for an absent anomaly; the oil–water
interfacial tension, 18–28 dyne/cm, flat in temperature; the well's connection chance.

Modelling choices: the detection function is logistic in column height; a flat event that is
not the contact is equally likely at any depth in the model's contact range; the pick and a
penetration are independent evidence; the floors `1 − c` and `1 − p_connected` keep every depth
in play; the barren trap's chance of showing is tied to the filled trap's; the gas–water tension
follows a temperature line of unknown provenance that agrees with methane–brine data.

Things the model does not do. One fluid at a time: seal capacity depends on the density contrast,
so a gas column and an oil column under the same seal differ in height, and a mixed-phase
prospect needs the gas cap and the oil leg limited by different capacities with a gas–oil contact
between them; phases are run as separate cases. A separate-case answer is not a two-phase answer,
and the difference is not conservative: a single seal sees gas at the crest and oil on the flanks
between the two contacts, the oil leg is unchanged by the gas above it, and the total column is
taller than either single-phase answer rather than between them. On the shipped defaults that is
roughly 150 m of oil under 130 m of gas, against 150 m pure oil or 183 m pure gas; spill and
every other limit still apply. The numbers follow from the physics in `hcwc/core/seals.py`; the
tool does not compute them, and the charge-driven route to a gas–oil contact in
`hcwc.core.charge` is not wired to a control either (docs/PLAN_DUAL_PHASE_SEAL.md). No
hydrodynamics or tilted contacts; the contact is hydrostatic and horizontal, and remigration and
hydraulic reconfiguration are absent for the same reason (Grant 2020 includes the gradient). No
compartmentalisation; a compartmentalised trap needs a contact per compartment. Presence draws
are independent (8.1.4). Calculator inputs are independent (8.1.4). The empirical record is discovery-conditioned, censored above and truncated below
(8.1.7). The seismic likelihoods are elicited, not calibrated, which is why the effective sample
size and the sensitivity to each seismic input are reported: when a typed assumption moves the
contact further than the geology does, that is a finding about the assumption. A proven column in
the closure makes the prospect a discovery, which is a larger statement than one about depth;
the tool uses the depth only and does not change the element chances.
