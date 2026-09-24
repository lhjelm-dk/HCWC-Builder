# Building hydrocarbon–water contact distributions from competing geological limits and DHI evidence

### A stochastic framework with probabilistic DHI updating for pre-drill prospect assessment

**Lars Hjelm**

---

*This article documents a method and the open-source tool that implements it. Every figure is an
exhibit of the tool, exported unchanged by `scripts/export_exhibits.py`. Every number is produced by
`scripts/paper_facts.py` from the shipped prospect at the settings stated. The method is set out in
full in the tool's theory notes.*

## Abstract

Hydrocarbon–water contact (HCWC) depth is a major source of uncertainty in pre-drill prospect
evaluation and can affect in-place volume estimates by orders of magnitude. The complexity of the
processes controlling HCWC depth means that many assessments represent the uncertainty with a
generic distribution for contact depth or column height, based on analogue fields, regional
statistics, expert judgement, company standards, or a combination. This is practical. But a generic
distribution may over- or underestimate the potential of an individual prospect and hides which
geological mechanisms actually control the column.

Here, column-height uncertainty is derived from competing geological limits rather than specified
directly. Structural spill, charge limitation, top-seal capillary and mechanical capacity, seal
continuity, fault-seal leakage and reservoir pinch-out are represented as uncertain limits, each
with its probability of being active and its depth or capacity uncertainty. In each Monte Carlo
realisation, the shallowest active limit controls the column, and the controlling mechanism is
retained. The result is therefore both a column-height distribution and a record of what controls
it.

The same realisations provide the probability of reaching any column height or well depth, linking
HCWC uncertainty to depth-dependent probability of success and volumetrics without a separate
depth-risk elicitation.

Where seismic evidence indicates a possible HCWC, the DHI is treated as additional evidence rather
than as a deterministic contact. The DHI evidence index updates the probability of a
hydrocarbon-bearing accumulation, while the prospect-specific DHI geometry reweights the
conditional HCWC distribution. The resulting posterior is used for both HCWC prediction and
probability of success with depth.

An open-source application implements the workflow and provides the geological assumptions,
controlling mechanisms, DHI update and empirical benchmark in one assessment.

---

## 1 · Introduction

The assumed hydrocarbon column uncertainty propagates directly into prospect volume and probability
of well success. Despite its importance, HCWC is commonly represented by a distribution of possible
contact depths or column heights derived from analogue fields, regional statistics, expert
judgement, company policy, or some combination.

There is nothing inherently wrong with this approach. But it leaves a basic question unanswered:

> What geological process is represented by the selected distribution?

A hydrocarbon column is not a random variable in isolation. Its maximum extent is the outcome of
geological processes: structural spill, charge limitation, seal capacity, seal discontinuity, fault
leakage, reservoir geometry and, in some settings, post-charge processes.

A distribution can of course be derived from statistics of similar prospects. But is that
distribution appropriate for this prospect?

The alternative explored here is to represent the geological mechanisms that may limit the column
and let their competition generate the HCWC distribution. The distribution then becomes an output
of the geological model rather than an input. The same realisations also provide the probability of
reaching a given column height or absolute depth, linking HCWC uncertainty to depth-dependent
probability of success and well risk.

### 1.1 · From trapping elements to HCWC

The competing-limits concept is not new. Beha *et al.* (2012) described consistent volume assessment
of complex traps by considering combinations of trapping elements being present or failing and
deriving the resulting leak points. Hood (2019, 2024) described the stochastic treatment of column
height by sampling background column height and explicit geometric limits and taking the minimum.

The tool used here follows the same geological principle, but represents the limiting
mechanisms as probabilistic depth or capacity distributions. Charge limitation, structural spill,
fault leakage, seal capacity and continuity, mechanical seal failure and reservoir geometry can
therefore compete within each Monte Carlo realisation.

The shallowest active limit controls the column. The model retains that controlling mechanism, so
the result is not only a distribution of HCWC depths but also a record of what controls the column
and how that control changes with depth.

This is important for risking. The uncertainty is not only described; it is linked to a geological
mechanism that can be examined, challenged or potentially reduced with additional information.

### 1.2 · Incorporating DHI evidence

A DHI provides a different type of information. Its seismic character may provide evidence for
hydrocarbon presence, while its geometry may provide information about the position of the HCWC.

These are treated separately.

The DHI evidence index provides an evidence weight for the hydrocarbon-bearing state:

$$LR(s)=\frac{f(s\mid HC)}{f(s\mid NoHC)}$$

where $s$ is a conceptual DHI evidence index. Combined with the geological accumulation probability
$P(G)$, this gives an updated probability:

$$P(G\mid s)= \frac{LR(s)\,P(G)}{LR(s)\,P(G)+(1-P(G))}$$

The index is relative rather than physical: zero represents neutral evidence, positive values
increasingly positive evidence, and negative values increasingly negative evidence.

The prospect-specific DHI geometry is treated separately as evidence on column height. The
geological HCWC realisations are reweighted according to the likelihood of observing the DHI
geometry for each possible column height:

$$P(H\geq h\mid G,\,DHI)$$

The result is an updated HCWC distribution rather than a deterministic contact placed at the DHI
depth.

This distinction matters. A strong DHI may provide strong evidence for hydrocarbons while the HCWC
remains uncertain because of depth conversion, contact attribution, pick uncertainty or the
possibility that the seismic response is not a contact. Conversely, a deep DHI may support
hydrocarbon presence while still giving a relatively low probability that the column reaches the
minimum required at a particular well.

The same posterior realisations are then used to calculate the probability of reaching any depth.
The DHI therefore affects both the probability of an accumulation and the distribution of where the
hydrocarbon column may terminate, without creating a separate depth-risk model.

### 1.3 · Scope and contribution

The competing geological limits used here are established concepts rather than a new risking
principle. The aim is to combine them in a practical workflow in which geological assumptions
generate the HCWC distribution and the controlling mechanism is retained for each realisation.

The main focus is the integration of DHI evidence with that geological HCWC distribution. DHI
evidence strength updates the accumulation probability, while prospect-specific DHI geometry
updates the conditional HCWC distribution. The resulting posterior provides a common basis for HCWC
prediction, controlling-mechanism analysis and probability of success with depth.

Empirical column-height data are used as a supporting benchmark rather than as a replacement for
prospect-specific geological reasoning. The application is intended to make the assumptions behind
HCWC uncertainty explicit, traceable and testable.

---

## 2 · Column height as the outcome of competing limits

