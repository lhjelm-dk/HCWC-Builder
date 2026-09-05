# Stop choosing a distribution for the hydrocarbon–water contact. Derive one.

**Draft for LinkedIn. Written to be argued with.**

---

Everyone who quantifies prospects knows the hydrocarbon–water contact is the weakest number in the
assessment. It drives volume harder than anything else, it is the only input that turns a prospect
chance into a chance at a specific well location, and it usually arrives as a distribution somebody
chose.

The problem is not that the choice is careless. It is that it is **undefendable**. When a reviewer
asks *why that distribution*, there is no answer that survives the question — not because the
assessor was lazy, but because nothing in the workflow ever asked them to write the reasoning down.

So the useful question is not

> *what is my HCWC distribution?*

but

> **what geological mechanism stops the hydrocarbon column at this depth — and what stops it if that
> one does not?**

Answer the second and the first falls out, and it falls out **with its reasoning attached.** The
contact depth is not an input to be chosen. It is the outcome of a competition between mechanisms,
any one of which can arrest the column, and only one of which wins in any given realisation.

## What is actually competing

Filling starts at the structural apex and works downward, so every limit below is a depth at which
the column could stop:

**Charge.** Source quality and maturity, generation and expulsion timing, migration efficiency and
carrier effectiveness, access to this particular trap, and phase behaviour. Charge that fills past
the deepest mapped point is not a shallow limit — it is *no* limit, and belongs in that mechanism's
probability of being active rather than as a contact at the base of the structure.

**Trap geometry.** Closure geometry and the spill point, with the uncertainty on the spill pick
carried explicitly; fault-bounded and wedge geometries; pinch-out and truncation ending the closure
down-dip.

**Top and base seal capacity.** Capillary entry pressure through pore-throat radius and seal
lithology — Schowalter's balance, `h_max = 2γcosθ(1/r − 1/R) / (gΔρ)` — plus seal thickness and
integrity. Note that this is *phase-dependent*: the same seal holds a much shorter gas column than
an oil one, because Δρ is in the denominator.

**Seal continuity**, which is a different failure from capillary breakthrough: a sand-filled
channel, an erosional window, a breaching fault tip.

**Mechanical top seal.** Not the pore throats letting go but the rock parting in tension, when
pressure at the crest reaches the minimum horizontal stress. It only ever controls in overpressured
sections, and it is independent of everything above it.

**Lateral and fault seal.** Juxtaposition, fault-rock properties and SGR, membrane seal, the fault
leak point across all bounding faults, and reactivation.

**Regional and dynamic controls.** Post-charge tilt spilling part of a column or leaving a
palaeo-contact behind; hydrodynamic gradients; remigration.

In each realisation, sample each of these, ask which are present, and take **the shallowest one that
is active**. Record which one won. Do it ten thousand times and you have a contact distribution that
is an *answer* rather than an assumption.

Crucially, nothing is blended. Merging a leak into a background column-height distribution
suppresses outcomes *above* the leak, and can make apparent volume rise when you add a leak (Hood,
2019, 2024). A leak is a competing limit, not a downward nudge on a curve.

## The part that changes how you spend your afternoon

Twelve mechanisms sounds like twelve elicitations. It is not, and this is the practical finding.

Because the model records **which limit won in each realisation**, it can tell you immediately which
ones are actually setting the contact. On a typical prospect two or three mechanisms control the
answer in ninety per cent of realisations and the rest never bite at all. The ranking sits at the
top of the input tab and updates as you type.

**So the workflow inverts.** Run it on defaults first. Read the ranking. Then spend the afternoon
eliciting the two or three limits that move the answer, and leave the others rough — because rough
is provably good enough for a mechanism that never wins. The limits you would have agonised over are
usually not the ones that matter, and you now find that out in thirty seconds instead of never.

That is also the answer to the obvious objection. *"This needs more inputs than I have."* It needs
fewer careful ones than you are giving now, and it tells you which.

## What you can put in front of a reviewer

This is the part that matters if the number has to survive a meeting.

**Every figure states its basis.** A contact distribution is either the geological one or the one
carrying seismic or well evidence, and those are different objects. Each figure and table is
numbered and stamped with which it is, so a chart pasted into a partner deck cannot quietly become
the other one.

**The controlling-mechanism diagnostic is the argument.** "The P50 contact is 2,185 m" invites
disagreement about a number. "The contact is set by top-seal capacity in 60 % of realisations and by
charge in 14 %, and here is how that changes with depth" invites disagreement about **geology** —
which is a conversation your team can actually have, and resolve.

**The whole assessment saves and reloads.** Every input, every elicited range, every switch, in one
file. Six months on you can reopen exactly what was assessed rather than reconstructing it from a
spreadsheet and a memory.

