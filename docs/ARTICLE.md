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

## This idea is not mine, and saying so makes the case stronger

**Beha, Christensen & Young (2012)** set out a general method for consistent volume assessment of
complex hydrocarbon traps by enumerating the combinations of trapping elements being present or
failing, assigning a probability to each resulting scenario, and deriving the leak point that
follows. Their worked example — a faulted four-way with two faults at 2050 m and 2100 m and a
lowest closing contour at 2150 m — collapses four scenarios onto three leak points with
probabilities 0.60, 0.12 and 0.28.

Their own headline observation is the one worth quoting:

> it is not intuitively obvious that a deep leak point can be statistically more likely than a leak
> point higher up the structure, although the deeper leak point requires more elements to seal
> simultaneously.

That is the competing-limits principle, in print, in 2012. **It is one of the closest published
precedents for the engine I have implemented**, and the logic is theirs, not mine.

What I have built is an implementation and an extension. Beha et al. enumerate *discrete* leak
points by hand and explicitly assume no dependency between their two faults. I sample each
mechanism as a *continuous distribution*, which lets a seal capacity or a charge volume enter
directly rather than as a fixed depth; I let the mechanisms be correlated through a Gaussian copula
— including, deliberately, the apex against any depth-stated limit, since both are picked off the
same depth-converted surface; and I record the controlling mechanism per realisation. They are the
same model at two levels of generality, and their hand enumeration is exact where mine is a
simulation.

Others got there too. **Grant (2020)** published Monte Carlo column-height modelling with fault
effects and what he calls "column height control statistics" — the controlling-mechanism diagnostic,
already in the literature. **Lowry, Suttill & Taylor (2005)** built a variable risk array across
column heights for exactly the fill-to-spill-versus-seal-capacity case, which is depth-dependent
risk two decades ago.

So: the engine is not the contribution. What follows is.

## The empirical record has a hole in it, and it is a statistical one

If you calibrate a column-height model against discoveries — and you should — you run into
something that took me a while to see.

**A trap that filled to spill tells you what the closure could hold. It does not tell you what the
seal could hold.**

That sentence is deliberately blunt, and it needs one qualification. Such an observation is not
*uninformative* about seal capacity: it tells you the seal held **at least** the full closure. It is
a **lower bound** — in survival-analysis terms a **right-censored observation** — and the error is
to treat it as a *measurement* of the maximum seal-supported column. The seal might have held twice
that. Nothing in the observation distinguishes the two cases.

In **Edmundson et al.'s (2021)** open dataset of 242 NCS discoveries — published under CC-BY, which
is the only reason any of this is checkable — **111 are classified as filled to spill.** Forty-six
per cent of the record is censored, not measured.

Fit column height on trap height and burial depth the ordinary way, then fit it treating filled
traps as censored:

| | trap height | burial depth |
|---|---|---|
| ordinary least squares | 0.880 | 0.143 |
| censoring-corrected | **0.701** | **0.277** |

Censoring **inflates** the trap-height term — unsurprising, since a filled trap is a point where
column equals trap by construction, so a naive fit is partly fitting an identity. And it **halves**
the burial-depth term. "Burial depth is the weaker control" is a fair reading of the uncorrected
fit; it does not survive the correction.

*The third digit is not robust: the trap-height coefficient runs 0.720 / 0.701 / 0.697 as you move
the tolerance for "at its spill" from 0.5 m to 1 m to 2 m. The direction and size of the effect are.*

**The check that convinced me** needs no simulated data. Ask each fit to reproduce the one statistic
anyone can verify — how often a discovery fills to spill:

```
observed in the dataset        45.9 %
censoring-corrected model      47.2 %
the uncorrected relationship   32.1 %
```

The corrected fit reproduces the filling behaviour of the dataset it was fitted to. The uncorrected
one is out by fourteen points, in the direction the omitted censoring predicts. *(Both computed
exactly, both given the same residual spread so only the mean function differs — the choice less
flattering to my argument, since letting the naive fit keep its own narrower spread gives 24.1 %.)*

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
