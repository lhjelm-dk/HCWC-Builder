# Stop choosing a hydrocarbon–water contact distribution. Start modelling where the column stops.

*[COVER IMAGE: fig1_competing_limits.png]*

The hydrocarbon–water contact is one of the most consequential uncertainties in pre-drill resource
estimation. It is also one of the hardest to quantify, and getting it wrong moves volumes more than
almost anything else we spend our time on.

We can spend months on seismic data and interpretation, depth conversion, structural mapping and
reservoir modelling. We build increasingly sophisticated estimates of the potential hydrocarbon
container.

And then, somewhere in the Monte Carlo model, we are asked:

**"What distribution do you want for the HCWC?"**

Uniform? Normal? Lognormal? PERT? Beta?

Perhaps we pick a most-likely depth and add an uncertainty range. Or use the company-standard
distribution.

There are many creative ways of saying: *we don't really know.*

Perhaps we can do better than choosing a distribution that looks reasonable.

## What are we actually uncertain about?

Imagine a structure with 300 m of potential closure. If the trap is sufficiently charged, properly
sealed and structurally correct, perhaps it fills to spill.

But what if charge is insufficient? Migration inefficient? The spill point 30 m shallower than we
think? A fault leaks at a particular depth. The top seal cannot support the required capillary
pressure. The seal is laterally discontinuous. Regional tilt causes spillage. The reservoir pinches
out.

The HCWC is the **result** of these uncertainties. It is not independent of them.

That, I think, is the problem with treating the contact as just another input distribution.

## We are actually rather good at defining the container

Exploration is increasingly good at describing the potential container. We map the structure,
estimate closure and spill, model reservoir presence and quality, and build sophisticated seismic
and geological models.

Sometimes we even have an idea of where the contact might be from a DHI. Maybe it is convincing.
Maybe it isn't. Often there is no DHI at all.

Then we are back to the awkward question: **how high could this trap realistically fill?**

There are several ways to answer it. A uniform distribution across the structural relief is easy. A
skewed distribution might reflect a belief that shallow contacts are more likely than deep ones. A
lognormal or beta distribution offers a mathematically convenient way of expressing asymmetry. Or we
might use a local, regional or global empirical filling distribution.

All can be defensible. But every prospect is different, and trying to be consistent across a
portfolio by putting the same standard distribution on every closure may create **inconsistent
geology disguised as consistent statistics**.

The real question is: *what geological mechanism could stop the column here?*

## The contact as a competition between limits

A hydrocarbon column can be limited by several different mechanisms:

- **Charge** — source quality and maturity, generation and expulsion timing, migration efficiency,
  carrier effectiveness, access to the trap, available volume and phase behaviour.
- **Trap geometry** — closure, spill-point uncertainty, fault-bounded geometry, wedges, truncations
  and compartmentalisation.
- **Seal** — top- and base-seal capacity, capillary entry pressure, pore-throat size, lithology,
  thickness and integrity.
- **Lateral and fault seal** — juxtaposition, fault-rock properties, SGR, membrane seal, and the
  effective fault leak point.
- **Dynamic effects** — regional tilt, hydrodynamic gradients, remigration, palaeo-contacts and
  hydraulic reconfiguration.
- **Reservoir** — presence, continuity, quality, effective pore volume and pinch-out.

These are different geological problems, and they impose different limits on the column.

So instead of sampling the contact directly, why not sample the mechanisms that can limit it?

In each realisation, spill has a possible limit, fault leakage has a possible limit, seal capacity
has a possible limit, charge has a possible fill limit, and reservoir geometry may impose another.

Then:

    HCWC = min( H_charge , H_spill , H_fault , H_seal , H_reservoir , ... )

**The shallowest active limit wins.**

Run that thousands of times and the contact distribution becomes an *output* of the geological
assumptions rather than an assumption itself.

*[IMAGE: fig1_competing_limits.png — every limit drawn on one depth axis, with the resulting contact
in red. The result sits shallower than any individual limit, because in each realisation the
shallowest active one wins.]*

And because the model records **which limit won**, it gives something a fitted distribution cannot:

*[IMAGE: fig2_what_controls_it.png — the controlling mechanism, as an output.]*

This is not a new geological principle. Beha, Christensen & Young (2012) set out a general method
for consistent volume assessment of complex traps by considering combinations of trapping elements
being present or failing, assigning probabilities to those scenarios and deriving the resulting
leak-point outcomes. Their work makes a slightly counter-intuitive point that matters here: a deeper
leak point can be *less* probable, because it requires more trapping elements to remain effective.
That is competing-limits logic. Grant (2020) demonstrated Monte Carlo modelling of column heights
and introduced column-height control statistics; Lowry et al. (2005) described risk as a function of
column height.

What I have been trying to do is turn that thinking into a practical workflow, and combine it with
empirical data, depth-dependent risk and DHI evidence.

## Why not just blend the uncertainties?

Consider a fault with a 20 % probability of leaking at 2 200 m.

That does not mean the prospect's contact distribution should be shifted downward by 20 %. In 80 %
of realisations the fault is not the controlling mechanism. In 20 % it is.

That is a competing-limit problem, not a broader probability distribution.

The distinction looks small mathematically. It is rather important geologically — blending a leak
into the background column-height distribution suppresses outcomes *above* the leak, which is not
what a leak does.

## Then comes the empirical reality check

If we are building contact distributions from geological assumptions, we should ask whether they
look anything like what nature has actually done.

Edmundson et al. (2021) provide an unusually useful dataset: 242 NCS discoveries with trap height,
burial depth and hydrocarbon column height.

But there is a catch. **111 of the 242 — almost 46 % — are classified as filled to spill.**

A trap that filled to spill tells us the hydrocarbons reached the structural limit. It does not tell
us the maximum column the seal could have supported. The seal may have held another 50 m. Or 500 m.
We don't know.