**Provenance travels with the export.** Trial count, seed, assessment minimum, which basis, which
limits were active. The exported percentiles carry it, so the volumetrics package cannot be fed a
distribution whose origin nobody can state.

**And it refuses to give you a chance until you say what counts as success.** A probability of
success is not a probability of anything until you name the smallest column that would make the well
a discovery. Naming that column names a depth, and risk and volume then come off the same curve and
cannot drift apart.

## Calibrate the answer against the record, and know the one trap in doing it

A derived distribution is not automatically a better one. It has to be checked, and there is exactly
one public dataset to check it against: **Edmundson et al. (2021)**, 242 NCS discoveries with both
column height and closure height, published under CC-BY.

The check that matters is not against the record as a whole — it is against the part of it that
looks like your prospect. Evaluate the benchmark at **your own structural relief and burial depth**
and three questions become answerable:

- **Where does my P50 land?** If it is the benchmark's P25, only a quarter of comparable closures
  reach it and I am optimistic. Below 50, optimistic; above 50, conservative.
- **How much of the distribution agrees, not just the median?** A curve parallel to the record is a
  uniform bias you can correct with one number. A curve that meets it in the middle and departs at
  P10 is disagreement in the upside only — the tail the volume comes from.
- **Does my model fill traps the way the record does?** The share of realisations reaching spill is
  a single number, and it is the sharpest QC there is.

Disagreement is a finding, not an error. A prospect can be legitimately optimistic — a better seal
than the average NCS closure is a real thing to believe. It just has to be believed **on evidence
you can name**, and the useful question a gap raises is *which of my elicited limits would have to
move to close it.*

### The trap

**A trap that filled to spill tells you what the closure could hold. It does not tell you what the
seal could hold.** It is a **lower bound** — in survival-analysis terms a right-censored observation
— and treating it as a measurement is the error. **111 of the 242 are filled to spill. Forty-six per
cent of the record is censored, not measured.**

Fitted the ordinary way, the record says closure height controls column height more than it does,
and burial depth less:

| | trap height | burial depth |
|---|---|---|
| ordinary least squares | 0.880 | 0.143 |
| censoring-corrected | **0.701** | **0.277** |

The check that settles it needs no simulated data — ask each fit to reproduce the one statistic
anyone can verify, how often a discovery fills to spill:

```
observed in the dataset        45.9 %
censoring-corrected model      47.2 %
the uncorrected relationship   32.1 %
```

The corrected fit reproduces the filling behaviour of the dataset it was fitted to. The uncorrected
one is out by fourteen points, in the direction the omitted censoring predicts.

So calibrate — but calibrate against the corrected fit. The tool ships both and draws them side by
side, because the difference between them is large enough to change what you conclude about your own
prospect.

## A DHI is evidence to be weighed, not a contact to be substituted

If one section of this is worth your time, it is this one. It is the piece I have not seen
demonstrated anywhere, and it is where the geologist and the geophysicist finally have the same
conversation.

### The failure mode, which you will recognise

A team quotes **POS = 0.85 because the DHI is strong**, and pairs it with the DHI-case volume.

The 0.85 was computed as a *presence* probability — the chance there is an accumulation of at least
the minimum size. The volume is the *large*-case volume, the bright conformable one the amplitude is
actually arguing for. **A chance for one event, a volume for another**, multiplied together and
booked. It is not a DHI problem; it is a threshold-labelling problem that the DHI makes acute,
because the DHI is the one piece of evidence that speaks loudly about the large case.

### The reframe that dissolves it

Everything the model produces is one function:

```
F(h) = P(column height ≥ h)          h measured below the apex
```

And **every "POS" in the workflow is `F` read somewhere**:

| Quantity | Is just |
|---|---|
| Geological POS at the risking criterion | `F(h_min)` |
| POS at the well's reservoir entry depth | `F(z_entry − apex)` |
| Probability the DHI-indicated case is real | `F(h_DHI)` |
| Probability of filling to spill | `F(h_spill)` |

`F` decreases, so `F(h_min) ≥ F(h_DHI)` **always**. There is no combination step and nothing to
reconcile — those numbers were never competing. They are two points on one curve, and the only sin
is quoting one without saying which `h` it was read at. Once you see that, the DHI stops being a
special case and becomes what it always was: **evidence that reshapes the curve.**

### What the geophysicist has to supply — two numbers, both already known

1. **The depth of the interpreted flat event, and its uncertainty.** Pick error *plus* depth
   conversion, and the second is usually the larger. Nobody has to invent this.
2. **How detectable a column of a given height would be** — the detection function `D(h)`. A thin
   column produces no mappable anomaly; a thick one usually does. Every seismic interpreter already
   holds an opinion about where that threshold sits on their data.

