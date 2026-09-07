# Hood (2019) — review

> **Hydrocarbon Column Height.** Kenneth C. Hood, ExxonMobil Upstream Integrated Solutions.
> Major contributions: Ken Tillman, Steve Davis, Christie Rogers, Ian Watson.
> Risk Coordinator Workshop #17, Houston, 14 November 2019. 21 slides.
> Later released publicly, in abridged form, as the two-part Rose & Associates blog (Hood, 2024).

Reviewed 7 Sep 2026. **This is the source presentation for the tool's central construction, and the
first read of the full deck rather than the blog abridgement.**

The finding: **the app does not contradict Hood anywhere.** Every recommendation in the deck is
either implemented, implemented in a stricter form, or is out of scope for a single-prospect tool.
Three things in the deck are not in the app and are worth having; one is a genuine methodological
gap.

---

## What the deck actually recommends

Hood's framing is a **three-lane workflow** (slide 8), and the lanes are deliberately independent:

| Lane | Feeds |
|---|---|
| **Empirical** — column-height database, analog columns | HC column distributions |
| **Trap & seal** — mapping, fault framework, seal characterisation, pressure | bed seal (SET), fault seal (SEAP), cryptic leak |
| **DHI** — anomaly mapping, HC leg / wet leg / contact range | DHI COV analysis, column-height weighting |

All three converge on one **Assessment Analysis** box producing *weighted column height
distributions*, *weighted spill depth distributions*, commodity scenarios and trap scenarios.
Every box in the diagram carries a `Confidence*` annotation, footnoted:

> *Need to define and track explicit measure of confidence to support calibration*

The five take-aways (slide 20): shared distributions for prospect families; **separate contact and
spill distributions**; avoid deterministic analyses; follow the DHI guidance; and prefer **"merge
late" over "merge early"** — multiple simple cases rather than fewer complex ones.

---

## Where the app aligns — and where it is stricter than the deck

### 1. Separate column and spill distributions (slides 12–13) — implemented, and enforced

Hood's slide 12 is the app's engine, stated as a recommendation:

> **Issue:** Combining background column height and explicit geometric spill(s) in a single input
> distribution produces non-geologic and erroneous results.

with two required parts — a background column distribution from seal capacity, and specific
geometric limits each with a probability — and the rule that

> All probabilities are conditional on the success of shallower potential limits (must sum to 1.0)

and

> Synclinal Spill (Probability = 1.0 − Conditional Shallower Potential Geometric Limits)

**The app implements this as a lower envelope rather than as a conditional-probability chain**, and
that is a strict improvement, not a deviation. `LimitSet.__post_init__` requires at least one limit
with `p_active = 1.0` — the app's version of "spill has whatever probability is left over" — and
`engine.run` takes the shallowest *active* limit per realisation. The two constructions agree
whenever the shallower limits really are shallower. They disagree exactly when a "shallower"
geometric limit samples *deeper* than spill on some realisations, which a normal-alt or beta
elicitation with overlapping tails does routinely. Hood's bookkeeping would still charge that
realisation to the geometric limit; the app charges it to spill, which is the geology. The user
never has to make probabilities sum to 1.0 by hand, and the controlling shares come out as an
output.

Measured on the shipped reference prospect (200 000 realisations):

| Controlling limit | Share |
|---|---:|
| Top seal (capillary) | 35.1 % |
| Fault 1 geometry | 33.9 % |
| Base seal (capillary) | 18.6 % |
| Charge | 7.0 % |
| Fault leakage 2 | 5.1 % |
| Closure / spill | 0.2 % |

Nobody typed any of those. They are the `argmin` histogram.

### 2. Fill-to-spill is an output, never an input (slide 14) — implemented

> The probability of Fill to Spill is not arbitrary — it should be determined by the percentage of
> the background distribution that exceeds the closure height. **Does not need to be defined or
> calculated in advance — it is an output of the Monte Carlo simulation.**

Exactly what the table above is. `P(fill to spill)` is the controlling share of `Closure / spill`.

### 3. Truncating, not terminating (slides 14–16) — implemented, and demonstrable

> Distributions lacking a Mode at synclinal fill have essentially no chance of being filled to
> spill … The common practice of extending a column height or contact distribution down to
> synclinal spill implies that the defined feature has **essentially no control** on the column.

His figure is a uniform column distribution on a 500 m closure, either *linked* to closure height
or *truncated* by it. Reproduced in the app's own engine:

| | mean column | P(at spill) |
|---|---:|---:|
| terminated — U(0, 500) linked to closure | 249.6 m | **0.0 %** |
| truncated — U(0, 1000) cut by spill | 374.6 m | **50.0 %** |

A 125 m difference in the mean and a 50-point difference in fill-to-spill, from a choice the
assessor may not know they are making. **The app cannot express the terminated form**: a limit's
distribution is stated in metres of column below the apex (or as an absolute depth) and is never
parameterised by closure height, so there is no widget that links the two. The failure mode is
designed out rather than warned about.

