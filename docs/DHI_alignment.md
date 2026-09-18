# Aligning the DHI update with the minimum-volume POS

**Lars Hjelm · 25 August 2026 · working note, for challenge**

> *"The geological POS relates to a minimum volume, but the DHI-updated POS relates to a
> potentially larger volume. I don't know how to combine them. Is the updated POS related to how the
> HCWC distribution is defined for the DHI HCWC?"*

**Yes — and that turns out to be the whole answer.** Under the formulation below the DHI-updated POS
and the DHI-updated contact distribution are *the same object*, read at two different thresholds.
Once you see that, the incompatibility disappears.

---

## 0 · Status, 14 September 2026 — what the audit changed

Three corrections to what follows, all in `hcwc/core/dhi.py`. The note is left as written below
so the reasoning can be followed; where it conflicts with this section, this section is current.

**The chain is conditional, and the strength enters once.** The engine samples `p(h | G)`, so
everything applied to its realisations is conditional on G. The prospect chance is

```
POS(h_min) = P(G | strength) × P(h ≥ h_min | G, geometry)
```

with `P(G | strength) = simm_update(P(G), R_strength)` and the second factor read off the same
weights that draw the posterior histogram and percentiles. `p_valid` is
`P(the picked event is the contact | G, contact attributes)` — the contact-attribute judgement `c`
and nothing else. It had been built as `P(G | strength) × c`, which put `P(G)` inside a term
already conditional on G, so the strength reached the geometry posterior through the mixture
weight and then again through a blended likelihood ratio (`CombinedUpdate`). Holding `c` at 0.70
and moving the strength alone moved the posterior P50 by 17 m. The blend also applied `r_dhi` — a
ratio between two column heights inside G — as if it were a likelihood ratio on the prospect.
§5's open question on the two channels' independence is answered by structure: they update
different factors. `dhi.prospect_pos` is the chain; `CombinedUpdate` stays only as a comparison.

**An absent anomaly reaches the chance through its own ratio.** With the chain conditional on G,
`1 − D(h)` can only reshape the column, and §3.2 below overstated what it does: on the shipped
prospect every column sits on the detection ceiling and nothing moves. The chance is now updated
by `dhi.absence_ratio`, `P(absent | G) / P(absent | ¬G) = (1 − d) / (1 − f·d)`, with `d` the mean
detectability over the geological columns and `f` an elicited relative false-positive rate on the
detection function (audit P1-0). It is never above 1 and is floored at 1/10.

**The spurious-event density is a property of the model.** It was `1 / (max − min)` of the
*sampled* contacts, so a pick's likelihood depended on the trial count and the seed — four per
cent between a 2 000- and a 50 000-trial run. It is now one over the declared contact support,
`LimitSet.contact_support_m()`: the apex's shallow quantile to the tightest always-active limit's
deep quantile, read off the distributions rather than the draws.

**Partial conformance is a censored pick.** "Bright above `z_off`, reliably absent below" is one
observation of where the anomaly's edge is, made with the same pick-and-depth-conversion error a
picked contact carries. Its likelihood is therefore the normal *cumulative* where a pick's is the
normal *density*:

```
L = p_valid · D(h) · Φ((z_off − (apex + h)) / σ)  +  (1 − p_valid)
```

The form it replaces, `D(h) · [1 − D((h − h_off)+)]`, applied the detection function twice —
once to the column and once to the slice below the cutoff — as if the two were independent
detections, and had no parameter of its own: its softness came from `h50` and its steepness, and
its floor inside the valid branch from `1 − ceiling`, all elicited for a different question. With
the shipped defaults that placed the fifty-per-cent point 25 m below the stated cutoff. The
censored form has one parameter, `σ`, already on the observation, and puts the half-way point at
the depth the interpreter stated.

---

## 1 · Why it feels contradictory

Two numbers that appear to be about the same thing:

