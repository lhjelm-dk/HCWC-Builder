# Monigle, Hedayati & Goulding (2025) — review

> **Integrated and improved direct hydrocarbon indicators: A step forward in petroleum risk
> discrimination.** P. W. Monigle, T. S. Hedayati & F. J. Goulding, ExxonMobil.
> *AAPG Bulletin* **109**(5), May 2025, 617–636. doi:10.1306/04042524030.
> **Gold Open Access, CC-BY** — this one can be cited and quoted freely.

Reviewed 7 Sep 2026. **This is the closest published work to the DHI half of this tool, and it is
the paper Lars suspected existed.** Ken Hood is named among its editors, so it sits directly
alongside `docs/HOOD_2019_REVIEW.md`: Hood's deck is the column-height half, this is the DHI half,
from the same company and the same risking system.

Three findings, in order of consequence:

1. **It supplies the external calibration the app's DHI strength axis has never had** — an
   empirically derived contact weight from 400+ drilled DHI prospects (§3). The app's cap is more
   permissive than theirs.
2. **It publishes the app's element-attribution rule verbatim** (§4), which converts a design
   argument into a citation.
3. **It forces a correction to `docs/ARTICLE.md` §12**: the claim that most workflows have nowhere
   to put an absent anomaly is no longer safe as written (§5).

No mathematical conflict was found. Two architectural gaps were (§6, §7).

---

## 1 · What the paper does

Three systems, evaluated separately and then combined:

| | |
|---|---|
| **GCOS** | Geological chance of success, from a **nine**-element risk model (Sykes *et al.*, 2011), each element scored against a **base rate** from an internal database (Hood & Steffen, 2018) rather than from a 50 % default. |
| **DHI score** | A chance of success from the seismic alone. Since 2021 it is produced by a **supervised machine-learning model** trained on 185 re-scored prospects, from five attributes: anomaly strength, lateral amplitude contrast, fit to structure, fluid contact reflection, amplitude terminations. |
| **iCOS** | The Bayesian integration: GCOS as prior, DHI score as evidence, posterior = iCOS. Cited to Houck (1999), Stabell (2012), Lowry *et al.* (2005) and **Simm & Bacon (2014)**. |

Between the two sits a new metric, **discernibility**, which decides *how much* the DHI is allowed
to move GCOS.

Benchmarked blind on pre-drill knowledge only: discrimination 15 % → 30 %, Brier score 0.23 → 0.15.
The DHI scoring changes alone took Brier from 0.22 → 0.17 (expectation-based attributes) → 0.14
(machine learning).

---

## 2 · Where the app already agrees

**The integration formula is the same one.** Their iCOS is a two-state Bayesian update of a prior
COS by a likelihood ratio, citing Simm & Bacon. `hcwc/core/dhi.py` implements
`simm_update(prior, r) = r·prior / (r·prior + (1 − prior))` and is named after the same source. The
app's character channel *is* their iCOS, on a four-element prior instead of a nine-element one.

**Absence as evidence.** They state it as an advance:

> Incorporating discernibility allows the absence of a DHI, when one is expected, to be treated as
> a negative line of evidence, which is not consistently applied in industry.

Their prospect B — GCOS 46 %, DHI score 5 %, moderate discernibility — gives iCOS **8 %**. The app,
on its own worked prospect, gives 25.0 % → **3.2 %** for an absent anomaly. Same direction, same
order of collapse, from independent machinery.

**Expectation-based, not absolute.** Their 2018 audit found that **AVO class and absolute amplitude
strength were not predictive of success globally** and removed them, replacing every attribute with
one defined *relative to what the container geometry should produce*. That is the same argument the
app's detection function makes — a thin, low-dip prospect should not be penalised for a long
termination that its own geometry guarantees.

**Volumetric consistency is enforced, not suggested.** For moderate and high discernibility the
volumetric parameters *must* be consistent with the geophysical observations. The app's phase-clash
refusal on tab 3.0 is the same instinct, narrower in scope.

---

## 3 · The finding that matters most: a calibrated contact weight

This is the paragraph to act on. On column height:

