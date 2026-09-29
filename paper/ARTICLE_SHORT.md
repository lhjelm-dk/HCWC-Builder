# Building hydrocarbon–water contact distributions from competing geological limits and DHI evidence

### The short version: a stochastic framework with probabilistic DHI updating for pre-drill prospect assessment

**Lars Hjelm**

---

*A short version of the paper on tab 8.2 of the tool, which carries the same argument in full with
its derivations, its worked numbers and its references. Every figure here is the tool's own output.
The tool runs at [hcwc-builder.streamlit.app](https://hcwc-builder.streamlit.app/) and its source is
at [github.com/lhjelm-dk/HCWC-Builder](https://github.com/lhjelm-dk/HCWC-Builder).*

## What the method does

A hydrocarbon–water contact does not have to be specified. It can be derived.

If the mechanisms that can stop a hydrocarbon column are modelled directly — structural spill,
charge limitation, capillary seal capacity, seal continuity, fault leakage, mechanical failure —
then in each realisation the shallowest active one sets the column, and the distribution of contacts
is what falls out. It becomes an output of the geological model rather than an input to it.

That single change has three consequences worth a geoscientist's attention.

The assessment can say which mechanism controls the contact, and how that control changes with
depth. Uncertainty and influence stop being the same thing: a mechanism may carry a wide range and
almost never decide the answer, while a narrow one that usually decides it moves everything.

The probability of success at any depth comes from the same model as the contact. Risk against depth
is not a second elicitation to be reconciled with the first, because there is only one model.

And a seismic indication can be treated as evidence that updates that model, rather than as a
separate case that replaces it. The indication changes the probability that hydrocarbons are present
and, separately, changes which contact depths are likely. Both readings come from the same
realisations.

## The problem this addresses

In most evaluations the contact uncertainty is a distribution somebody chose: uniform from apex to
spill, a three-point estimate, a company standard, a fit to analogue fields. The number may be
perfectly reasonable. What it cannot say is which geological process it represents, and therefore
what evidence would change it.

The awkwardness shows when the pieces are assembled. The geological probability of success is
assessed element by element — charge, reservoir, closure, retention — and arrives as one number. The
contact distribution is assessed separately and arrives as another. Then a direct hydrocarbon
indicator appears, modifies the chance by some factor, and indicates a contact at a depth quite
different from the minimum column the economics were built around.

Three numbers, three provenances, and no principled way to reconcile them. Worse, the assessment
cannot answer the question a reviewer actually asks: if this prospect fails, which mechanism failed,
and was that the mechanism we spent the money studying?

![Every mechanism that can stop the column, on one section](figures/Figure_1.1a_every-mechanism-that-can-stop-the-column-on.png)

> Figure 1. The mechanisms that can stop a column, drawn on one section, each with the range of
> depths over which it might act. Hydrocarbons fill downward from the crest, so every capacity is
> measured from there. This figure is the elicitation: a limit is entered where its mechanism acts,
> not where a contact is wanted.

## The mechanisms that can stop a column

Each mechanism is a geological statement, and each is already held as an opinion somewhere in the
team.

Structural spill is the maximum column the trap geometry retains. It is a mapped surface, so depth
conversion and interpretation make it a distribution rather than a fixed depth.

Charge limitation applies where the available charge is insufficient to fill the trap to a deeper
limit. It should not be represented as a contact at the base of the structure by default: if charge
fills the structure, charge imposes no contact at all. Its column can be computed from an area–depth
integration rather than elicited.

Capillary seal capacity is the column a seal holds before hydrocarbons pass through its pore
throats. It is dominated by the largest connected pore throat and it is phase dependent: the same
seal supports a much shorter gas column than an oil one, so the charge phase and the seal fluid have
to be set coherently.

Seal continuity is a different failure from capillary breakthrough. A seal may have ample local
capacity while being ineffective because of a sand-filled channel, an erosional window or local
thinning.

Fault seal adds juxtaposition, shale gouge, fault-rock properties and reactivation. Fault geometry
and fault leakage are different mechanisms even on the same fault, and belong to different risk
elements.

Mechanical failure applies in sufficiently overpressured systems, where the column is limited by the
headroom between the minimum horizontal stress and the pore pressure rather than by pore-throat
entry pressure.

Two conventions keep the elicitation honest. A capacity — what a seal holds, what a fault leaks past
— is naturally stated as metres of column below the crest and does not move when the crest pick
moves. A mapped surface is naturally stated as a depth. Everything resolves to metres of hydrocarbon
column in the end, but the input should be given in whichever form the geologist actually knows.

## How the competition works

Each mechanism carries two judgements: whether it is present on this prospect at all, and where it
acts if it is. Both are ordinary geological opinions.

In every Monte Carlo realisation all the limits are sampled, and the shallowest active one becomes
that realisation's contact. At least one limit is always present, since every closure has a spill
point. Repeating this many times produces the contact distribution — and, because the controlling
mechanism is recorded each time, a record of what produced it.

![Fifty realisations of the competition](figures/Figure_4.1.1a_the-competition-realisation-by-realisation.png)

> Figure 2. Fifty consecutive realisations. Each coloured dot is one limit's sampled depth; the
> ringed dot is the shallowest active one, which sets the contact for that realisation. No limit
> wins consistently, and the winner changes as the sampled depths reorder. On the right, the
> distribution those minima make.

A realisation is not a weighted average of several possible leak points. It is one possible
geological configuration, in which the first effective limiting mechanism determines the column.
That is why the limits are sampled and the minimum taken, rather than blended.

The distinction matters most for a leak. Merging a leak into a background column distribution
suppresses the realisations above the leak and leaves the rest untouched, which is not what a leak
does; the blended distribution then corresponds to no geology at all. The published consequence is
that adding a deep leak can make a prospect look larger.

The same reasoning applies at the spill point. Truncating a background distribution with an
independently sampled spill leaves the smaller columns alone and produces filled-to-spill cases at a
rate the seal implies. Simply defining the distribution to end at spill assigns almost no
probability to filling to spill, which asserts that the spill point exerts no control — and quietly
changes the distribution of every smaller column as well.

Not every limit is a leak point, and the difference is geometric. Spill, fault leakage and seal
failure are escape paths: hydrocarbons leave the accumulation. Charge and reservoir continuity cap
the column with the hydrocarbons staying where they are. In both cases what is entered is the
maximum column the mechanism supports. A base seal whose capacity is exceeded drains nothing if what
passes it has nowhere to go — in a four-way closure with no carrier beneath, the hydrocarbon
re-migrates into the same trap and the contact does not move.

## What the controlling mechanism adds

Recording which limit won costs one integer per realisation and is the point of the whole
construction.

![The controlling mechanism at each depth](figures/Figure_4.1.2a_the-controlling-mechanism-at-each-depth.png)

> Figure 3. Which mechanism stops the column, and where. The shares are not constant down the
> structure: shallow contacts are almost entirely seal-controlled, deeper ones pass to fault
> geometry and finally to spill. A distribution on its own cannot show this.

The practical reading is about where to spend the next study. A mechanism that controls under one
per cent of realisations cannot move the answer much however uncertain it is; refining the
seal-capacity elicitation, which controls a third of them, moves a great deal. That is a different
question from a sensitivity analysis, which asks how far each input shifts the mean, and the tool
reports both.

A small overall share is not the same as unimportance. A mechanism may control few realisations
overall but dominate the deep ones — and those are the realisations that carry the volume.

![The limits on one axis](figures/Figure_4.1.2e_one-axis-five-views-exceedance-curves-is-the.png)

> Figure 4. The same limits drawn as exceedance curves on one axis. Each flattens at that limit's
> probability of being present. The contact curve lies below all of them, because a column reaches a
> given depth only where every active limit permits it.

## One model for the contact and the risk against depth

Because the contact distribution is built from limits rather than chosen, it is simultaneously a
statement of how the chance of finding hydrocarbons falls with depth. The two are readings of one
object rather than two assessments that have to agree.

The chance that a well finds hydrocarbons at a given depth is the chance that an accumulation exists
at all, multiplied by the chance that the column reaches that depth. The first factor is the
geological risk assessment, unchanged and unchallenged. The second is read off the contact
distribution. Both terms are necessary: quoting the conditional term alone treats the accumulation
as certain and overstates the prospect substantially.

![The chance against depth, and what makes it](figures/Figure_4.1.3a_the-chance-against-depth-and-what-makes-it.png)

> Figure 5. One distribution read three ways: the chance the contact lies at or below each depth
> given an accumulation, the same multiplied by the chance an accumulation exists, and the
> controlling limit in each depth bin. Because the curve falls with depth, a probability quoted
> without the depth or column height it was read at means very little.

An array built this way cannot contradict itself. The chance of reaching a deeper contact cannot
exceed the chance of reaching a shallower one, since a column that reaches the deeper level has
already passed the shallower. That is guaranteed by construction here, because every point on the
curve is read off the same sample. An array assembled band by band, with a risk stated for each
column-height slice, carries no such guarantee, and a violation is easy to miss because each band
looks reasonable on its own.

The same construction gives the risk element by element.

![Each element's chance against depth](figures/Figure_4.2.2a_each-element-s-chance-curve-derived-from-the.png)

> Figure 6. The same information per risk element — charge, reservoir, closure, retention — derived
> from the shallowest active limit within each element rather than allocated by judgement. This is
> the form a volumetric tool needs, and the tool checks on every run that the per-element curves
> still multiply back to the contact distribution.

Change a seal capacity, a fault limit or a spill distribution, and the contact, the chance at the
well and the volume range all move together, consistently, because they were never separate.

## Checking against what has been found

A distribution nobody has compared with observation is an opinion. The tool compares the modelled
contact against a published record of 242 Norwegian Continental Shelf discoveries, each with a
column height, a trap height and a burial depth.

The comparison answers a narrow but useful question: for a closure of this height at this burial
depth, is the modelled column plausible, and is the modelled probability of filling to spill
plausible?

Two properties of discovery data have to be carried into that comparison rather than ignored.

Discoveries that filled to spill are right-censored. Such a pool tells you the seal held at least
the trap height; it does not measure what the seal could have held. Treated as exact measurements
they bias the fitted relationship toward structural spill. Dropping them is not a remedy either — it
trades one bias for another, since what remains is conditioned on capacity being less than trap
height.

Column height and trap height also share the crest pick. Both are measured downward from the same
depth-converted surface, so an error in the crest propagates into both with opposite sign. That
manufactures a correlation between them which no censoring correction removes.

![Column height against closure height](figures/Figure_6.2a_column-height-against-closure-height-after.png)

> Figure 7. Column height against closure height in the discovery record. The red points lie on the
> one-to-one line by definition — they are filled to spill. The two fitted lines are the ordinary
> fit and the censoring-corrected one, and the gap between them is what treating a lower bound as a
> measurement costs. The violins are this prospect at the same closure height, geological and after
> the seismic update, offset sideways so they can be read.

The point of the comparison is not to find a true empirical distribution and adopt it. It is a
check: if the model disagrees materially with the record for closures of this size, that is a
finding about the spill and seal inputs, and it should be explained by a mechanism.

## A seismic indication as evidence, not as a second model

A direct hydrocarbon indicator is usually handled by defining a separate case and substituting its
contact depth, or its volume, for the geological result. That merges late, which is a real virtue,
but it treats an observation as a scenario — and a scenario cannot be argued with in geological
terms.

The alternative is to treat the indication as evidence about the model that already exists. The
geological realisations are a sample of what the model considers possible. The seismic observation
does not need a new simulation; it only changes how much each realisation counts. Realisations
consistent with the observation gain weight, those inconsistent with it lose weight, and the set of
geological possibilities is unchanged.

Two things follow that a scenario switch cannot offer. Each realisation still carries its
controlling limit, so the model can say which mechanism controls the contact given the seismic
evidence. And the geological and updated results are the same realisations under different weights,
so they are directly comparable rather than being two unrelated answers.

![The model as two rows](figures/Figure_8.1.1a_the-model-as-two-rows-the-geological-model.png)

> Figure 8. The whole workflow. The geological model is the prior: element chances give the chance
> of an accumulation, and given an accumulation the limits compete. The seismic indication enters as
> evidence in two separate channels. Both rows end in the same reading: the chance of meeting the
> threshold, at the assessment minimum and at a well.

The essential move is to separate what the indication tells us about *whether* hydrocarbons are
present from what it tells us about *where the column ends*. These are different questions, they are
supported by different attributes, and collapsing them into one DHI factor is why a single number is
so often argued about.

## What the character channel does to the chance

Amplitude strength, polarity, conformity, behaviour with offset and consistency with the expected
fluid response are evidence about whether the response is consistent with hydrocarbons at all. They
say nothing directly about contact depth.

In the tool this reading is placed on a DHI evidence index: a relative scale, neutral in the middle,
increasingly supportive above and increasingly contradictory below. Two reference distributions —
one for hydrocarbon-bearing outcomes, one for non-hydrocarbon — give the weight of evidence at any
reading, and that weight updates the probability that an accumulation exists.

The index moves the chance and leaves the contact distribution alone. On the worked prospect a
moderately supportive reading takes the prospect chance from roughly four in ten to nearly five in
ten, while the median contact does not move at all and the spread is unchanged. Nothing has been
reweighted, because the character of the response is not evidence about depth.

Two limits on that update are worth stating. The index is a conceptual scale, not a calibrated
measurement: the reference pair the tool ships with is a relationship, not a basin calibration, and
it is editable. And a single channel of fluid-indicator evidence is capped, because one line of
evidence rarely justifies more, and a reading beyond the cap is a signal to revisit the inputs
rather than to trust the arithmetic.

## What the geometry channel does to the contact distribution

The position of the interpreted event, and its uncertainty, are evidence about where the column
ends. Pick error and depth conversion both enter, and the second is usually the larger.

One more judgement is needed, and it is the one that carries the most weight: whether the picked
event is the contact at all. A flat event can be lithology, a diagenetic front, fizz gas read as
pay, or a processing artefact. That judgement is separate from how bright the anomaly is, and it
must not be derived from the amplitude, because the amplitude's evidence about hydrocarbons has
already been used in the other channel.

Keeping the two apart protects a case worth protecting: a dim body with a flat, conformable event
that cuts structure is weak evidence for hydrocarbons and strong evidence about where the contact
would be, and a method that derives one judgement from the other cannot say so.

![The pick against the geology](figures/Figure_5.1.1a_blue-is-the-geological-contact-distribution.png)

> Figure 9. The two inputs of the geometry channel: the geological contact distribution in blue, the
> interpreted event with its uncertainty in red. Here the pick is about five times sharper than the
> geology and sits near its median, so it narrows the answer without moving it.

The result is that the seismic evidence reshapes the distribution rather than scaling it. A single
multiplier on the probability of success changes the level of a curve and leaves its shape alone. An
observation about depth cannot do that: it must raise the chance at some depths and lower it at
others.

![The chance against threshold, before and after](figures/Figure_5.1.5a_the-chance-against-threshold-p-g-f-h.png)

> Figure 10. The chance of reaching each depth before and after the update. The curve does not
> simply lift. The character scales it; the geometry reshapes it, raising the chance near and above
> the indicated contact and lowering it below, because the evidence moves probability toward the
> depths the interpreted event supports.

How far the evidence moves the answer is set by the uncertainty the interpreter states. A broad
likelihood leaves the geological model with most of the influence; a narrow one lets the seismic
observation dominate the contact distribution. That is not a defect — a well-imaged, conformable
flat spot at a confidently picked depth is better evidence about the contact than any elicited seal
capacity — provided the strength of the update follows from the stated uncertainty rather than from
a decision to believe the DHI.

The tool reports how much of the original geological ensemble the answer now rests on. A low value
does not mean the interpretation is wrong; it means the result depends heavily on a small part of
the ensemble, which is worth knowing before the number is quoted.

![The limits on one axis, given the DHI](figures/Figure_5.2.2e_one-axis-five-views-exceedance-curves-is-the.png)

> Figure 11. Figure 4 after the update. The same limits, reweighted by the evidence, with the
> contact still the minimum of the active ones. The geological model has not been replaced; the
> evidence has changed which of its realisations count.

![The chance against depth given the DHI](figures/Figure_5.2.3a_the-chance-against-depth-and-what-makes-it.png)

> Figure 12. Figure 5 after the update, so the two can be read side by side. The contact
> distribution and the risk against depth have moved together, because they are readings of the same
> object. The controlling mechanism per depth bin has moved with them.

## Absence as evidence

A missing indication can carry information too, but only where the data were good enough that
something should have been visible.

No DHI is not the same as evidence against hydrocarbons. A thin or poorly imaged column may simply
produce no mappable response, in which case its absence says very little. Whether a column could
have shown at all is a geophysical judgement, and the tool asks for it explicitly as the chance that
a column of a given height produces a mappable anomaly.

Where that judgement bites, absence reshapes the contact distribution toward the shorter columns
that would not have shown. Whether it also lowers the chance that hydrocarbons are present at all
requires one further assumption: how often a barren trap produces a similar-looking response. That
rate is elicited rather than calibrated, so it belongs in an explicit sensitivity rather than hidden
inside a result.

## What the evidence is not allowed to do

Three boundaries keep the update honest, and each corresponds to a way this kind of analysis
normally goes wrong.

An indication is not a contact. Even a sharp, confident pick cannot make one depth certain, because
the event may not be the contact at all. Push the indicated contact progressively deeper than the
geology supports and the answer stops following it: the model concludes that the event is probably
not the contact, rather than that the contact lies where the pick says. That is the correct
conclusion, and a scenario switch cannot reach it.

An indication does not rewrite the geological risk. It is evidence that hydrocarbons may be present.
It does not identify which of charge, reservoir, closure or retention would otherwise have failed,
so the element chances are set once and the seismic workflow cannot edit them. A bright spot does
not retrospectively improve a charge argument. This is the practical guard against using one
observation twice.

The two judgements are related, and the model cannot fix that. An interpreter who sees a strong,
conformable response will reasonably grade both the evidence and the contact attribution highly. The
arithmetic keeps the two updates in separate factors, but the dependence lives in the elicitation
and has to be handled there, by being explicit about what each judgement is meant to represent.

![What the DHI can turn out to have been](figures/Figure_5.1.4b_the-outcomes-of-a-seen-dhi-in-depth-order-as.png)

> Figure 13. What an indication can turn out to have been, as shares of all outcomes: no
> hydrocarbons at all, a contact above the indicated band, a contact within it because the
> indication is the contact, a contact within it by coincidence, and a contact below it.

![The outcomes with their chances](figures/Table_5.1.4c_the-outcomes-with-their-chances-summing-to.png)

> Table 1. The same outcomes as numbers. The two rows inside the band are separated by which branch
> of the evidence put the contact there: the indication being the base of the column, or the geology
> having put a contact near that depth anyway. A well that finds the contact inside the band
> confirms the indication in that proportion — which is a more useful post-well question than
> whether the DHI "worked".

## What the tool is not

The framework is deliberately simple. It is not a basin model, a hydrodynamic model or a
three-dimensional flow simulation, and hydrodynamic gradients, remigration, palaeo-contacts and
compartmentalisation are not represented.

That is a scope statement rather than an apology. Where a more detailed model exists, its output can
enter as one more competing limit — a fluid-potential limit, a palaeo-contact, a migration
constraint — and be carried through to the contact distribution with everything else. The framework
is an integration layer between geological understanding, contact uncertainty and seismic evidence,
not a competitor to the models that produce better constraints.

Two simplifications are worth naming. Whether a mechanism is present is drawn independently of every
other mechanism, so two faults that leak at correlated depths can be expressed while two faults that
stand or fall together cannot. And a single contact is modelled at a time: a gas–oil contact and an
oil–water contact under the same seal are limited by different entry pressures, and that construction
is not implemented.

The seismic likelihood is a modelling assumption rather than a measurement. Every term in it is a
convention or an elicited judgement, so the arithmetic is exact given the observation model and the
uncertainty lies in the model. That is why the sensitivity to each seismic input is reported rather
than hidden: when a typed assumption moves the contact further than the geology does, that is a
finding about the assumption.

## Why it is worth the trouble

The objective is not a more sophisticated distribution for its own sake. It is a distribution that
is a consequence of stated geological assumptions, so that it can be defended in review and
corrected after drilling.

A directly elicited contact distribution asks the assessor to specify the final uncertainty. The
competing-limits approach asks them to specify the mechanisms that produce it — and those mechanisms
mean different things: geometry, retention against buoyancy, lateral containment, petroleum-system
uncertainty, a stress condition. Once each is a competing limit, the contact distribution and the
chance of success at every depth are properties of the model rather than inputs to it.

A dry hole or an unexpectedly small discovery can then be examined in terms of the mechanism that
was misassessed, instead of the unanswerable question of why the contact distribution was too deep.

The tool is open source, runs in a browser and ships with a worked prospect, so nothing has to be
set up to see what it does. The paper on tab 8.2 carries the derivations, the worked numbers and the
references.
