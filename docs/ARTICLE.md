# Stop choosing a distribution for the hydrocarbon–water contact. Derive one.

**Draft for LinkedIn. Written to be argued with.**

---

Ask an explorationist where the hydrocarbon–water contact will be and you get a distribution. Ask
*why it is that distribution* and the answer is usually some version of "it looked reasonable", or
"that is what we used on the last one".

That is the wrong question being answered. The useful question is not

> *what is my HCWC distribution?*

but

> **what geological mechanism stops the hydrocarbon column at this depth — and what stops it if
> that one does not?**

Answer the second and the first falls out. The contact depth is not an input to be chosen. It is
the **outcome of a competition between mechanisms**, any one of which can arrest the column, and
only one of which wins in any given realisation of the subsurface.

## What is actually competing

Filling starts at the structural apex and works downward, so every limit below is a depth at which
the column could stop:

**Charge.** Source quality and maturity, generation and expulsion timing, migration efficiency and
carrier effectiveness, access to this particular trap, and phase behaviour. Charge that fills past
the deepest mapped point is not a shallow limit — it is *no* limit, and belongs in that mechanism's
probability of being active rather than as a contact at the base of the structure.

**Trap geometry.** Closure geometry and the spill point, with the uncertainty on the spill pick
carried explicitly; fault-bounded and wedge geometries; pinch-out and truncation ending the closure
down-dip; compartmentalisation.

**Top and base seal capacity.** Capillary entry pressure through pore-throat radius and seal
lithology — Schowalter's balance, `h_max = 2γcosθ(1/r − 1/R) / (gΔρ)` — plus seal thickness and
integrity. And note that this is *phase-dependent*: the same seal holds a much shorter gas column
than an oil one, because Δρ is in the denominator.

**Seal continuity**, which is a different failure from capillary breakthrough: a sand-filled
channel, an erosional window, a breaching fault tip.

**Lateral and fault seal.** Juxtaposition, fault-rock properties and SGR, membrane seal, the fault
leak point across all bounding faults, and reactivation.

**Regional and dynamic controls.** Post-charge tilt spilling part of a column or leaving a
palaeo-contact behind; hydrodynamic gradients; remigration and hydraulic reconfiguration.

**Reservoir.** Presence, continuity, quality and effective pore volume.

In each realisation, sample each of these, ask which are present, and take **the shallowest one
that is active**. Record which one won. Do it ten thousand times and you have a contact
distribution that is an *answer* rather than an assumption — and, because you kept the argmin, you
also have the thing a distribution alone can never give you: **which mechanism controls this
prospect, and how that changes with depth**.

Crucially, nothing is blended. Merging a leak into a background column-height distribution
suppresses outcomes *above* the leak, and can make apparent volume rise when you add a leak (Hood,
2019, 2024). A leak is a competing limit, not a downward nudge on a curve.

**That list is the geology. It is not a claim about what my implementation samples**, and the
difference matters if you are going to use it. Charge, spill and fault geometry, wedge and
pinch-out, top and base seal capacity and continuity, fault leakage and post-charge tilt are
sampled as competing limits. **Hydrodynamic tilting and remigration are not modelled at all** —
they belong on the list because they genuinely stop columns, and their absence is a stated
limitation rather than an oversight. Reservoir presence and effectiveness are carried as an
*element chance* rather than as a contact-moving limit, because a reservoir that is not there has
no contact to distribute; only its geometric end — the pinch-out — moves the contact.
Compartmentalisation is not modelled: it turns one contact into several, which is a different
object from the one this builds.

## The ideas are published. A working tool was not.

Almost none of the thinking here is mine, and saying so is not modesty — it is the reason to trust
the result.

**Hood (2019, 2024, ExxonMobil)** states the rule the engine implements: build the geological column
and each geometric limit as *separate* distributions and take the minimum per realisation. Merging
them into one weighted input, he shows, "produces non-geologic and erroneous results" — apparent
volume can *increase* when you add a leak.

**Beha, Christensen & Young (2012)** did it by hand. They enumerate the combinations of trapping
elements sealing or failing, weight each scenario, and collapse the result onto leak-point
frequencies. Their headline observation is the competing-limits principle, in print, in 2012:

> it is not intuitively obvious that a deep leak point can be statistically more likely than a leak
> point higher up the structure, although the deeper leak point requires more elements to seal
> simultaneously.

Their worked example — 0.60 / 0.12 / 0.28 at 2050 / 2100 / 2150 m — is reproduced exactly by this
tool's test suite, and is its only external validation.

**Grant (2020, ConocoPhillips)** is the closest prior art and goes furthest: Monte Carlo over fault
seal capacity, fault orientation, the regional stress tensor and trap geometry, referenced to the
crest, with juxtaposition *and* membrane seal, hydrodynamics and reactivation risk — and he already
publishes the controlling-mechanism diagnostic, under the name "column height control statistics".
**Lowry, Suttill & Taylor (2005)** had depth-dependent risk two decades ago.