> When constructing a probabilistic assessment, an empirical relationship has been established
> between DHI score and column height weighting (Figure 8). **High DHI scores (>0.50 rating) weight
> the HCWC at the rated DHI elevation to 95 % of the total trials.** Lower DHI scores (<0.50
> rating) weight the HCWC at the DHI elevation relative to the rating outcome (**double the DHI
> score** for weighting value).

So, calibrated on their drilled database:

```
w(score) = min(2 × score, 0.95)
```

with the figure caption adding the validation:

> Note that for nearly all prospects with a DHI score >50, in a success case, the HCWC was the DHI
> evaluated HCWC.

**This is exactly the app's `p_valid`, measured rather than elicited.** It is a scenario weight —
Hood's construction, which `dhi.scenario_switch` implements — but `p_valid` occupies the same role
in the likelihood form, and the two are directly comparable.

### 3.1 · What it says about the app's strength axis

The app derives `p_valid` from DHI strength through the E-POS two-curve model. Running that
mapping backwards against Monigle's rule gives the app's strength axis its first external
referent:

| Monigle DHI score | their contact weight | app strength that gives that `p_valid` |
|---:|---:|---:|
| 0.05 | 0.10 | **−46** |
| 0.10 | 0.20 | −29 |
| 0.20 | 0.40 | −8 |
| 0.30 | 0.60 | +8 |
| 0.40 | 0.80 | +29 |
| 0.50 and above | 0.95 (capped) | **+61** |

Two readings, both useful:

**The shipped default is defensible.** Strength 5 gives `p_valid` 0.560, implying a DHI score
around 0.28 — a weak-to-moderate anomaly, which is what the default is meant to be.

**The top of the app's slider is not.** Their calibration **caps the contact weight at 0.95**, and
the app reaches that at strength +61. Above that the app keeps going: strength 100 gives
`p_valid` **0.980**, a floor of 0.02 rather than 0.05.

### 3.2 · Three independent anchors on the ceiling, and the app sits above all of them

| source | implied likelihood ratio |
|---|---:|
| Simm (2016), verbal — `strength_bands` already quotes it | above **10** "rarely justified" for a single DHI |
| Monigle *et al.* (2025), empirical — weight 0.95 | **19** |
| Kjønsberg *et al.* (2010), measured by AVO inversion | **29** |
| **`hcwc.core.dhi.R_CAP`** | **50** |

The three published anchors span 10–29. The app's cap is 50, which is above all of them, and
`volume_weight(50) = 0.980`.

### Settled, 9 September 2026

Not by moving the number but by **splitting the constant**, because it was doing two jobs whose
right answers differ — and the table above is what shows it. Kjønsberg's 29 came out of a full
prestack inversion carrying the amplitude *and* the geometry, so it is a **combined** ratio.
Simm's 10 is explicitly about a **single** line of fluid-indicator evidence. Ranking them in one
column was the error: they are bounds on different quantities.

| constant | value | bounds | anchored by |
|---|---:|---|---|
| `R_SINGLE_CHANNEL` | **10** | each channel, going into the combination | Simm (2016) |
| `R_CAP` | **50** | the combination, coming out | above Kjønsberg's measured 29 |

What made this more than housekeeping was a sensitivity sweep of the whole DHI tab. On the
shipped prospect the strength slider alone moved the prospect chance from **1.4 % to 97.2 %** —
a 96-point swing from one elicited number on an axis with no external referent, and more than
every other control on the tab combined. Under the split it is 81 points, which is still the
largest single lever in the app and now a defensible one.

The slider was narrowed to match rather than left to run into a flattened range: `strength_at`
inverts the two curves for the reading that buys R = 10, and that is where the axis ends. A
dead half-slider would have invited a reading the arithmetic then silently refused.

The narrow change this section originally recommended — **naming 0.95 on the `p_valid` control
as the empirically calibrated ceiling**, with the citation — is still worth doing and still open.

---

## 4 · The element-attribution rule, now citable

`docs/ARTICLE.md` §14.2 and the app's refusal to let the DHI tab edit element chances rest on an
argument. The paper states it as policy:

> To avoid double counting positive or negative observations, geologic risking must remain
> independent of DHI attributes. For example, the presence of a DHI does not increase the chance of
> adequacy (COA) of source presence; the adequacy of source is determined by considering the
> geologic factors alone.

