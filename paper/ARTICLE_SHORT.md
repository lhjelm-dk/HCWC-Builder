# The hydrocarbon–water contact as an output, not an input

### A short version of the paper, for readers who will not open the long one

**Lars Hjelm**

---

*The short version of `paper/ARTICLE.md`, which carries the argument in full with its
derivations and references. Every figure here is the tool's own, and every number comes from the
same script. The tool runs at [hcwc-builder.streamlit.app](https://hcwc-builder.streamlit.app/).*

## The result first

A hydrocarbon–water contact does not have to be specified. It can be derived.

If the mechanisms that can stop a hydrocarbon column are modelled directly — spill, charge, seal
capacity, seal continuity, fault leakage, mechanical failure — then in each realisation the
shallowest active one sets the column, and the distribution of contacts is what falls out. It is an
output of the geological model rather than an input to it.

That one change has three consequences worth a geoscientist's attention. The assessment can say
which mechanism controls the contact, and how that changes with depth. The probability of success
at any depth comes from the same model as the contact, so risk against depth is not a second
elicitation. And a seismic indication can be treated as evidence that updates the model, rather
than as a separate case that replaces it.

## The problem this addresses

In most evaluations the contact uncertainty is a distribution somebody chose: uniform from apex to
spill, a three-point estimate, a company standard. The number may be reasonable. What it cannot say
is which geological process it represents.

The awkwardness shows when the pieces are put together. The geological probability of success is
assessed separately from the contact. Then a direct hydrocarbon indicator arrives, modifies the
chance, and indicates a contact somewhere quite different from the minimum volume the assessment
was built around. Three numbers, three provenances, and no way to reconcile them.

![Every mechanism that can stop the column, on one section](figures/Figure_1.1a_every-mechanism-that-can-stop-the-column-on.png)

> Figure 1. The mechanisms that can stop a column, drawn on one section, each with the range of
> depths over which it might act. Hydrocarbons fill downward from the crest, so every capacity is
> measured from there. This is the elicitation: a limit is entered where its mechanism acts, not
> where a contact is wanted.

## How the competition works

Each mechanism carries two judgements: whether it is present on this prospect at all, and where it
acts if it is. Both are ordinary geological opinions, and both are already held.

In every Monte Carlo realisation all the limits are sampled, and the shallowest active one becomes
that realisation's contact. Repeating this produces the contact distribution — and, because the
controlling mechanism is recorded each time, a record of what produced it.

![Fifty realisations of the competition](figures/Figure_4.1.1a_the-competition-realisation-by-realisation.png)

> Figure 2. Fifty consecutive realisations. Each coloured dot is one limit's sampled depth; the
> ringed dot is the shallowest active one, which sets the contact. No limit wins consistently. On
> the right, the distribution those minima make.

![The controlling mechanism at each depth](figures/Figure_4.1.2a_the-controlling-mechanism-at-each-depth.png)

> Figure 3. Which mechanism stops the column, and where. The shares are not constant down the
> structure: shallow contacts are almost entirely seal-controlled, deeper ones pass to fault
> geometry and finally to spill. A distribution alone cannot show this.

That last point is the practical one. A mechanism may carry great uncertainty and little influence,
if it rarely provides the minimum; a narrow uncertainty in a dominant mechanism can move the whole
answer. The assessment therefore says where further work is worth doing, rather than only what the
answer is.

![The limits on one axis](figures/Figure_4.1.2e_one-axis-five-views-exceedance-curves-is-the.png)

> Figure 4. The same limits as exceedance curves on one axis. Each flattens at that limit's
> probability of being present. The contact curve lies below all of them, because a column reaches
> a depth only where every active limit permits it.

## The same model gives the risk against depth

Because the contact distribution is built from limits rather than chosen, it is also a statement of
how the chance of finding hydrocarbons falls with depth. The two are readings of one object.

The probability that a well finds hydrocarbons at a given depth is the chance that an accumulation
exists at all, multiplied by the chance that the column reaches that depth. Nothing about depth
risk is elicited twice, because there were never two models.

![The chance against depth, and what makes it](figures/Figure_4.1.3a_the-chance-against-depth-and-what-makes-it.png)

> Figure 5. One distribution read three ways: the chance the contact lies at or below each depth
> given an accumulation, the same multiplied by the chance an accumulation exists, and the
> controlling limit in each depth bin. A probability quoted without the depth it was read at means
> little, because the curve falls.

An array built this way cannot contradict itself. The chance of reaching a deeper contact cannot
exceed the chance of reaching a shallower one, since a column that reaches the deeper level has
already passed the shallower. An array assembled band by band, with a risk stated for each slice,
carries no such guarantee.

![Each element's chance against depth](figures/Figure_4.2.2a_each-element-s-chance-curve-derived-from-the.png)

> Figure 6. The same information per risk element — charge, reservoir, closure, retention — derived
> from the shallowest active limit within each element rather than allocated by judgement. This is
> the form a volumetric tool needs.

## Checking against what has actually been found

A distribution nobody has compared with observation is an opinion. The tool compares the modelled
contact against a published record of 242 Norwegian Continental Shelf discoveries.

One property of that record needs care. Discoveries that filled to spill record the trap, not the
seal: they show the seal held at least that much, not what it could have held. Treated as exact
measurements they bias the relationship toward structural spill. Fitting them as the lower bounds
they are gives a different, and lower, estimate of seal capacity.

![Column height against closure height](figures/Figure_6.2a_column-height-against-closure-height-after.png)

> Figure 7. Column height against closure height in the discovery record. The red points lie on the
> one-to-one line by definition — they are filled to spill. The two fitted lines are the ordinary
> fit and the censoring-corrected one; the difference between them is what treating a lower bound
> as a measurement costs. The violins are this prospect, at the same closure height.

## The seismic indication as evidence

A direct hydrocarbon indicator is usually handled by defining a separate case and substituting its
contact. That merges late, which is a virtue, but it treats an observation as a scenario.

The alternative is Bayes' rule, and it is the only piece of arithmetic in this article:

    P(contact | seismic) is proportional to P(seismic | contact) × P(contact)

In words: the geological realisations are already a sample of what the model considers possible, so
the seismic observation does not need a new simulation. It only changes how much each realisation
counts. Realisations consistent with the observation gain weight; those inconsistent with it lose
weight. The set of geological possibilities is unchanged.

![The model as two rows](figures/Figure_8.1.1a_the-model-as-two-rows-the-geological-model.png)

> Figure 8. The whole workflow. The geological model is the prior. The seismic indication enters as
> evidence in two separate channels, and each ends in the same reading: the chance of meeting the
> threshold, at the assessment minimum and at a well.

Those two channels answer different questions, and keeping them apart is most of the method.

The character of the response — amplitude, conformity, behaviour with offset — is evidence about
whether hydrocarbons are present at all. It updates the chance of an accumulation.

The geometry of the response — where the flat event sits, and how well it is picked — is evidence
about where the column ends, given that there is one. It reweights the contact distribution.

A strong response can therefore make hydrocarbons much more likely while leaving the contact depth
almost as uncertain as before. The two are reported apart, because they are.

![The pick against the geology](figures/Figure_5.1.1a_blue-is-the-geological-contact-distribution.png)

> Figure 9. The two inputs of the geometry channel: the geological contact distribution in blue,
> the interpreted event with its uncertainty in red. Here the pick is about five times sharper than
> the geology and sits near its median, so it narrows the answer without moving it.

![The chance against threshold, before and after](figures/Figure_5.1.5a_the-chance-against-threshold-p-g-f-h.png)

> Figure 10. The chance of reaching each depth before and after the update. The curve does not
> simply lift: the character scales it, and the geometry reshapes it, raising the chance near and
> above the indicated contact and lowering it below. A single multiplier on the probability of
> success cannot express that.

![The limits on one axis, given the DHI](figures/Figure_5.2.2e_one-axis-five-views-exceedance-curves-is-the.png)

> Figure 11. Figure 4 after the update. The same limits, reweighted by the evidence. The geological
> model has not been replaced; the evidence has changed which of its realisations count.

![The chance against depth given the DHI](figures/Figure_5.2.3a_the-chance-against-depth-and-what-makes-it.png)

> Figure 12. Figure 5 after the update, so the two can be read side by side. The contact and the
> risk against depth move together, because they are readings of the same object.

## What the evidence is not allowed to do

Three boundaries keep the update honest.

An indication is not a contact. Even a sharp, confident pick cannot make one depth certain, because
the picked event may be lithology, a diagenetic front or a processing artefact. Push the indicated
contact progressively deeper than the geology supports, and the answer stops following it: the
model concludes that the event is probably not the contact, rather than that the contact lies where
the pick says.

An indication does not rewrite the geological risk. It says something about whether hydrocarbons
are present. It does not identify which of charge, reservoir, closure or retention would otherwise
have failed, so the element chances are set once and the seismic workflow cannot edit them. This
avoids using the same observation twice.

An absent response is not the same as evidence against hydrocarbons. It carries information only
where the data were good enough that something should have been visible. Whether a column could
have shown at all is a geophysical judgement, and it has to be made explicitly.

![What the DHI can turn out to have been](figures/Figure_5.1.4b_the-outcomes-of-a-seen-dhi-in-depth-order-as.png)

> Figure 13. What an indication can turn out to have been, as shares of all outcomes: no
> hydrocarbons, a contact above the indicated band, a contact within it because the indication is
> the contact, a contact within it by coincidence, and a contact below it.

![The outcomes with their chances](figures/Table_5.1.4c_the-outcomes-with-their-chances-summing-to.png)

> Table 1. The same outcomes as numbers. The two rows inside the band are separated by which branch
> of the evidence put the contact there — the indication being the base of the column, or the
> geology having put a contact near that depth anyway. A well that finds the contact in the band
> confirms the indication in that proportion.

## What it is not

The framework is deliberately simple. It is not a basin model, a hydrodynamic model or a
three-dimensional flow simulation, and it does not try to be. Where such a model exists, its output
can enter as one more competing limit — a fluid-potential limit, a palaeo-contact, a migration
constraint — and be carried through to the contact distribution with everything else.

The seismic likelihood is a modelling assumption rather than a measurement. Its terms are typed, not
observed, which is why the tool reports how far the evidence has displaced the geology, and why the
sensitivity to each seismic input is shown rather than hidden.

## Why it is worth the trouble

The purpose is not a more sophisticated distribution. It is a distribution that is a consequence of
stated geological assumptions, so that it can be defended in review and corrected after drilling.

A dry hole or an unexpectedly small discovery can then be examined in terms of the mechanism that
was misassessed, instead of the unanswerable question of why the contact distribution was too deep.

The tool is open source, runs in a browser, and ships with a worked prospect, so nothing has to be
set up to see what it does. The full paper carries the derivations, the worked numbers and the
references.