| | Event it is about | Typical column |
|---|---|---|
| **Geological POS** | "there is an accumulation of at least the minimum size" | `h ≥ h_min`, small |
| **DHI-updated POS** | felt to be about "the bright, conformant, mappable accumulation" | `h ≈ h_DHI`, large |

They are not the same event, so multiplying either by the other's volume is a category error. That
is the real problem, and it is worth naming plainly:

> **The failure mode.** A team quotes POS = 0.85 because the DHI is strong, and pairs it with the
> DHI-case volume. But the 0.85 was computed as a *presence* probability — the minimum-case event —
> while the volume is the maximum-case volume. **A POS for one event, a volume for another.**

This is not a DHI problem. It is a **threshold-labelling** problem that the DHI makes acute, because
the DHI is the one piece of evidence that speaks loudly about the *large* case.

---

## 2 · The reframe: POS is not a number, it is a reading

Everything the tool computes is one function:

```
F(h) = P(column height ≥ h)          h measured below the apex
```

Then, and this is the point, **every "POS" in the workflow is `F` evaluated somewhere**:

| Quantity | Is just |
|---|---|
| Geological POS at the risking criterion | `F(h_min)` |
| POS at the well's reservoir entry depth | `F(z_entry − apex)` |
| Probability the DHI-indicated case is real | `F(h_DHI)` |
| Probability of filling to spill | `F(h_spill)` |

`F` is monotonically decreasing, so `F(h_min) ≥ F(h_DHI)` **always**. There is no combination step
and nothing to reconcile — the two numbers were never competing. They are two points on one curve,
and the only sin is quoting one of them without saying which `h` it was read at.

**Design consequence, and it is the most important one in this note:**

> **The app must never display a bare POS.** Every POS is displayed with the threshold it was read
> at, and the primary risk output is the **`F(h)` curve itself**, not a scalar.

---

## 3 · Where the DHI enters: a likelihood over column height

The DHI is evidence. Bayes needs a likelihood, and the question is *a likelihood of what*.

The insight that makes this work: **the seismic response depends on how much hydrocarbon is there,
not merely on whether any is.** So the likelihood is a function of `h`:

```
L(observed seismic | h)
```

and the posterior is an ordinary reweighting of the column-height distribution:

```
posterior(h)  ∝  prior(h) × L(observed seismic | h)
```

Everything Lars wants then falls out of one equation:

- **A strong, conformant DHI** makes `L` large at large `h`, so the posterior mass moves down-dip:
  POS rises **and** the contact distribution deepens. Both, from one update.
- **An absent DHI where one was expected** makes `L` large only at small `h`: POS falls **and** the
  contact distribution shallows. Also both.
- **`POS_post = ∫_{h_min}^{∞} posterior(h) dh`** — the min-volume POS is an integral of the same
  posterior that produced the contact distribution. That is the direct answer to the question.

### 3.1 What `L(seismic | h)` is made of

Two factors, and they do different jobs:

```
L(seismic | h)  =  D(h)  ×  Pick(z_DHI | apex + h)        if an anomaly was observed
                =  1 − D(h)                                if no anomaly was observed
```

**`D(h)` — the detection function.** The probability that a column of height `h` produces a
*detectable* anomaly. Physically this is near zero below tuning thickness, rises through the
resolution limit, and plateaus. A logistic in `h` is the natural form, parameterised by the two
numbers an interpreter can actually state:

- `h₅₀` — the column at which you would have a 50/50 chance of seeing it. Roughly the tuning
  thickness for the reservoir and frequency in question.
- a steepness, or equivalently the column at which detection becomes near-certain.

**`Pick(z_DHI | contact)` — the pick likelihood.** Given that an anomaly *is* detectable, how
likely is the observed down-dip termination depth if the true contact is at `apex + h`? A normal
centred on the true contact, with σ from the flat-spot pick uncertainty *plus the depth-conversion
error* — which is the same depth-conversion uncertainty that moves the well's entry depth, so it is
the one place the two tools genuinely couple.

