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

The common treatment of a possible flat event is a scenario switch: *if* the DHI is valid, the
contact is at the flat spot; otherwise the geological contact stands. That is honest, and it moves
the contact **without moving the chance**.

But it discards information. The order that uses it is:

1. **Build the geological distribution first.** The DHI never edits it.
2. **State the depth of the interpreted flat event and its uncertainty** — pick error *plus* depth
   conversion, and the second is usually the larger.
3. **State how detectable a column of a given height would be.** A thin column produces no anomaly;
   a thick one usually does. This detection function is what makes an *absent* anomaly usable
   evidence rather than a special case, since the likelihood becomes `1 − D(h)`.
4. **Update the distribution**, and therefore the depth-dependent chance, rather than replacing it.

The geometric channel **is** a Bayesian likelihood update: the engine's realisations are draws from
the prior, so weighting each by `L(seismic | h)` and normalising is self-normalised importance
sampling, with the controlling-mechanism bookkeeping surviving intact.

**Combining the two evidence channels is not Bayes, and I will not pretend it is.** Multiplying the
amplitude's geometry and its character as independent evidence would assume something false. So the
implementation interpolates between the product and the stronger single channel, with the dependence
exposed as a number you set. That is probabilistic evidence weighting with a stated assumption, and
it is labelled as such in the tool.

The likelihoods are **elicited, not calibrated** — the detection function and the pick sigma are
modelling choices, and a posterior is only as defensible as they are. So the tool plots what the
answer is most sensitive to. When a typed seismic assumption moves the contact further than the
geology does, that is a finding about your assumptions, not about the prospect.

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

Lowry, D. C., Suttill, R. J. & Taylor, R. J. (2005). Advances in risking exploration prospects.
*APPEA Journal* **45**(1), 143–158.

Schowalter, T. T. (1979). Mechanics of secondary hydrocarbon migration and entrapment. *AAPG
Bulletin* **63**(5), 723–760.

*Lars Hjelm. App, code and data open — links in the comments.*