That is the app's rule, from ExxonMobil, in the AAPG Bulletin, open access. **Cite it.** It turns
"this tool declines to do something you might want" into "this tool implements published practice."

---

## 5 · What has to be corrected in the article

`docs/ARTICLE.md` §12 currently says of the absent-anomaly result:

> Most workflows have nowhere to put that observation, and in practice it is either argued about
> qualitatively or quietly dropped.

**That is no longer safe as written.** Monigle *et al.* have somewhere to put it, they say so
explicitly, and they show it working on a real dry hole. The honest form of the claim is narrower
and survives:

- They use absence on the **chance** axis — it lowers COS, through iCOS.
- The app uses absence on the **column-height** axis as well — `L = 1 − D(h)`, so absence reshapes
  the *contact distribution*, not only the chance.

That distinction is real and is the thing to claim. Their own hedge — "not consistently applied in
industry (e.g. Nixon *et al.*, 2018)" — is the correct level of confidence for the general
statement.

*Status, 14 September 2026.* The correction above was made, and the audit of the same day
went further. Under the corrected chain (`archive/development_notes/DHI_alignment.md` §0) the realisations are
conditional on G, so `1 − D(h)` reshapes the column and cannot move the chance; the 40.3 % → 6.3 %
result the article quoted came from a within-G ratio applied as a ratio on the prospect, and is
withdrawn. The chance-axis route Monigle *et al.* use is now implemented as a separate ratio on
G, `(1 − d) / (1 − f·d)`, with `f` an elicited relative false-positive rate (audit P1-0,
`dhi.absence_ratio`). At the maximum-ignorance `f = 0.5` the default prospect goes 40.3 % → 11.0 %.
The article's §12 states the construction and §17 states that `f` is uncalibrated.

The same trim applies to §1.1's novelty item 4, which says the scenario switch "cannot use an
absent anomaly". True of the *scenario switch*, but it now needs to say that the chance-axis route
is published and that what is offered here is the column-height route.

---

## 6 · Discernibility: the concept the app does not have

This is the paper's genuine invention, and the app has no equivalent.

**Discernibility asks whether a DHI analysis is meaningful at all for this prospect**, before any
attribute is scored. Two axes:

- **Expectations** — given the anticipated rock properties, trap geometry and fill, *should* a
  fluid change be visible? Rated likely / more likely than not / less likely than not / unlikely,
  and explicitly "evaluated regardless of the quality of the seismic data".
- **Confidence** — can the interpreter actually make the observation? Seismic coverage, offset,
  processing maturity; and geological confidence in the container definition and rock-property
  model.

Combined by a **least-common-denominator** rule — one weak axis caps the result — into high /
moderate / low / none. At *none*, "it is not advised to conduct DHI analysis" at all.

Their prospect C is the case the app cannot express: **DHI score 30 %, low discernibility, so the
DHI was given no weight and iCOS was left equal to GCOS at 72 %.** The prospect was a success. The
app has no control that says *this anomaly rating exists but should not count*.

### What the app has that is adjacent, and why it is not the same

- The **detection function** `D(h)` carries part of *expectations* — if `D(h) ≈ 0` then seeing
  nothing is uninformative, which is the right behaviour. But it is a function of column height
  only. It cannot express "this is a carbonate reservoir and no column height would be visible", or
  "the container is structurally complex enough to manufacture false attributes".
- **`p_valid`** carries part of *confidence*, as the chance the picked event is really a contact.
  But it is derived from the strength, so a bright anomaly on poor data gets a high `p_valid` from
  its brightness alone.
- **`dependence`** is a different thing entirely — how much the geometry and character channels
  overlap, not whether either is worth listening to.

**The gap is real: confidence and quality are conflated in one strength axis.** Their benchmarking
is worth quoting on exactly this, because they tried the app's arrangement and abandoned it:

> Internal benchmarking also demonstrated that the legacy DHI confidence metrics were not
> predictive of success and were removed from the scoring process.

Confidence did not disappear — it moved *out of the score* and into discernibility, where it
modulates weight instead of contributing to it. **That separation is the lesson**: a confidence
judgement mixed into a quality score makes a mediocre anomaly on excellent data indistinguishable
from a strong anomaly on poor data, and the app currently cannot tell them apart.