Hood's corollary on slide 12 is followed by the shipped defaults:

> For single phase accumulations, model seal properties assuming a closure height greater than the
> capillary capacity of the seal (to avoid truncation of the distribution in the model)

The reference prospect's top seal is `beta_subj(20, 200, 250, 618)` against a ~350 m closure — the
seal capacity is deliberately allowed to run past spill, and spill truncates it.

### 4. The weighted-column error (slide 13) — designed out

> For weighted column distribution, the prospect volumes actually **increase** by adding the deep
> leak (the weighting erroneously decreases the number of realizations above the geometric spill
> depth).

His slide-13 chart shows the weighted-*contact* curve sitting above the no-leak base case, and the
weighted-*spill* curve at or below it. The app never builds either weighted input distribution, so
the question does not arise; adding a leak as a competing limit moves the mean strictly down
(−59.6 m on a test case). One caveat on the app's own wording: `README.md` and
`hcwc/ui/limiters_tab.py:368` both repeat the "can even make apparent prospect volume rise" claim.
It is correctly attributed to Hood in both places, which is right — **I could not reproduce his
paradox from first principles**, because the mechanism is specific to how GeoX weights a fractile
distribution and the slide does not show the construction. Keep it attributed; do not restate it as
something this tool measured.

### 5. DHI as a weighting, not a substitution (slide 17) — implemented, both ways

Hood's example is a 7-fractile background, DHI at 600 m, spill at 1000 m, and a weight he calls
**COV** — the app's `p_valid` under a different name:

| | Hood's P10/P90 |
|---|---:|
| base case, no DHI | 13.6 |
| DHI, low COV — weight 0.6 | 9.2 |
| DHI, high COV — weight 0.95 | 2.9 |

with the warning: *"the revised weighting will result in assessments with much narrower ranges!"*

The app's `dhi.scenario_switch` is Hood's construction verbatim, and reproduces the behaviour on the
reference prospect (DHI at 2 250 m, σ = 15 m):

| | P10/P90 |
|---|---:|
| no DHI | 2.71 |
| COV 0.60 | 1.71 |
| COV 0.95 | 1.24 |

Same direction, same order of collapse. **Hood's exclamation mark is the app's ESS diagnostic**: he
flags the narrowing as something to be alarmed by and stops there; the app reports the effective
sample size behind the update so the narrowing has a number attached to it (10 000 → 312 at the
sharp end). The likelihood formulation is offered alongside the scenario switch rather than instead
of it, and `hcwc/core/dhi.py:481` names the switch as Hood's rule.

### 6. Merge late, avoid deterministic analyses (slides 6, 20) — aligned

Slide 6's volume table ends with a deterministic row annotated **"Never do just this!"** —
151 / 151 / 151 across F90, F50, F10. The app has no deterministic mode.

---

## Where the app differs, defensibly

### Prospect families are supported as plumbing, not as a product

Hood's first recommendation is to start every evaluation from a **representative column height
distribution for the applicable family** (slides 9–11: five structural families, plus stratigraphic)
and modify for local considerations. The app's `hcwc/core/limits.py:12` docstring says this is why
distributions are data rather than code, and `hcwc/io/prospect.py` round-trips a whole prospect to
JSON — so a family template is a saved file away. What does not exist is a **library**: a shipped or
curated set of family distributions with a picker. Tab 6's "benchmark families" are calibration
comparators, not input templates.

This is a scope call, not a disagreement. Hood is describing a corporate database backed by an
internal column-height archive; a single-prospect tool with no such archive cannot ship five
families and pretend they mean something. Worth noting that the *mechanism* is already there — the
`empirical` limit kind (a quantile table) is exposed in the UI on every limit, so an analog-derived
column-height distribution can be used as an input today.

### The assessment minimum is a flag, not a truncation

Slide 10 annotates "Truncate at Asmt Minimum / Ensure COA consistent with truncation". The app
deliberately does **not** filter below-minimum realisations out of the array
(`hcwc/core/engine.py`, `above_minimum`), because `POS = P(column ≥ h_min)` has to be readable off
the same object as the contact distribution. This is the same requirement Hood states — COA
consistent with the truncation — met by construction rather than by a check.

---

## What is in the deck and not in the app

### 1. Capillary-controlled dual-phase columns — the one real gap

Slide 18, Case 1:

> When both the GOC and OWC are controlled by capillary seal limitations, the GOC will comprise
> **approximately 20 %** of the total hydrocarbon column height. This is rarely equivalent to 20 %
> of the trap (hydrocarbon-bearing) or energy-equivalent volume.

The app's two-phase support is entirely **charge-driven**: `charge.mixed_separate` and
`charge.mixed_joint` place the GOC from the free-gas volume via the area–depth table, with `nan`
where there is no free gas cap. There is no seal-capacity route to a GOC at all.