Statistically, that is a **censored observation**: a lower bound, not a measurement. And the record
is bounded at the other end too, because we cannot know whether a contact existed up-dip of the
exploration well's reservoir entry.

That matters when using discovery data to infer what controls column height.

*[IMAGE: fig5_filled_to_spill.png — the filled-to-spill discoveries lie on a tight line, because
that line is the trap geometry, not the seal.]*

Fit the dataset conventionally and you get log-log elasticities of about **0.880 on trap height and
0.143 on burial depth**. Treat the filled-to-spill discoveries as censored and the same data gives
about **0.701 and 0.277**.

The exact values depend on the censoring definition, but the direction is robust: the naive
treatment gives too much weight to trap height and too little to burial depth. That is not
surprising — every filled-to-spill accumulation lies on the structural limit by definition, so the
regression is partly fitting an identity imposed by the geometry of the trap.

This does not make burial depth the dominant control. It means we should be careful about what the
discovery record is actually telling us.

Comparable non-public compilations from other basins point the same way, and also suggest something
worth taking seriously: there is a **regional base rate** of trap fill that belongs in the
construction of a contact distribution, not merely as a check afterwards.

## Statistics should challenge geological judgement, not replace it

I don't think the answer is *"forget geological judgement, use the statistics"*. Nor is it *"every
prospect is unique, so statistics are useless"*.

The useful question is: **how does my geological contact model compare with what has actually
happened in analogous traps?** Is it unusually optimistic? Unusually conservative? And, most
importantly, *which geological assumption is driving the difference?*

The empirical record is a sanity check, not an oracle.

## And then there is the DHI

Prospects capable of producing a DHI usually get an update to their probability of success, and the
anomaly may also constrain where the contact sits.

The tempting answer is: *"the DHI is at 2 210 m — put the contact there."*

But a DHI is evidence, not truth. At least two uncertainties matter: how likely is the event to
represent an actual contact, and where exactly is the contact it indicates? The real difficulty is
weighting true against false positives. And the **absence** of an anomaly does not mean the absence
of hydrocarbons, if the expected anomaly would have been below detection.

So a DHI should not replace the geological model. It should **update** it:

    P(HCWC | DHI)  ∝  P(DHI | HCWC) · P(HCWC)

The important part is not the equation. It is that the anomaly is treated as evidence carrying
uncertainty, rather than as a switch that fixes the contact at one depth.

*[IMAGE: fig6_dhi_updates_it.png — the geological curve and the same curve updated by the amplitude.
The evidence moves and sharpens it; it does not replace it.]*

### One caveat worth stating plainly

There is a trap in updating a geological POS with DHI evidence, and it is easy to walk into.

The geological POS is normally defined at a **crestal minimum volume** — the smallest accumulation
that would count as a discovery. The DHI, on the other hand, usually points at a contact well below
the crest.

Those are two different thresholds, and chance falls as the column grows: the probability of
reaching the DHI-inferred contact is **lower** than the probability of reaching the minimum-volume
criterion. Quoting a chance read at one threshold beside a volume read at the other is incoherent,
and it is easy to do when the chance arrives as a scalar from one tool and the volume as a
distribution from another.

The way out is to stop treating POS as a number and treat it as a **reading**. If everything is one
curve — the chance the column reaches at least *h* — then the minimum-volume chance and the DHI-case
chance are two points on the same curve, and they cannot drift apart.

*[IMAGE: fig4_risk_against_depth.png — chance against depth, and which mechanism is taking it away.]*

Which leads to the question that matters at the well: **a prospect can have a good chance of
containing hydrocarbons somewhere, and that does not mean the proposed well will encounter them.**
The chance should change with structural position.

## So perhaps we should stop choosing the distribution

We have become very good at making our models stochastic. More distributions. More Monte Carlo. More
P10s, P50s and P90s.

There is a danger of producing a beautifully stochastic answer to a poorly defined geological
question.

For contact uncertainty, the better question is: *what geological process is capable of stopping the
hydrocarbon column here?*

Answer that, and the distribution becomes an output of the geological reasoning. The P10, P50 and
P90 then have something behind them. Not just a shape — a reason.

*[IMAGE: fig3_the_distribution.png — the distribution, as an output.]*

## The tool

This is the thinking behind the **HCWC Distribution Builder** I have been building. It lets you
define the geological limits, assign probabilities and uncertainties, generate the contact
distribution from their competition, identify the controlling mechanism, examine risk as a function
of depth, compare the result against the empirical trap-fill record, and fold in DHI evidence.

The goal is not to replace geological judgement. It is to make the judgement explicit, testable and
traceable.

Because *"I used a lognormal because it looked about right"* is not necessarily bad science.

But *"these are the geological limits, these are my assumptions, and this is what they produce"* is
a much more interesting conversation.

---

**References**

Beha, A., Christensen, J. E. & Young, R. (2012). A general method for the consistent volume
assessment of complex hydrocarbon traps. *Journal of Petroleum Geology*, 35(1), 85–98.

Edmundson, I. et al. (2021). An empirical approach to estimating hydrocarbon column heights for
improved pre-drill volume prediction in hydrocarbon exploration. *AAPG Bulletin*, 105(12),
2381–2403.

Grant, N. T. (2020). Using Monte Carlo models to predict hydrocarbon column heights and to
illustrate how faults influence buoyant fluid entrapment. *Petroleum Geoscience*, 27(2).

Hood, K. C. (2024). *Hydrocarbon Column Heights*, Part 1 & Part 2. Rose & Associates.

Lowry, D. C., Suttill, R. J. & Taylor, R. J. (2005). Advances in risking exploration prospects.
*APPEA Journal*, 45(1), 143–158.