So the engine is not the contribution. **Here is what I think is.**

**A working tool, in the open, that you can run on a prospect this afternoon.** Every one of the
references above is either a method paper or an in-house implementation. The published
implementations that do exist — the Petrel plug-in workflows Grant cites — need a 3D geomodel, and
Grant's own argument for his approach is that such a model "is not always available or built when
evaluating exploration prospects". That gap between a well-argued method and something an explorer
can actually use is the one this fills. *I have looked and not found an open tool that does this. If
one exists I would genuinely like to be pointed at it.*

**A correction to the benchmark everyone calibrates against** — the censoring above. I have not seen
it applied to this dataset.

**Per-element chance against depth, derived rather than allocated.** Because the engine records
which mechanism won in each realisation, each risk element gets its own chance-versus-depth curve
from its own group minimum. Grant publishes the aggregate; the per-element decomposition I have not
found in print.

One honest gap, and it is Beha's too: **whether** a mechanism is present is drawn independently, so
I can say that two faults leak at similar depths but not that they are the same fault and therefore
stand or fall together. Neither of us has solved it.

## Calibrate the answer against the record, and know the one trap in doing it

A derived distribution is not automatically a better one. It has to be checked, and there is
exactly one public dataset to check it against: **Edmundson et al. (2021)**, 242 NCS discoveries
with both column height and closure height, published under CC-BY.

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
seal could hold.** It is a **lower bound** — in survival-analysis terms a right-censored
observation — and treating it as a measurement is the error. **111 of the 242 are filled to spill.
Forty-six per cent of the record is censored, not measured.**

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
prospect. The derivation, the sensitivity of the third digit, and the argument for why a benchmark
can never inform the *chance* of a discovery — only where the contact sits — are in the tool.

## A DHI is evidence to be weighed, not a contact to be substituted

This is where the workflow earns its keep, and it is the second half of the argument.

The common treatment of a possible flat event is a scenario switch: *if* the DHI is valid, the
contact is at the flat spot; otherwise the geological contact stands. That is honest, it needs no
new elicitation, and it moves the contact **without moving the chance**. Hood's rule — merge late,
never blend into the input distribution — applies.

But it discards information. The order that uses it is:

1. **Build the geological HCWC distribution first**, from the competing mechanisms above. The DHI
   never edits it.
2. **State the depth of the interpreted flat event and its uncertainty** — flat-spot pick error
   *plus* depth conversion, and the second is usually the larger.
3. **State how detectable a column of a given height would be.** A thin column produces no anomaly;
   a thick one usually does. This detection function is what makes an *absent* anomaly usable
   evidence rather than a special case, since the likelihood becomes `1 − D(h)`.
4. **Update the distribution**, and therefore the depth-dependent chance, rather than replacing it.

On the precision of that word "update": the geometric channel **is** a Bayesian likelihood update.
The engine's realisations are draws from the prior, so weighting each by `L(seismic | h)` and
normalising is self-normalised importance sampling — posterior ∝ prior × likelihood, with the
controlling-mechanism bookkeeping surviving intact. The amplitude-character channel is a two-state
Bayes update in odds form, `posterior = R·prior / (R·prior + (1−prior))`.

**Combining the two channels is not Bayes, and I will not pretend it is.** Multiplying the two
likelihood ratios would assume the geometry of the anomaly and its character are conditionally
independent evidence. They are not, and neither are they the same evidence. So the implementation
interpolates between the product and the stronger single channel, with the dependence exposed as a
number you set. That is **probabilistic evidence weighting with a stated assumption**, not a
theorem, and it is labelled as such in the tool.

Two consequences worth stating. The likelihoods are **elicited, not calibrated** — the detection
function and the pick sigma are modelling choices, and a posterior is only as defensible as they
are. So the tool also plots what the answer is most sensitive to; when a typed seismic assumption
moves the contact further than the geology does, that is a finding about your assumptions, not
about the prospect.

## What this is all for

Column height, HCWC depth, spill point and seal capacity are four different quantities and it is
worth keeping them apart. The spill point is one *limit*. Seal capacity is another. The column
height is what the winning limit leaves you. The HCWC depth is the apex plus that column. And the
chance of success is a reading of the resulting curve at whatever minimum column you decided makes
the well a discovery — which is why a probability of success means nothing until you say what
counts as success.

Get the mechanism right and all four are consistent by construction. Choose a distribution because
it looks reasonable and none of them are.

The tool is free and open source: the competing-limits engine, the censoring-aware calibration
against the NCS record, depth-dependent risk per element, the DHI update, and an importer so a
company can run the same correction on its own trap-fill database without the data leaving the
browser.

It will not tell you whether to drill. It produces one input to that decision, honestly, with its
provenance attached.

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