### 3.2 Absence of evidence, handled properly

E-POS already states the principle: *"an amplitude that is absent where one was expected is itself
evidence and lowers P(G)."* With a detection function this needs no special case. If no anomaly was
seen, `L = 1 − D(h)`, which is largest at small `h`. The posterior shifts shallow, POS falls, the
contact distribution tightens up-dip. **Same machinery, no extra parameters.** That is a good sign
the formulation is the right one.

---

## 4 · The area is a second, independent contact statement

A DHI has an areal extent as well as a down-dip termination. Through the area–depth table, an area
*is* a depth:

```
A_DHI  --(area–depth table, inverted)-->  z_A  -->  h_A = z_A − apex
```

So a mapped DHI gives **two readings of the same contact**:

1. the down-dip amplitude termination / flat spot → `h_DHI`
2. the areal extent of the anomaly → `h_A`

**They should agree, and when they do not, that is information.** Concretely:

| Observation | Reading |
|---|---|
| `h_A ≈ h_DHI` | consistent; use both, treat as one observation with reduced σ |
| `h_A < h_DHI` (anomaly narrower than its down-dip limit implies) | the anomaly may not be filling the closure — a stratigraphic or diagenetic component, or a smaller effective trap |
| `h_A > h_DHI` | the anomaly extends beyond the mapped conformance — suspect a non-fluid cause (lithology, tuning) |

**Design consequence:** the DHI panel shows both readings against the area–depth curve and flags
disagreement. Nothing forces the two readings to agree, which is what makes the check worth
running.

### 4.1 The containment constraint

Your `DHI Prospect inputs` sheet already carries the note *"Min area of geological assessed area
must reside within the DHI area."* That is the consistency requirement, and it should be enforced,
not remembered:

```
A(h_min)  ≤  A_DHI
```

If the minimum-case area is **larger** than the DHI area, then the DHI is not evidence about the
success case you are risking — it is evidence about a smaller one, and the update is invalid as
posed. The app should refuse, or make the user re-state `h_min`, rather than quietly updating.

---

## 5 · How this divides work with E-POS

There are **two distinct DHI updates**, using two different aspects of the same observation. Keeping
them separate is what makes the whole thing tractable.

| | E-POS | HCWC Builder |
|---|---|---|
| **Uses** | amplitude class / DHI evidence index, against its reference distributions | anomaly **geometry**: down-dip termination, areal extent |
| **Updates** | `P(HC present)` and `P(reservoir effective)` — a **categorical** update over 8 outcomes | the **continuous** distribution of column height |
| **Answers** | *is there hydrocarbon, and is there reservoir* | *how far down does it go* |
| **Implemented** | `logic/dfi_bayes.py`, `logic/dfi_pillar_update.py` | to build |

And the constraint that E-POS already documents governs the split:

> A DFI is a *fluid* indicator: it can sense whether a reservoir exists and what fluid fills it. **It
> cannot tell which of charge / trap / retention failed.**

So the DHI may move POS, and may say where the contact is. **It may not re-weight the competing
limits** — it cannot tell you the contact is seal-controlled rather than spill-controlled. Output 2
(which limit controls the contact) must therefore be reported from the *geological* model, with the
DHI-conditioned version shown alongside only as "given the DHI contact, which limits are consistent
with it" — a filter, not an update.

**[Open] Are the two updates independent evidence?** Not strictly: a bright anomaly is more likely
to have a mappable termination, so amplitude class and geometric quality co-vary. Treating them as
independent double-counts a little. My recommendation is to treat them as independent in v1, state
it plainly on the screen, and offer a single correlation knob rather than pretending the problem
does not exist.

---

## 6 · The output that makes all of this un-misstatable

One figure, and it should be the headline of the DHI tab:

**POS versus threshold**

- x: threshold column height `h` (with a second axis showing the equivalent volume and the
  equivalent contact depth, since those are what people actually argue about)