Consider a prospect in which several geological mechanisms may limit the hydrocarbon column. For a
given realisation let $H_\text{charge}$, $H_\text{spill}$, $H_\text{seal}$, $H_\text{continuity}$,
$H_\text{fault}$ and $H_\text{mech}$ be the maximum columns consistent with charge, structural
spill, capillary seal capacity, seal continuity, fault or lateral seal, and mechanical top-seal
failure.

The resulting column height is

$$H = \min\left(H_\text{charge},\,H_\text{spill},\,H_\text{seal},\,H_\text{continuity},\,H_\text{fault},\,H_\text{mech},\,\ldots\right)$$

Only mechanisms active in that realisation enter the minimum, so each carries two separate
uncertainties: whether it is active as a limit, and, given that it is, where it bites. An inactive
mechanism can simply be represented as having no finite limiting height.

A realisation does not contain a weighted average of several possible leak points. It is one
possible geological configuration, in which the first effective limiting mechanism determines the
maximum column. Repeating this over many realisations generates the HCWC distribution and the
statistics of which mechanism controls it.

This is also why a potential leak should not simply be blended into a background column-height
distribution. A leak changes the outcome only for realisations that reach the leak; it should not
reduce the probability of shallower columns. The competing-limit formulation does this by
construction: the background capacity and the geometric limit are sampled separately, and the
minimum is taken for each realisation. Hood (2019) illustrates the same problem, including cases
where representing a deep leak by reweighting the background distribution can produce the
counter-intuitive result of increasing prospect volume.

![The limiting mechanisms on a common column-height axis](figures/Figure_4.1.2e_one-axis-five-views-exceedance-curves-is-the.png)

> **Figure 1.** The limiting mechanisms for the worked prospect shown on a common column-height
> axis. The HCWC distribution results from taking the minimum of
> the active limits in each realisation. The plotted limit curves show the corresponding sampled
> constraints; the resulting contact is their realised minimum. No curve is elicited as an HCWC
> distribution.

A limit is not necessarily a leak point. Some limits represent an actual escape path, such as
structural spill, fault leakage or seal failure. Others limit the column without hydrocarbons
necessarily leaving the trap: charge may be insufficient to fill higher, or reservoir continuity may
terminate the connected pore volume. In all cases the relevant quantity is the maximum column that
can be supported in that realisation.

The distinction is about connectivity rather than the statistics of the depth distribution. A seal
capacity exceeded at 2 200 m only becomes an effective drainage limit if there is a connected escape
path from the accumulation. If the volume beyond the seal is itself closed, exceeding the local seal
capacity does not necessarily empty the trap. In the model, this has to be represented explicitly
through the mechanism activation, the presence of an escape path, or the sampled limiting depth.
Once that decision is made, the minimum assumes it has already been accounted for.

---
## 3 · Geological mechanisms

The limits should be defined in terms of geological processes rather than as arbitrary statistical
distributions. They should ultimately all resolve to the same quantity: metres of hydrocarbon
column. The input may naturally be either a capacity or a mapped depth. A **capacity** — what a seal
can hold, what a fault will leak past — is naturally stated in metres of column below the apex and
does not move when the apex pick moves; a **mapped surface** — spill point, juxtaposition window,
pinch-out — is naturally stated as a depth. The conversion between them uses the apex drawn in the same realisation, and that is where
a known bias enters: $H = z_\text{limit} - z_\text{apex}$ subtracts two picks from the same
depth-converted surface.

![Every mechanism that can stop the column, on one section](figures/Figure_1.1a_every-mechanism-that-can-stop-the-column-on.png)

> **Figure 2.** The mechanisms on one section, each with the distribution of the depth at which it
> acts. Charge enters from below and fills downward from the apex, so every capacity is
> measured from the apex. The figure is the elicitation: a limit is entered where its mechanism
> acts, not where a contact is wanted.

**Structural spill** is the maximum column the trap geometry retains. Depth conversion, seismic
interpretation, and closure, fault and pinch-out geometry all make it a distribution rather than a
fixed depth.

A related distinction is whether a distribution is **truncated by spill or terminated at spill**.
Truncating a background column-height distribution with a prospect-specific spill limit leaves the
probability of smaller columns unchanged and creates filled-to-spill realisations where the
background capacity exceeds the structural limit. Simply defining the distribution only below spill
changes the distribution of all smaller columns as well. The competing-limit approach gives the
former behaviour by construction.

**Charge limitation** applies where the available charge is insufficient to fill the trap to a
deeper limit. It should not automatically be represented as a contact at the base of the structure:
if charge fills the structure, it imposes no contact at all. Its column-height distribution can be
computed from an area–depth integration rather than elicited.

**Capillary seal capacity** gives another maximum column. In a Schowalter-type formulation,

$$h_\text{max} = \frac{2\gamma\cos\theta}{g\,\Delta\rho}\left(\frac{1}{r} - \frac{1}{R}\right)$$

where $r$ is an effective seal pore-throat radius and $R$ the reservoir pore scale, only the
*difference* having to be overcome. Capacity is dominated by the pore-throat radius, since
$P_c \propto 1/r$, and it is **phase dependent**: the density contrast means the same seal supports
a much shorter gas column than an oil one, so the charge phase and the seal fluid must be set
coherently or the contact belongs to no prospect.

**Seal continuity** is a different failure mechanism from capillary breakthrough: a seal may have
ample local capacity while being ineffective because of sand-filled channels, erosional windows or
local thinning, so it is its own mechanism with its own probability of presence.

**Fault seal** adds juxtaposition, shale gouge ratio, fault-rock properties, fault-zone architecture,
reactivation and discrete leak points. Fault *geometry* and fault *leakage* are different mechanisms
even on the same fault, and are separate limits in different risk elements.

**Mechanical top-seal failure** applies in sufficiently overpressured systems. Following Grant
(2020), the supportable column is $H = (S_{H\min} - P_p) / (\text{grad}_w - \text{grad}_h)$: the
headroom between minimum horizontal stress and pore pressure, over the difference in fluid gradients.
The limiting condition is rock failure under stress, not pore-throat entry pressure. Where the
headroom is spent before any hydrocarbon is added, the trap has failed rather than being limited:
that is a retention risk at the crest, not a zero-metre column.

A further question is what happens after mechanical failure. Does the seal heal? Is the accumulated
column lost permanently, or can the system recharge and rebuild it? That is a different problem from
defining the instantaneous failure limit, and needs to be treated explicitly if it is material to
the prospect.