That is the entire elicitation. No new risk numbers, no re-running the geological model.

### Why the machinery is clean rather than clever

The engine already drew ten thousand realisations from the geological distribution. Those
realisations **are** draws from the prior. So weighting each one by `L(seismic | h)` and
renormalising is not an approximation of a Bayesian update — it *is* one, by self-normalised
importance sampling. Posterior ∝ prior × likelihood, with no re-run and no re-elicitation.

And because the weights attach to realisations rather than to a curve, **the controlling-mechanism
bookkeeping survives the update.** You can still ask which limit set the contact — and now ask it
*given the DHI*, which is a question the scenario switch cannot answer at all.

**The detection function is what makes an absent anomaly usable.** If a column of that height should
have been bright and is not, the likelihood is `1 − D(h)`. Absence stops being an awkward special
case and becomes evidence in the same machinery — and on the worked prospect it is *severe*: prospect
POS falls from **40.8 % to 6.6 %.** Most workflows have nowhere to put that observation.

### What it actually does to the answer

On the shipped worked prospect, a **mild** amplitude — strength 5 on a −100 to 100 scale, barely
above neutral:

| | geological | given the DHI |
|---|---|---|
| Prospect POS | 40.8 % | **46.7 %** |
| Contact P50 | 2,186 m | **2,241 m** |
| P90–P10 spread | 140 m | **118 m** |

Two things to notice. The contact moves 55 m deeper — that is a lot of volume. And **the spread
narrows**: the evidence does not merely shift the answer, it sharpens it, which is what evidence is
supposed to do and what a scenario switch cannot do at all.

Push the strength to 40 and POS goes to **82.5 %**. Say the anomaly is absent and it goes to
**6.6 %**. That is the range one seismic opinion is worth, made explicit instead of argued about.

**And the effect on risk against depth is not a scale factor.** This is the part I would put in
front of a geophysicist:

```
chance of reaching a contact at    geological    given the DHI
2,100 m                               40.3 %         46.5 %
2,200 m                               14.8 %         32.8 %      more than doubled
2,300 m                                1.6 %          0.9 %      lower
```

The amplitude does not lift the whole curve. It **reshapes** it — pushing probability toward the
depths the flat event supports and taking it away from the depths it argues against. A single POS
multiplier cannot express that, and a scenario switch cannot either.

### Where I stop, and say so

**A neutral observation must do nothing, and here it does exactly nothing.** At strength 0 the
likelihood ratio is 1.000 and POS is 40.8 % before and 40.8 % after. That sounds trivial. It is easy
to get wrong, and getting it wrong means a DHI that says nothing quietly improves your prospect.

**Combining the two evidence channels is not Bayes, and I will not pretend it is.** The amplitude's
*geometry* — where it terminates — and its *character* — how bright, how conformable — are not
independent evidence, so multiplying their likelihood ratios would assume something false. The
implementation interpolates between the product and the stronger single channel, with the dependence
exposed as a number you set. Probabilistic evidence weighting with a stated assumption, labelled as
such.

**The likelihoods are elicited, not calibrated.** So the tool reports the effective sample size
behind every update — 2,799 of 10,000 realisations on the worked case — and plots what the answer is
most sensitive to. When a typed seismic assumption moves the contact further than the geology does,
that is a finding about your assumptions, not about the prospect.

For scale, the one published measurement I know of: Kjønsberg et al. (2010) inverted prestack AVO by
Markov chain Monte Carlo at three locations offshore Norway and reported prior and posterior
hydrocarbon probabilities. The implied likelihood ratio at the prospect centre was **29** — and that
location was subsequently drilled and found gas in two layers. A careful inversion on good data buys
about a factor of thirty. It is worth knowing what the ceiling looks like before you type a number
into a slider.

### Why I think this is new

**Hood recommends the scenario switch** — merge late, never blend into the input distribution — and
he is right that it is honest. It moves the contact without moving the chance. But it discards
information: it cannot use an *absent* anomaly, it cannot narrow the distribution, it cannot tell you
which mechanism set the contact given the DHI, and it gives you no depth-dependent risk at all.

The likelihood formulation over column height — detection function times pick likelihood, reweighting
the realisations, with the argmin bookkeeping intact — I have not found demonstrated in the
literature. *If it has been, I would like the reference.*

## If you carry a portfolio rather than a prospect

Three things change at that level.

**Prospects become comparable.** When every contact distribution is derived the same way, from a
stated assessment minimum, differences between prospects are geological rather than differences in
who assessed them and what they happened to think was reasonable that week.

**Systematic optimism becomes visible.** The calibration above is a per-prospect check, but run it
across a portfolio and the pattern is the finding: if every prospect lands at the benchmark's P25,
that is a house style, not twenty independent geological judgements.