A minimal implementation, if it is wanted: a three-state control — *the DHI should be visible and I
can see it well* / *partly* / *this prospect is not amenable* — which scales the combined likelihood
ratio toward 1 and, at the bottom setting, pins it there. Nothing in the machinery resists this;
`CombinedUpdate.r_combined` is the single place it would apply.

---

## 7 · Smaller things worth taking

**Their column-height weight applies to a *rated* elevation, not a picked one.** Their contact
weight is driven by the DHI *score* — the whole five-attribute rating — while the app's `p_valid`
comes from strength alone and the pick's σ is separate. Their arrangement bundles what the app
deliberately separates into geometry and character. **The app's separation is better, and the
worked numbers in `ARTICLE.md` §10 demonstrate why**, but it means Monigle's weight is not a
drop-in for `p_valid`: it is a bound on the *combined* result. The comparison in §3.1 should be
read that way.

**Brier score and discrimination as the calibration metrics.** The app's `trust.py` audits whether
the arithmetic supports the number quoted; it cannot score prediction quality, because it has no
outcomes. But the paper is the reference for *what a calibrated risking system looks like* —
Brier 0.15, discrimination 30 % — and `archive/superseded_notes/BASE_RATE_NEGLECT.md` is the right place to point at
it.

**Base rates, not 50 %.** They begin every element at a database-derived base rate, explicitly
"avoiding an initial COA of 50 %, common in risk matrices". This supports the argument already made
in `archive/superseded_notes/BASE_RATE_NEGLECT.md` and gives it a 2025 citation.

**A fluid contact reflection constrains net-to-gross.** From 121 calibration points: reservoirs
with an FCR run 40–85 % NTG, those without 18–55 %; "the absence of an FCR does not preclude a
moderate NTG, but presence does preclude low NTG". Out of scope for a contact-depth tool, but it is
a clean example of a DHI attribute constraining a *volumetric* parameter rather than a chance, and
it is the kind of thing WellVolPOS would want.

**DHIs are not observed below about 14 % porosity.** A hard empirical floor, offered without
qualification. Useful as a sanity check on any prospect where a DHI is claimed.

---

## 8 · Conflicts found

| | |
|---|---|
| Mathematical conflict | **None.** The integration formula is the same; the app's is a strict superset (it also reweights the column-height distribution). |
| Conceptual conflict | **None on attribution or double counting** — the paper states the app's rule as policy. |
| Calibration disagreement | **Was one, now resolved.** `R_CAP = 50` was bounding a single channel as well as the combination. Split on 9 Sep 2026 into `R_SINGLE_CHANNEL = 10` (Simm) and `R_CAP = 50` (above Kjønsberg's 29). §3.2. |
| Missing concept | **Yes.** Discernibility, and specifically the separation of *confidence* from *quality*, which they tested and adopted after finding the combined form unpredictive. §6. |
| Overclaim in this repo | **Yes, one.** `docs/ARTICLE.md` §12 on absent anomalies. §5. |

---

## References

Monigle, P. W., Hedayati, T. S. & Goulding, F. J. (2025). Integrated and improved direct
hydrocarbon indicators: A step forward in petroleum risk discrimination. *AAPG Bulletin*
**109**(5), 617–636. doi:10.1306/04042524030. CC-BY.

Rudolph, K. W. & Goulding, F. J. (2017). Benchmarking exploration predictions and performance using
20+ yr of drilling results: One company's experience. *AAPG Bulletin* **101**(2), 161–176.

Hood, K. C. & Steffen, K. J. (2018). *The rising V — one company's evolution of risking concepts
and applications.* Rose & Associates Risk Coordinators Workshop #13.

Sykes, M. A., Hood, K. C., Salzman, S. N. & Vandewater, C. J. (2011). *Say what we mean and mean
what we say: the unified upstream risk model.* AAPG ICE, Milan.

Nixon, S., Hallam, T. & Constantine, A. (2018). *Ranking DHI attributes for effective prospect risk
assessment applied to the Otway Basin, Australia.* AEGC, Sydney. — already held in
`_private/papers/`.