---

## 4 · Monte Carlo implementation

For each realisation $j$, sample the uncertain geological parameters, including apex-depth
uncertainty; determine which limiting mechanisms are active; calculate the limiting column height
for each active mechanism; select the minimum; and **record both the resulting column height and the
controlling mechanism**.

The output is therefore not just $H_1,H_2,\ldots,H_N$, but the pairs $(H_j,M_j)$, where $M_j$ is the
mechanism controlling realisation $j$. The probability that mechanism $i$ controls the column is

$$P(M=i)=\frac{N_i}{N}.$$

This bookkeeping costs one integer array per realisation and is the point of the whole construction.
It distinguishes a mechanism that is *uncertain* from one that is actually *controlling*. Keeping
that information answers a different question from the HCWC distribution itself, and points directly
to what should drive further geological work.

Sampling is performed through each limit's quantile function. Correlation is imposed when the random
draws are generated: a Gaussian copula with a rank-correlation matrix specified by the assessor
allows correlated limits without requiring the individual limit definitions to know about each
other. Mechanism presence is treated separately from the correlation of the active limits; the
implications and limitations of this assumption are discussed later.

---

## 5 · One distribution: contact and risk against depth

The primary output is the probability that the hydrocarbon column reaches at least a specified
height,

$$F(h)=P(H\geq h\mid G)$$

where $G$ is the event that a hydrocarbon-bearing accumulation exists under the assessed geological
risk elements.

This conditioning matters. If there is no accumulation, there is no HCWC to distribute. The column
distribution therefore describes the **conditional geometry of an accumulation**, while $P(G)$
describes the chance that such an accumulation exists in the first place.

If the apex is at $z_\text{apex}$,

$$z_\text{HCWC}=z_\text{apex}+H$$

so the same realisations can be read directly in depth. For a well entering at depth $z$, the
corresponding chance of hydrocarbons is

$$P(G)\,P(z_\text{HCWC}\geq z\mid G).$$

If $h_\min$ is the minimum column required by the assessment, then

$$\mathrm{POS} = P(G) \times F(h_\min).$$

Both terms are necessary. $P(G)$ asks whether an accumulation exists; $F(h_\min)$ asks whether that
accumulation reaches the required column. Reporting $F(h_\min)$ as the prospect POS would therefore
ignore the geological chance $P(G)$.

![The chance against depth, and what makes it](figures/Figure_4.1.3a_the-chance-against-depth-and-what-makes-it.png)

> **Figure 3.** One distribution read in three ways. The conditional curve is the
> probability that the HCWC lies at or below each depth, given an accumulation; the prospect curve
> multiplies this by $P(G)$. The bars show the controlling limit by depth bin. In the worked
> example, $F = 98.7\,\%$ at the 120 m assessment minimum, giving a POS of 40.3 %; at the 2 250 m
> DHI pick, $F = 48.3\,\%$, giving 19.7 %. A quoted probability is therefore only meaningful
> together with the depth or column height at which it is read.

### The limits are the risk model

The important point is that prospect POS and the HCWC distribution are not separate assessments. The
limits define both. The distributions entered as column-limiting mechanisms are the geological
statement of how the chance of encountering hydrocarbons decreases with depth.

The same realisations that generate $F(h)$ generate

$$P(G)\,F(h)$$

at every depth. The per-element curves are derived from the same limiting realisations rather than
being allocated independently. Change a seal capacity, fault limit or spill distribution and the
contact distribution, well risk and volume range change together.

This avoids building one depth-dependent risk model for POS and another for HCWC and then trying to
reconcile them afterwards. There was only one model to begin with.