- y: `F(h)` = P(column ≥ h)
- two curves: **prior (geological)** and **posterior (DHI-updated)**
- vertical markers at: `h_min` (the risking criterion), `h_DHI` (the DHI-indicated contact),
  `z_entry − apex` (the well), `h_spill`
- a read-out table underneath giving POS *and* volume at each marker, **always paired**

What it shows at a glance, and what no scalar can:

1. The DHI raises POS at `h_min` **and** raises the chance of the big case. No contradiction.
2. The gap between the curves *is* the DHI's contribution, visible as a shape rather than a number.
3. Quoting "POS = 0.85 with the DHI volume" becomes visibly wrong, because the 0.85 is read at one
   marker and the volume at another.

---

## 7 · Three implementation options, and a recommendation

| | Method | Updates POS? | Updates contact? | Effort |
|---|---|---|---|---|
| **A** | **Scenario switch** — Bernoulli on DHI validity; if valid, contact = DHI depth; else geological. The older and simpler approach, and what Hood recommends. | ✗ | ✓ | trivial — already specified |
| **B** | **Likelihood over column height** — §3. Detection function × pick likelihood, reweight the prior, renormalise. | ✓ | ✓ | moderate |
| **C** | **Full joint with E-POS** — categorical fluid update and geometric contact update combined with an explicit dependence. | ✓ | ✓ | high |

**Recommendation: build A first, then B, and present both.**

A is honest and needs no new elicitation. It is the right default for a screening run, and it is
what most assessors will already recognise.

B is the one that answers the question in this note, and it is not much more work: it needs exactly
two new numbers from the interpreter (`h₅₀` and a pick σ), both of which are things a geophysicist
can state and neither of which the current 0.655 captures. Showing A and B side by side is also the
cleanest way to demonstrate what the extra structure buys.

C waits until B has been used in anger.

### 7.1 What this says about a typed `P(DHI valid)`

Under formulation B, a hard-typed `P(DHI valid) = 0.655` is revealed as a **collapsed
version of the detection function** — a single number standing in for `D(h)` evaluated somewhere
unspecified. That explains cleanly why it does not equal E-POS's `dhi_volume_weight` of 0.128: the
two are answering different questions, and 0.655 was never meant to be the fluid-discrimination
likelihood ratio.

So **defect B‑10 is not a bug.** It is an unlabelled parameter of a model that was never written
down. Formulation B writes it down.

---

## 8 · Summary — the five things to build

1. **Never display a bare POS.** Every POS carries its threshold. The `F(h)` curve is the primary
   risk output.
2. **A detection function `D(h)`**, logistic, parameterised by tuning thickness — with the empirical
   guidance in the helper text, because this is exactly where a geoscientist needs a prompt.
3. **A pick likelihood** on the DHI contact depth, σ from flat-spot pick **plus** depth conversion.
4. **The area cross-check** — `h_A` from the area–depth table against `h_DHI` from the termination,
   with disagreement flagged; and the containment constraint `A(h_min) ≤ A_DHI` enforced.
5. **The POS-versus-threshold figure**, prior and posterior, markers at `h_min`, `h_DHI`, `z_entry`,
   `h_spill`, with POS and volume always read as a pair.

---

## 9 · What I am not sure about

- **The detection function's shape.** Logistic is a reasonable default but the physics (tuning,
  AVO class, impedance contrast) may warrant something with a hump — a Class III sand can be *less*
  visible when very thick if the top and base responses separate. **Worth asking a geophysicist,
  and worth exposing the shape rather than hard-coding it.**
- **Whether `D(h)` should depend on depth as well as column height.** Almost certainly yes —
  resolution degrades with depth — which would make it `D(h, z)`. That is a second-order refinement
  but it interacts with the burial-depth term we recovered in the censoring analysis.
- **Gas versus oil.** A gas DHI and an oil DHI have very different detectability. The detection
  function is fluid-specific, so this branch has to be inside the phase scenario, not above it.