**Numbers become traceable.** A saved assessment, a numbered figure with its basis stamped on it,
and a provenance line on the export mean a post-mortem can ask *which limit were we wrong about*
rather than *who chose that curve*.

## The ideas are published. A working tool was not.

Almost none of the thinking here is mine, and saying so is not modesty — it is the reason to trust
the result.

**Hood (2019, 2024, ExxonMobil)** states the rule the engine implements: separate distributions, take
the minimum per realisation, and never merge. **Beha, Christensen & Young (2012)** did it by hand,
enumerating combinations of trapping elements and collapsing them onto leak-point frequencies. Their
headline observation is the competing-limits principle, in print, in 2012:

> it is not intuitively obvious that a deep leak point can be statistically more likely than a leak
> point higher up the structure, although the deeper leak point requires more elements to seal
> simultaneously.

Their worked example — 0.60 / 0.12 / 0.28 at 2050 / 2100 / 2150 m — is reproduced exactly by this
tool's test suite, and is its only external validation. **Grant (2020, ConocoPhillips)** goes
furthest, and already publishes the controlling-mechanism diagnostic under the name "column height
control statistics". **Lowry, Suttill & Taylor (2005)** had depth-dependent risk two decades ago.

So the engine is not the contribution. What I think is:

**A working tool, in the open, that you can run on a prospect this afternoon.** Every reference above
is a method paper or an in-house implementation, and the published implementations that do exist need
a 3D geomodel — Grant's own argument for his approach is that such a model "is not always available
or built when evaluating exploration prospects". *I have looked and not found an open tool that does
this. If one exists I would genuinely like to be pointed at it.*

**A correction to the benchmark everyone calibrates against**, which I have not seen applied to this
dataset. And **per-element chance against depth, derived rather than allocated** — Grant publishes
the aggregate; the decomposition I have not found in print.

## What it does not do

Stated here rather than discovered later.

**Hydrodynamic tilting and remigration are not modelled**, though they genuinely stop columns.
**Compartmentalisation is not modelled**: it turns one contact into several, which is a different
object. Reservoir presence is carried as an element chance rather than a contact-moving limit,
because a reservoir that is not there has no contact to distribute. And **whether** a mechanism is
present is drawn independently, so the model can say two faults leak at similar depths but not that
they are the same fault and therefore stand or fall together — Beha et al. make the same assumption
explicitly, and neither of us has solved it.

## What this is all for

Column height, HCWC depth, spill point and seal capacity are four different quantities and it is
worth keeping them apart. The spill point is one *limit*. Seal capacity is another. The column height
is what the winning limit leaves you. The HCWC depth is the apex plus that column. And the chance of
success is a reading of the resulting curve at whatever minimum column you decided makes the well a
discovery.

Get the mechanism right and all four are consistent by construction. Choose a distribution because it
looks reasonable and none of them are — and worse, none of them can be defended when it matters.

The tool is free and open source: the competing-limits engine, the censoring-aware calibration
against the NCS record, depth-dependent risk per element, the DHI update, and an importer so a
company can run the same correction on its own trap-fill database without the data leaving the
browser.

It will not tell you whether to drill. It produces one input to that decision, honestly, with its
provenance attached — and that is the point. **A number you can defend is worth more than a number
you like.**

---

**References**

Beha, A., Christensen, J. E. & Young, R. (2012). A general method for the consistent volume
assessment of complex hydrocarbon traps. *Journal of Petroleum Geology* **35**(1), 85–98.

Edmundson, I. et al. (2021). An empirical approach to estimating hydrocarbon column heights for
improved pre-drill volume prediction in hydrocarbon exploration. *AAPG Bulletin* **105**(12),
2381–2403.

Grant, N. T. (2020). Using Monte Carlo models to predict hydrocarbon column heights and to
illustrate how faults influence buoyant fluid entrapment. *Petroleum Geoscience* **27**(2).

Hood, K. C. (2024). *Hydrocarbon Column Heights*, Parts 1 and 2. Rose & Associates, from Hood
(2019).

Kjønsberg, H., Hauge, R., Kolbjørnsen, O. & Buland, A. (2010). Bayesian Monte Carlo method for
seismic predrill prospect assessment. *Geophysics* **75**(5), O9–O19.

Lowry, D. C., Suttill, R. J. & Taylor, R. J. (2005). Advances in risking exploration prospects.
*APPEA Journal* **45**(1), 143–158.

Schowalter, T. T. (1979). Mechanics of secondary hydrocarbon migration and entrapment. *AAPG
Bulletin* **63**(5), 723–760.

*Lars Hjelm. App, code and data open — links in the comments.*