![Each element's chance against depth](figures/Figure_4.2.2a_each-element-s-chance-curve-derived-from-the.png)

> **Figure 4.** Each element's chance against depth, derived from the shallowest active limit within
> that element and scaled by its element chance. When the element-level limits are
> independent, the product of these curves reproduces the overall contact survival function. With
> correlated elements, that identity does not generally hold; the full Monte Carlo result remains
> the reference. The curves are therefore derived diagnostics for downstream use, not separately
> elicited risks.

---

## 6 · DHI evidence and geometry

### 6.1 · DHI evidence strength

Let $s$ denote a dimensionless DHI evidence index, with zero representing neutral evidence, positive
values increasingly supporting a hydrocarbon-bearing accumulation and negative values increasingly
contradicting it.

The evidence model is described by conditional densities,

$$f(s\mid HC) \qquad\text{and}\qquad f(s\mid NoHC)$$

which give the relative likelihood of observing a given evidence strength under the two states.
Their ratio gives the likelihood ratio,

$$LR(s)=\frac{f(s\mid HC)}{f(s\mid NoHC)}.$$

Applied to the prior accumulation probability,

$$P(G\mid s)= \frac{LR(s)P(G)}{LR(s)P(G)+1-P(G)}.$$

The evidence index therefore changes the probability of the geological accumulation state. It does
not directly define an HCWC.

The relationship is an evidence model rather than a universal physical law. The shape and strength
of the conditional densities depend on the underlying evidence and calibration basis, and should not
be interpreted outside their intended range.

### 6.2 · DHI geometry

The DHI geometry provides a second piece of information. A picked event at depth $z$ may be
consistent with a hydrocarbon contact, but both its position and its interpretation are uncertain.

For each geological realisation, the conditional HCWC distribution can therefore be reweighted
according to how compatible that realisation is with the observed DHI geometry. The result remains a
distribution of possible contacts rather than a deterministic contact pick.

This distinction is important. A strong DHI may provide strong evidence that hydrocarbons are
present while leaving substantial uncertainty in the actual HCWC depth. Conversely, a DHI whose
geometry is consistent with a deep contact may support hydrocarbon presence while still giving a low
probability that the accumulation reaches the minimum column required at the well.

### 6.3 · Combined DHI result

The two updates address different questions:

$$P(G) \rightarrow P(G\mid s)$$

updates the probability that an accumulation exists, while

$$P(H\geq h\mid G) \rightarrow P(H\geq h\mid G,\mathrm{DHI\ geometry})$$

updates the conditional column-height distribution.

The resulting prospect probability against depth is therefore

$$P_\mathrm{DHI}(z) = P(G\mid s)\, P(z_\mathrm{HCWC}\geq z\mid G,\mathrm{DHI\ geometry}).$$

The same posterior realisations can be used to calculate the DHI-updated HCWC distribution,
depth-dependent well risk and threshold POS. No separate depth-risk model is required.

---

## 7 · Empirical benchmark and QC

The column-height distributions are built from the geological model, not fitted to an empirical
dataset. An empirical record nevertheless provides a useful QC check: does the resulting range sit
within what has been observed in comparable settings, and where it does not, which geological
mechanism might explain the difference?

Edmundson *et al.* (2021) compiled 242 Norwegian Continental Shelf discoveries with hydrocarbon
column height, trap height, burial depth and trap-fill ratio. Their dataset provides a benchmark
rather than a substitute for prospect-specific geological assessment.

![Column height against closure height, with the filled-to-spill discoveries marked](figures/Figure_6.2a_column-height-against-closure-height-after.png)

> **Figure 5.** Column height versus closure height for the Edmundson *et al.* (2021) dataset.
> Filled-to-spill discoveries are right-censored: they show that the column reached at least the
> trap height, but do not measure the maximum column the seal could support. Any empirical benchmark
> therefore needs to state how these observations were treated. The three violins are all at this
> prospect's closure height; the geological and DHI ones are nudged either side of the empirical
> prior only so they can be read.

A filled-to-spill discovery tells us that the observed column reached the structural limit; it does
not tell us that the seal would have leaked at that depth. This matters when using the dataset as a
benchmark for seal-supported column height. The comparison should therefore state how filled-to-spill
observations were treated rather than silently treating them as exact capacity measurements.

The purpose of the comparison is not to identify a "true" empirical column-height distribution. It
is a QC check on the prospect model. A material disagreement should trigger a geological question:
is the prospect outside the observed range, or is one of the assumed limiting mechanisms poorly
constrained?

---

## 8 · A worked prospect example — a practical approach

The tool ships with a worked conceptual prospect to illustrate the concepts. This tool offers a
computed charge fill and top-seal capacity, and estimation of fault geometry challenges,
fault leakage probability and fault seal retention distribution, seal continuity and preservation
limits. Element chances are charge 0.90, closure 1.00, reservoir 0.63 and retention 0.72, giving
$P(G) = 0.408$; the assessment minimum is 120 m of column. All results below are 10 000
realisations at the tool's default seed.

![Fifty realisations of the competition, and the distribution they belong to](figures/Figure_4.1.1a_the-competition-realisation-by-realisation.png)

> **Figure 6.** The competition, realisation by realisation. Left: fifty consecutive realisations,
> each coloured dot one limit's sampled depth, the ringed dot the controlling minimum. No limit wins
> consistently. Right: the contact distribution those minima make, with its exceedance curve on the
> top axis. The shape is an output; nothing about it was elicited.

| | |
|---|---:|
| $P(G)$, element product | 0.408 |
| $F(h_\min)$ at 120 m | 0.987 |
| **Prospect POS** | **40.3 %** |
| HCWC P90 / P50 / P10 | 2 191 / 2 248 / 2 327 m |
| P(filled to spill) | 3.5 % |

![The controlling mechanism at each depth](figures/Figure_4.1.2a_the-controlling-mechanism-at-each-depth.png)

> **Figure 7.** The controlling limit at each depth: the contact distribution stacked by the limit
> that set it, so each depth bin shows which mechanisms stop the column there. Over the realisations
> that meet the assessment minimum, top-seal capillary capacity sets the contact in 33 %, fault
> leakage in 23 %, seal continuity in 16 %, fault geometry in 14 %, charge in 10 % and spill in 4 %,
> the remaining limits in under 1 % each. The share is **not constant down the structure**: shallow
> contacts are almost entirely seal-controlled, deeper ones pass to fault geometry and finally to
> spill, which is the diagnostic a distribution alone cannot provide.

These are controlling-mechanism statistics and display how often each mechanism sets the minimum.
They also indicate what refinements are worth doing: refining the preservation model would move very
little here, because it controls under 1 % of realisations, while refining the seal-capacity
elicitation would move a great deal. A small overall share is not unimportance, though — Figure 7
shows fault geometry controlling a large fraction of the *deep* realisations, which are the ones
that carry the volume.

---

## 9 · Incorporating seismic evidence

One way to handle a seismic indication such as an apparent DHI is to define a separate "DHI case"
and substitute its contact depth for the geological HCWC distribution. This keeps the two
assessments separate, but treats the seismic interpretation as a scenario rather than as evidence.

A Bayesian update takes a different approach. The geological model already gives a set of possible
outcomes, each equally likely by construction. The seismic observation then changes how much weight
is given to those outcomes. Realisations that are more consistent with the observation become more
likely; those that are less consistent become less likely.

In simple terms,

$$P(H\mid D)\propto P(D\mid H)\,P(H)$$

where $H$ represents a possible geological outcome and $D$ the seismic observation. The prior term,
$P(H)$, is what the geological model thought was possible before considering the DHI. The likelihood
term, $P(D\mid H)$, asks how plausible the observed seismic response would be if that particular
geological outcome were true.

Because the Monte Carlo realisations are already a sample from the geological model, no new
geological simulation is needed. Each realisation is simply given a new weight according to how well
it matches the seismic observation — self-normalised importance sampling, which for this sample is
an exact Bayesian update conditional on the observation model. The set of possible realisations
stays the same; only their relative importance changes.

This is useful for more than just producing an updated HCWC distribution. Each realisation still
carries the geological mechanism that controlled its column. After the DHI update, the model can
therefore ask not only where the contact is likely to be, but also which geological mechanisms are
now most likely to control it. A simple "DHI case" cannot provide that information.

The same realisations also make the geological and DHI-updated distributions directly comparable.
The prior and posterior differ only in their weights, not in the underlying set of geological
possibilities.

There is one important boundary in the calculation. The HCWC realisations describe the column given
that a hydrocarbon-bearing accumulation exists. The seismic geometry can therefore redistribute
probability between possible column heights, but it does not by itself determine whether the
accumulation exists. That question is handled separately by the DHI evidence strength of Section 6.1.

The two pieces then combine as

$$P_\mathrm{DHI}(h) = P(G\mid s)\, F_\mathrm{post}(h)$$

where $P(G\mid s)$ is the updated probability of a hydrocarbon-bearing accumulation and
$F_\mathrm{post}(h)$ is the DHI-updated probability that the column reaches height $h$.

Each piece of seismic evidence is therefore used for the question it actually addresses: character
updates the chance of hydrocarbons; geometry updates where the column may terminate.

![The model as two rows: the geological prior, and the DHI as evidence](figures/Figure_8.1.1a_the-model-as-two-rows-the-geological-model.png)

> **Figure 8.** The assessment workflow. The geological model is the prior: element chances give
> $P(G)$, and given an accumulation the HCWC limits compete. The DHI is evidence: the evidence index
> — how strongly the amplitude character supports hydrocarbons — updates $P(G)$, and the apparent
> DHI contact geometry reweights the same realisations, so neither piece of evidence is counted
> twice. Both rows end in the same reading — the chance of meeting the threshold at the assessment
> minimum (POS geological, or POS given the DHI) and at any depth.

---

## 10 · Seismic geometry and seismic character

A seismic indication such as an apparent DHI can provide two different kinds of information. They
answer two different questions, so treating everything as one "DHI factor" can hide what the seismic
evidence is actually telling us.

**Geometry.** The position of an apparent flat event, together with its picking and depth-conversion
uncertainty, gives information about where the hydrocarbon column may terminate. This constrains
$H$, the column height.

**Character.** Amplitude, polarity and phase, conformity, AVO behaviour and consistency with the
expected fluid response give information about whether the seismic response is consistent with
hydrocarbons at all. This constrains the probability of a hydrocarbon-bearing accumulation, $P(G)$,
through the DHI evidence index described in Section 6.1.

The two therefore need not give the same answer. A strong seismic response can increase confidence
that hydrocarbons are present without fixing the contact depth. Conversely, a well-defined flat
event can constrain the contact position even when the evidence for hydrocarbons is relatively weak.

To illustrate the separation: when the geometry is made deliberately uninformative, the DHI
character can increase the prospect POS significantly while the contact distribution is essentially
unchanged. When the character is neutral and the geometry is informative, the contact distribution
becomes narrower while the overall prospect chance changes very little. When both are used, both
effects are present. Character and geometry often point in the same direction, since both improve
with data quality and impedance contrast; where they do not, the disagreement is information worth
reporting rather than an error to reconcile.

The distinction is therefore structural rather than just a convenient way of arranging the
calculation: character updates the chance of an accumulation; geometry updates where the column may
terminate.

![The pick against the geology](figures/Figure_5.1.1a_blue-is-the-geological-contact-distribution.png)

> **Figure 9.** The two inputs of the geometry channel. Blue is the geological contact distribution
> from the competing limits; red is the interpreted event with its uncertainty. Here the pick is
> about five times sharper than the geology and sits near its median, which is why it narrows the
> answer without moving it.

### 10.1 · What the geophysicist has to supply

The tool needs three inputs that are already part of normal seismic interpretation.

First, the depth of the interpreted event and its uncertainty. This includes both picking
uncertainty and depth-conversion uncertainty. Together they describe where the apparent contact
might actually be.

Second, the probability that the picked event is the HCWC at all, written $c$. A flat event may be a
real fluid contact, but it may also be a lithological boundary, processing artefact or another
seismic event. The parameter $c$ describes this attribution uncertainty given that hydrocarbons are
present.

Third, a detection function $D(h)$: the probability that a hydrocarbon column of height $h$ would
produce a mappable seismic anomaly.

The detection function is normally small for columns below seismic resolution, increases as the
column becomes easier to detect, and eventually approaches a ceiling below 1. It is deliberately not
allowed to reach certainty. Otherwise, an absent anomaly could become infinitely strong evidence
against a particular column height.

The tool uses a simple logistic form for $D(h)$. This is a practical detectability model, not a
physical seismic model. Being monotone, it also cannot represent a response that weakens again with
thickness, as a Class III sand's can when the top and base responses separate.

No new geological risk elements are required and the geological Monte Carlo simulation is not rerun.
The seismic information is applied to the existing geological realisations.

### 10.2 · The second question is not the first one restated

It is tempting to derive $c$ directly from the strength of the DHI: if the anomaly is bright and
convincing, surely the event bounding it is also likely to be the HCWC.

The distinction is useful because these are actually two different judgements. The split below is
drawn here, across the five DHI attributes Monigle *et al.* (2025) grade into a single score.

Body attributes such as anomaly strength and lateral amplitude contrast mainly address:

> Are hydrocarbons likely to be present?

These are the attributes reflected in the DHI evidence index and $P(G\mid s)$.

Contact attributes such as fit to structure, flatness, amplitude termination and evidence for a
fluid-contact reflection address:

> Is this particular event likely to be the HCWC?

These determine $c$.

The two judgements are related. Better data and stronger impedance contrast may improve both. But
they do not have to. A bright anomaly can have a poor or irregular termination and therefore a low
$c$. A weak anomaly can have an exceptionally flat, conformable event that gives relatively high
confidence that the event is the contact.

That is why $c$ should not simply be calculated from the DHI likelihood ratio. For example,

$$c=\frac{LR}{LR+1}$$

looks like a natural conversion of likelihood ratio to probability, but it is actually the posterior
probability from an even prior. $c$ is a different quantity: it is the probability
that the picked event is the contact conditional on hydrocarbons being present.

The evidence for hydrocarbons therefore belongs in the first part of the calculation, while the
evidence that the picked event is actually the contact belongs in the second. Keeping the two
separate prevents the same seismic observation from being counted twice.

Monigle *et al.* (2025) describe an empirical relationship between a multi-attribute DHI score and
the weight given to a DHI-indicated contact in their own scenario construction. The tool
shows that relationship as a comparison, not as a calibration of $c$ for the present model.

### 10.3 · When does detectability matter?

The detection function $D(h)$ can look like an important part of the seismic model, but its effect
depends strongly on the situation.

For a seen anomaly, detectability may add relatively little when all columns of interest are already
well above the detection threshold. That is the case in the worked prospect: with a detection
midpoint of 25 m and an assessment minimum of 120 m, essentially all relevant realisations lie on
the upper part of the detection curve. Changing $D(h)$ therefore has little effect on the result.

In this case, the more important uncertainty is whether the picked event is actually the contact.
The contact-attribution parameter $c$ determines how strongly the seismic pick is allowed to favour
some depths over others. On the worked prospect the difference is plain: replacing $D(h)$ with a
constant leaves the exceedance curve unchanged, while removing the floor that $c$ places under the
pick likelihood moves it by up to 22 points of exceedance (Section 14.1).

Detectability becomes more important in two situations.

First, when the anomaly is absent. A missing anomaly can then provide negative evidence: a large
column that should have been easy to detect becomes less likely. Within the hydrocarbon-bearing
state this is represented by

$$P(\text{no DHI}\mid h,G)=1-D(h).$$

This is discussed further in Section 12.

Second, detectability matters when the detection threshold falls inside the range of column heights
supported by the geological model. In that situation, seeing an anomaly provides information not
only about whether hydrocarbons are present, but also about how large the column is likely to be.

The practical point is therefore simple: do not assume that detectability is always the dominant DHI
uncertainty. Check where the detection threshold sits relative to the geological column-height
distribution, and check the contact attribution $c$. In the worked prospect, the latter matters more
for a seen anomaly.

---

## 11 · Evidence reshapes the HCWC distribution rather than scaling it

A seismic observation does more than simply increase or decrease prospect POS by one factor. The
character part of the evidence changes the probability that hydrocarbons are present, while the
geometry part changes which HCWC outcomes are more or less likely.

This means that the seismic update can change the shape of the column-height distribution, not just
its overall level. A DHI near a particular depth can increase the probability of contacts around
that depth, while reducing the probability of contacts that are less consistent with the
observation.

![The chance against threshold, geological and updated](figures/Figure_5.1.5a_the-chance-against-threshold-p-g-f-h.png)

> **Figure 10.** The chance of reaching each depth, before and after the seismic update, for a pick
> centred near 2 250 m with $c = 0.36$: $P(G) \times F(h)$ geological against
> $P(G \mid s) \times F(h \mid G, \text{geometry})$ updated. The evidence index updates the
> probability of a hydrocarbon-bearing accumulation, which scales the curve; the geometry then
> reweights the possible HCWC depths, so realisations compatible with the interpreted event receive
> more weight and less compatible depths receive less. At the assessment minimum the prospect chance
> goes from 40 % to 64 %; read off the same curves at 2 230 m, a well entering there goes from 23 %
> to 49 %.

Read as depth-dependent risk, the effect is no longer a simple upward shift of the POS curve. The
chance of reaching depths around the interpreted contact increases, while the chance at depths
beyond the part of the distribution supported by the DHI can decrease.

That is the important difference from applying a single POS multiplier. A multiplier changes the
level of the curve but leaves its shape unchanged. A scenario switch has a different problem: it
replaces one interpretation with another rather than updating the probabilities within the
geological model.

The likelihood-based approach does both things in the same calculation: the evidence index changes
the overall chance of an accumulation, while the DHI geometry changes the conditional distribution
of possible column heights. The result can therefore move the expected contact, narrow the
uncertainty, or move and narrow it at the same time.

The worked prospect shows all three effects depending on the seismic input. In the example shown
here, the strongest effect is to concentrate the contact distribution around the interpreted event.
The numerical consequences are read directly from the depth-risk curve in Figure 10.

Because the update is a reweighting rather than a replacement, the geological model remains intact.
The same geological realisations are still present, with the same competing limits and controlling
mechanisms; the seismic evidence simply gives some realisations more weight than others. The limits
are therefore still the risk model, now read at the posterior weights.

![The limits on one axis, given the DHI](figures/Figure_5.2.2e_one-axis-five-views-exceedance-curves-is-the.png)

> **Figure 11.** The competing limits after the seismic update. The same geological limits and
> realisations are retained, but they are reweighted according to how well their resulting HCWC is
> supported by the DHI geometry. The contact is still the minimum of the active limits; the seismic
> evidence changes the relative weight of the possible geological outcomes.

![The chance against depth given the DHI](figures/Figure_5.2.3a_the-chance-against-depth-and-what-makes-it.png)

> **Figure 12.** The updated result in the same form as Figure 3, so the geological and DHI-updated
> results can be compared directly. The conditional HCWC distribution and the probability against
> depth are derived from the same posterior realisations. They therefore move together: when the
> seismic evidence changes which contact depths are more likely, it changes both the HCWC
> distribution and the chance of reaching each depth.

---

## 12 · Absence as evidence

The detection function is what lets an *absent* anomaly enter the update at all. If a column of
height $h$ should have produced a mappable anomaly and none is present, the likelihood within $G$ is
$1 - D(h)$, which is largest at small $h$. No special handling is required.

What that can do is bounded by Section 9: within $G$, absence redistributes probability among column
heights and says nothing about whether there are hydrocarbons. On the worked prospect the
redistribution is nil, every column above the assessment minimum sitting on the detection ceiling;
move the midpoint to 150 m and the median contact shallows from 2 248 m to 2 197 m, with the
effective sample down to 5 243.

**Absence on the chance needs one more number.** Monigle *et al.* (2025) treat an absent anomaly as
a negative line of evidence within an integrated chance-of-success framework, while noting that the
practice "is not consistently applied in industry". The likelihood ratio on $G$ is
$R_\text{absent} = (1 - d) / (1 - f d)$, where $d$ is $D(h)$ averaged over the geological columns —
the chance a hydrocarbon-filled trap of the modelled geometry shows, 0.90 here — and $f$ is the
chance a barren trap shows an anomaly of the same class, stated *relative* to $d$ so that the ratio
behaves at the ends and never rises above one: absence never counts *for* hydrocarbons.

$f$ is elicited, and no calibration is known. The tool opens at the maximum-ignorance
$f = 0.5$ and labels it as such, giving $R_\text{absent} = 0.18$ and a prospect POS of 11.0 % against
40.3 % before; at $f = 0$ it is 6.4 %, and at $f = 1$ the chance is untouched. The narrower claim is
the column-height route, which the chance axis cannot reproduce: where the detection threshold falls
inside the range of geological columns, absence reshapes the contact distribution toward the short
columns that would not have shown. A negative reading of the evidence index is a different
observation again, and the two are not combined.

---

## 13 · Seismic uncertainty and the effective sample size

The influence of the evidence depends on the stated uncertainty of the interpretation: a broad
likelihood leaves the geological prior substantial influence, while a sharp one concentrates the
posterior on a narrow range of column heights, and the answer can become dominated by the seismic
observation.

**That is not a defect.** A well-imaged, conformable flat spot at a confidently picked depth is
better evidence about where the contact sits than any elicited seal capacity, and a model that
refused to let it win would be wrong. The requirement is that the displacement be *visible* rather
than discovered afterwards, and the diagnostic is Kish's effective sample size,
$\text{ESS} = \left(\sum_i w_i\right)^2 / \sum_i w_i^2$, which reports how many of the original
realisations the posterior effectively rests on:

| interpretation | prospect POS | contact P50 | P90–P10 | ESS |
|---|---:|---:|---:|---:|
| geological prior | 40.3 % | 2 248 m | 136 m | 10 000 |
| mild — index 5, $\sigma$ 15 m | 46.4 % | 2 251 m | 105 m | 6 163 |
| moderate — index 20, $\sigma$ 10 m | 63.9 % | 2 250 m | 105 m | 4 857 |
| strong — index 40, $\sigma$ 5 m | 82.0 % | 2 250 m | 106 m | **3 006** |
| absent where one was expected, $f = 0.5$ | 11.0 % | 2 248 m | 136 m | 9 978 |

A low ESS does not mean the interpretation is wrong; it means the posterior depends heavily on it.
At 3 006 the answer rests on under a third of the geological realisations, and the number belongs
beside the result rather than in an appendix. It reports the geometry channel only: the evidence
index updates a single number and throws no realisations away, which is why the chance can reach
82.0 % on the strong row at the ESS of a neutral index at the same pick, and why the absent row moves
the chance with nothing reweighted at all.

---

## 14 · What the evidence cannot override

Two constraints bound the update, and they are different in kind.

### 14.1 · The likelihood floor

The pick likelihood carries a floor, $L \geq (1 - c)\,s$, where $c$ is the chance that the picked
event is the hydrocarbon–water contact given that there is hydrocarbon for it to be the contact of,
and $s$ is the density of a spurious event over the model's contact range. A flat event can be
lithology, a diagenetic front, fizz gas read as pay, or a processing artefact, and the floor is where
that possibility lives — Cromwell's rule made operational, since a bounded pick shape would otherwise
assign probability zero below its deepest bound, and no later evidence can revive a zero.

What the floor guarantees is worth stating precisely, because it is easy to overstate. No depth's
likelihood falls below $1 - c$ times the flat alternative, so no contact depth is ever excluded and
an attributed contact cannot become certain. It does **not** cap how strongly the geometry
discriminates between two depths: that ratio is at most
$1 + c\,D\,\text{Pick}_{\max} / \left((1 - c)\,s\right)$, which grows as the pick narrows — about
8 : 1 on the worked prospect at $c = 0.36$ with a 10 m pick, and about 32 : 1 at $c = 0.70$.

Its behaviour under a pick the geology considers implausible is instructive. Holding the index
strong (40) and the pick sharp ($\sigma = 5$ m), and moving the indicated contact deeper:

| indicated contact | prospect POS | contact P50 | P90–P10 | ESS |
|---|---:|---:|---:|---:|
| 2 250 m — well supported | 82.0 % | 2 250 m | 106 m | 3 006 |
| 2 300 m | 82.0 % | 2 296 m | 110 m | 2 943 |
| 2 350 m | 81.8 % | 2 279 m | 160 m | 3 372 |
| 2 500 m — beyond all support | 81.5 % | **2 248 m** | 136 m | **10 000** |

The contact follows the pick while the geological model supports it, then **detaches**. At 2 500 m
the median is the prior's exactly and the effective sample is back to 10 000: the likelihood has gone
flat, and the model has concluded *that is probably not a contact* rather than *the contact is at
2 500 m*. The ESS is **not monotone** — it dips as the evidence sharpens against the prior, then
rises as the floor takes over — so it is read alongside the answer rather than as a quality score.
POS stays at 81–82 % throughout, which is correct: a bright anomaly is evidence for hydrocarbons even
when the interpreter has mislocated the contact.

Where the contact turns out to lie, relative to the band the pick defines, also names what the DHI
was, which is the post-well reading:

![What the DHI can turn out to have been](figures/Figure_5.1.4b_the-outcomes-of-a-seen-dhi-in-depth-order-as.png)

> **Figure 13.** The outcomes of a seen DHI in depth order, as shares of all outcomes.
> The first is off the depth axis: no hydrocarbons, the DHI a false hydrocarbon indicator. The four
> others share $P(G \mid s)$: the contact above the indicated contact band, within it because the DHI
> is the contact, within it by coincidence, and below it.

![The outcomes with their chances](figures/Table_5.1.4c_the-outcomes-with-their-chances-summing-to.png)

> **Table 1.** The same outcomes as numbers, at the scenario this paper reads throughout. The two rows
> within the band are separated by the branch of the likelihood that put the contact there: the
> posterior attribution — the chance the DHI is the contact, given the geology as well — is 0.47
> against a stated $c$ of 0.36, because the pick landed where the geology already expected a contact.

### 14.2 · Attribution between risk elements

A fluid indicator senses whether a reservoir with hydrocarbons exists and, more weakly, what fluid
fills it. It does **not** identify which of charge, closure, reservoir or retention would otherwise
have failed. The update may therefore move the total chance and the contact, and may **not**
re-attribute risk between elements: a bright spot does not retrospectively improve a charge argument.
In the tool the element chances are set once, and nothing in the DHI workflow can edit
them.

This is published practice rather than a local convention — Monigle *et al.* (2025) state that
geological risking must remain independent of the DHI attributes, and that "the presence of a DHI
does not increase the chance of adequacy of source presence; the adequacy of source is determined by
considering the geologic factors alone" — and it is the practical guard against double counting, a
DHI being read simultaneously as evidence for charge, reservoir presence, seal quality and contact
depth.

---

## 15 · Dependence between the two channels

Separating geometry from character raises an apparent problem: the two observations are not
independent, since a strong anomaly is more likely to produce a clearly mappable termination than a
weak one. In the arithmetic it does not arise, because the two channels are not ratios on the same
hypothesis: the evidence channel is a likelihood ratio on $G$, the geometry channel a likelihood over
$h$ within $G$. Each factor is updated once by the evidence that bears on it, and the product is the
chain rule, not an independence assumption.

The dependence that remains is between the two *judgements*. The characteristics that grade $c$ are
also the ones the published drilled-prospect rankings put first for finding hydrocarbons — amplitude
conformance to structure, flat spots among the most definitive (Roden *et al.*, 2012; Nixon *et al.*,
2018) — so an assessor who grades the conformance strongly is likely to read the index higher too.
That is a matter for the elicitation, not for the arithmetic, which cannot tell a correlated pair of
honest judgements from an uncorrelated one.

For scale: Kjønsberg *et al.* (2010) inverted prestack AVO by Markov chain Monte Carlo offshore
Norway, and the implied likelihood ratio at the prospect centre was about **29**, at a location later
drilled and found gas. A careful inversion on good data buys roughly a factor of thirty, carrying
amplitude and geometry together; the evidence channel here is bounded at 10 either way, after Simm
(2020).

---

## 16 · Limitations

The framework is deliberately simplified and is not a basin or reservoir simulator: hydrodynamic
gradients, remigration and palaeo-contacts, compartmentalisation, three-dimensional fluid-flow
simulation and pressure-history modelling are not represented.

**Mechanism presence is drawn independently.** Limit *depths* can be correlated through the copula,
but whether a mechanism is present is an independent Bernoulli draw per limit — a strong assumption
where the presence of one implies another, as with faults sharing a reactivation history. The element
chances are likewise multiplied as conditionally independent inputs.

**Two-phase columns are handled through charge, not through seal capacity.** Where both a gas–oil
and an oil–water contact are controlled by capillary leak, one top seal is in contact with gas at the
crest and oil on the flanks, and the two legs are limited by different entry pressures. That
construction is not implemented.

**The seismic likelihood is a modelling assumption, not a measurement.** Every term in it is a
convention or an elicited judgement: the detection function's form and parameters, the pick shape and
width, the contact attribution $c$, the uniform density of a spurious event. The Bayesian arithmetic
is exact conditional on that observation model; the model is the assumption. This is why the
effective sample size and the sensitivity to each seismic input are reported — when a typed
assumption moves the contact further than the geology does, that is a finding about the assumption —
and the false-positive rate of Section 12 is uncalibrated in particular.

These limitations do not invalidate the framework. They define where additional modelling is
required.

---

## 17 · Discussion and conclusions

The principal advantage is conceptual rather than computational. A directly elicited HCWC
distribution asks the assessor to specify the final uncertainty; the competing-limits approach asks
them to specify the mechanisms that produce it, and those mechanisms mean different things —
geometry, retention against buoyancy, lateral containment, petroleum-system uncertainty, a stress
condition. Once each is a competing limit, the contact distribution is an emergent property of the
model rather than an input to it, and so is the chance of success at every depth.

The construction separates *what is uncertain* from *what controls the outcome*: a mechanism may
carry considerable uncertainty and little influence, if it rarely provides the minimum, while a
narrow uncertainty in a dominant mechanism moves the whole distribution. The assessment therefore
retains an explanation of its own answer, which makes it defensible under review and auditable after
drilling, when a dry hole or an unexpectedly small discovery can be evaluated in terms of the
mechanism that was misassessed rather than by asking why an HCWC distribution was too deep.

The seismic extension follows the same principle. A DHI is not a distribution over the contact; it
is an *observation* of one, and treating it as a likelihood over column height keeps the geological
model intact underneath while making the extent of its influence a reported number.

In summary:

1. **Column height can be derived rather than specified.** The maximum column in each realisation is
   set by the shallowest active geological limit, and the distribution is the output.
2. **The limits are also the risk model.** HCWC depth, the chance at any depth and the commercial
   discovery probability are readings of one curve, with $\text{POS} = P(G) \times F(h_\min)$, and
   the per-element curves come from the same limits. The conditional term alone overstates the
   prospect by $1/P(G)$.
3. **Controlling mechanisms can be identified explicitly.** Recording the argmin turns a distribution
   into a diagnostic of which uncertainties influence the assessment, and how that changes with depth.
4. **How the distribution meets the spill point is consequential.** Truncating a background
   distribution by an independently sampled spill produces filled-to-spill cases at a rate the seal
   implies; terminating it at spill does not.
5. **Empirical discovery data require care.** Filled-to-spill discoveries are lower bounds on seal
   capacity rather than measurements of it, and column height and trap height share the apex pick.
6. **Seismic evidence can be incorporated as evidence.** Likelihood weighting requires no
   re-simulation, preserves the mechanism attribution, and reshapes the depth-dependent risk rather
   than scaling it. Each piece of evidence enters once, in the factor it is evidence about; the
   effective sample size reports how far the geometry has displaced the geology; and the floor
   ensures that one interpretation can never rule the geology out.

The objective is not a more sophisticated distribution for its own sake. It is to make the
distribution a consequence of explicit geological assumptions — so that it can be defended, reviewed,
and corrected after drilling. An open-source application applies these concepts during prospect
evaluation without requiring a three-dimensional geomodel. It does not determine whether a prospect
should be drilled; it gives a transparent representation of one of the key uncertainties informing
that decision.

---

## References

Beha, A., Christensen, J. E. & Young, R. (2012). A general method for the consistent volume
assessment of complex hydrocarbon traps. *Journal of Petroleum Geology* **35**(1), 85–98.

Edmundson, I., Davies, R., Frette, L. U., Mackie, S., Kavli, E. A., Rotevatn, A., Yielding, G. &
Dunbar, A. (2021). An empirical approach to estimating hydrocarbon column heights for improved
pre-drill volume prediction in hydrocarbon exploration. *AAPG Bulletin* **105**(12), 2381–2403.
doi:10.1306/03122119223. Data: https://osf.io/6ysbv/ (CC-BY 4.0).

Grant, N. T. (2020). Using Monte Carlo models to predict hydrocarbon column heights and to assess
the value of seal capacity data. *Petroleum Geoscience* **27**(2).

Hood, K. C. (2019). *Hydrocarbon column height.* Risk Coordinator Workshop #17, Houston,
14 November 2019. ExxonMobil Upstream Integrated Solutions.

Hood, K. C. (2024). *Hydrocarbon column heights*, Parts 1 and 2. Rose & Associates.

Kjønsberg, H., Hauge, R., Kolbjørnsen, O. & Buland, A. (2010). Bayesian Monte Carlo method for
seismic predrill prospect assessment. *Geophysics* **75**(2), O9–O19.

Monigle, P. W., Hedayati, T. S. & Goulding, F. J. (2025). Integrated and improved direct hydrocarbon
indicators: a step forward in petroleum risk discrimination. *AAPG Bulletin* **109**(5), 617–636.
doi:10.1306/04042524030.

Nixon, S., Hallam, T. & Constantine, N. (2018). Direct hydrocarbon indicators: risk and value.
*First Break* **36**(6), 71–78.

Roden, R., Forrest, M. & Holeywell, R. (2012). Relating seismic interpretation to reserve/resource
calculations: insights from a DHI consortium. *The Leading Edge* **31**(9), 1066–1074.

Simm, R. & Bacon, M. (2014). *Seismic Amplitude: An Interpreter's Handbook.* Cambridge University
Press.

Simm, R. (2020). Pitfalls in the use of AVO and DHI analysis. *First Break* **38**(2), 61–67.