That 20 % is not a rule of thumb — it falls out of the density contrasts, because the same seal
holds a gas column against a larger buoyancy gradient than an oil column. The app already has the
machinery: `seals.py` computes capillary capacity from interfacial tension, contact angle and
density contrast, and would give the gas and oil legs different capacities if asked for both. **This
is worth building**, and Hood's second sentence is the reason — the 20 % is a *column* fraction and
teams routinely apply it as a volume fraction, which the app's area–depth table would immediately
expose as wrong.

### 2. Commodity scenarios from realisation proportions

Slide 19, Case 2 — where the GOC and OWC are both set by probabilistic geometric spills:

> Filter realisations into Oil only, Gas only, and Dual-Phase groups … **Scenario chance based on
> relative proportion of realisations in each group.** Note that the HWC distribution can be
> different for three commodity scenarios.

The app has the raw material — `mixed_joint` already returns `nan` GOC for the no-gas-cap
realisations, so the oil-only share is one line away — but nothing splits the contact distribution
by commodity or reports the three scenario chances. This is the "merge late" philosophy applied to
the output, and it fits the existing argmin bookkeeping naturally: a second categorical per
realisation alongside the controlling limit.

Low cost, high alignment. Worth doing after the capillary GOC, since the two share an input.

### 3. Explicit confidence on every input, tracked for calibration

The `Confidence*` annotation on all nine boxes of slide 8, and its footnote, is the deck's quietest
and most demanding recommendation. There is **no confidence field anywhere in the app** — a `Limit`
carries `name`, `group`, `p_active`, `distribution`, `note`, `kind`, and nothing about how well the
elicitation is supported.

The app's `trust.py` is a different thing and says so in its own docstring: it audits whether the
*arithmetic* supports the number being quoted, and explicitly declines to score the geology. Hood
wants the opposite — an assessor-stated confidence per input, persisted, so that a later
back-analysis can ask whether high-confidence inputs actually outperformed low-confidence ones.

**This is only worth building if the record it feeds exists.** A confidence dropdown that nothing
ever reads back is a widget that makes an assessment look more rigorous without making it more
rigorous, which is the failure the whole tool is built against. The honest version is a
free-text-plus-tier field written into the saved prospect JSON and printed in the report, so it
travels with the assessment and can be audited by a person — not scored by the app.

---

## What the deck says that the app should quote

Two lines are better stated by Hood than by anything currently in the app, and both are already
half-said in the UI:

> Essential that alternative characterizations of column height have a compelling geologic basis,
> as the potential impact on business decisions may be substantial.

Slide 6's supporting table is worth having in tab 6 as a calibration exhibit — seven column-height
distributions applied to the *same* hypothetical 1 000 m closure, referenced to the deterministic
fill-to-spill case at 100 %:

| Distribution | Mean | F90 | F50 | F10 | % of deterministic |
|---|---:|---:|---:|---:|---:|
| Fill to spill | 156 | 57 | 132 | 288 | 103.6 % |
| Weighted at spill | 111 | 16 | 91 | 237 | 74.0 % |
| Uniform to global max | 88 | 9 | 64 | 202 | 58.5 % |
| Uniform to spill | 69 | 7 | 49 | 160 | 46.0 % |
| Regional 7-fractile | 47 | 7 | 29 | 113 | 31.2 % |
| Pseudo-exponential | 29 | 3 | 16 | 69 | 19.1 % |
| Deep-water strat traps | 24 | 4 | 13 | 58 | 16.2 % |
| *Deterministic* | *151* | *151* | *151* | *151* | *100.0 %* |

A **6.4× spread in the mean** from the choice of column-height distribution alone, every one of
which was in production use inside one company. That is the strongest single argument for a tool
that makes the choice explicit and documented, and it is a better opening number than anything the
app currently quotes.

---

## Verdict

| | |
|---|---|
| Does the app contradict the deck? | **No.** Not on any of the five take-aways. |
| Is anything implemented more weakly than recommended? | No. The lower envelope is stricter than the conditional chain; truncation is designed in rather than advised. |
| Is anything missing that matters? | **Yes — capillary-controlled dual-phase columns (slide 18).** The app has the seal physics and the area–depth table and does not connect them. |
| Anything cheap and aligned? | Commodity scenarios from realisation proportions (slide 19). One categorical array. |
| Anything to be careful about? | The "volumes rise when you add a leak" claim is Hood's, reproduced from his slide, not measured here. Keep it attributed. |

## References

Hood, K. C. (2019). *Hydrocarbon Column Height.* Risk Coordinator Workshop #17, Houston,
14 November 2019. ExxonMobil Upstream Integrated Solutions.

Hood, K. C. (2024). *Hydrocarbon Column Heights*, Parts 1 and 2. Rose & Associates, 7 May 2024 —
the released abridgement of the above.
