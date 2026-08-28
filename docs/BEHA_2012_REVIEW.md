# Beha, Christensen & Young (2012) — review

> **A general method for the consistent volume assessment of complex hydrocarbon traps**
> *Journal of Petroleum Geology* **35**(1), January 2012, 85–98. DONG E&P and Rose & Associates.

Reviewed 26 Aug 2026. **This is the closest published precedent to this tool, and it changes what
can be claimed as new.**

---

## What it says

**Complex traps** are those where several trapping elements must work simultaneously to reach the
full volume. Their concern is a specific, common error:

> Evaluations which involve multiplying additional chance factors may lead to an under-estimation of
> the probability of geological success and an over-estimation of the hydrocarbon volume.

Their fix is to **enumerate the scenarios** — every combination of trapping elements working or
failing — compute each one's probability, and collapse the result into a single uncertainty
distribution for the contact.

### The worked example

A faulted four-way closure, crest at 2000 m:

| | Cuts top reservoir at | P(seals) |
|---|---:|---:|
| NE fault | 2050 m | 0.4 |
| SW fault | 2100 m | 0.7 |
| Lowest closing contour | 2150 m | — (always) |

Four scenarios collapse onto three leak points:

| Leak point | Probability | Requires |
|---:|---:|---|
| 2050 m | **0.60** | NE leaks (SW irrelevant) |
| 2100 m | **0.12** | NE seals, SW leaks |
| 2150 m | **0.28** | both seal |

Their own headline observation, and the reason they wrote the paper:

> it is not intuitively obvious that a deep leak point can be statistically more likely than a leak
> point higher up the structure, although the deeper leak point requires more elements to seal
> simultaneously.

---

## Where this leaves the novelty claim

**The competing-limits model is not new, and this is its clearest statement.** Beha et al. describe
exactly what `hcwc/core/engine.py` computes: independent trapping elements, each with a probability
of being active and a depth at which it bites, the shallowest active one setting the contact, and
the resulting frequencies used directly as Monte Carlo weights. Their Table 2 *is* the argmin.

This is the second such correction. Grant (2020) already turned out to publish the controlling-limit
diagnostic as "column height control statistics"; Beha et al. (2012) publish the model that produces
it, eight years earlier. **The README and the plan should say so.**

**What is still ours, and it is not nothing:**

| | Beha et al. (2012) | This tool |
|---|---|---|
| Limit form | **discrete** leak points — a fault/top-reservoir intersection is one depth | **continuous distributions** per limit, so a seal capacity or a charge volume enters directly |
| Number of elements | enumerated by hand; four scenarios from two faults | simulated; 2ⁿ scenarios never written down |
| Dependence | *"It is assumed that there is no dependency between the two faults"* | Gaussian copula over the limits, with a nearest-correlation projection |
| Empirical basis | none | 242 NCS discoveries, and the censoring correction |
| Derived element risk | not attempted | per-element chance against depth, from the argmin |

Their hand enumeration is exact but does not scale and cannot take a distribution. Ours scales and
takes distributions but is a simulation. **They are the same model at two levels of generality**, and
saying so is more defensible than discovering it in review.

---

## What it settles — the DHI anchoring question, independently

Beha et al. state the POS/volume split more clearly than anything else read for this project, and
they settle the bug found on 26 Aug 2026 in the DHI update:

> The potential failure of additional trapping elements down-dip from the crest of the structure
> will **not** reduce the probability of finding hydrocarbons at the prospect location. Rather, they
> will influence the probability of deeper hydrocarbon-water contacts.

and, on their scenario tree:

> the POS only determines the success rate of the prospect … Once a success has been identified, the
> POS neither influences the scenario weighting nor the volume calculation. In other words, the
> weighting of scenarios is **normalised to the success rate of the prospect**.

That is precisely the structure now implemented: **prospect POS = ∏ element chances × P(column ≥ h)**,
the second term conditional on success. Two independent sources — E-POS's `prior_pg_override` and
this paper — say the same thing, which is as much confirmation as this kind of question gets.

---

## The warning we should act on

Their central criticism is of **multiplying trap-element factors into the POS chain**. This tool
mostly avoids it by construction: fault seal is a limit on tab ③, not a factor in the tab ② product.

**But there is a real double-count risk one level in, and the tool does not currently warn about
it.** The Retention chance on tab ② comes from E-POS. If an assessor defined it as *"the seal holds
the column I am carrying"*, and then also enters a top-seal capacity distribution on tab ③, the same
uncertainty is counted twice — POS is understated and, by Beha et al.'s argument, volume overstated.

The definitions have to be:

* **Element chance (tab ②)** — does this element work *at the crest*, enough for the minimum
  volume? Beha et al.'s definition, and Otis & Schneidermann's.
* **Limit distribution (tab ③)** — *given* it works at the crest, how far down does it hold?

**[D‑37] Put that distinction on tab ② beside the element inputs, and on tab ③ beside the Retention
section.** It is one caption in each place and it prevents the error the paper is written about.

---

## Also worth taking

1. **They use the same exceedance convention** — *"P99 is the smallest outcome and P1 is the
   largest"*. Same as this tool and as the GeoX export. Worth citing on tab ⑦, because the
   convention is the single thing most likely to be got backwards by a reader.
2. **POS = chance of exceeding the P99 volume**, before any commercial truncation. That is a
   cleaner statement of the assessment minimum than the tool currently gives, and it is what tab ②'s
   *assessment minimum* should say it means.
3. **Their scenario tree is a good figure** and the tool has no equivalent. For a prospect with two
   or three switchable limits, drawing the tree beside the simulated shares would make the argmin
   concrete — and would show a reader the deep-leak-more-likely result the paper found
   counter-intuitive. **[D‑38]**, optional.

---

## Validation gained

Their three leak-point frequencies are a **published case computed by someone else**, which this
project has never had — every other check is internal, and internal checks cannot catch a shared
misconception. The engine reproduces all three:

| Leak point | Paper | Engine (400 000 trials) |
|---:|---:|---:|
| 2050 m | 0.60 | **0.5998** |
| 2100 m | 0.12 | **0.1198** |
| 2150 m | 0.28 | **0.2804** |

Locked in as `tests/test_engine.py::TestBeha2012PublishedExample`, including the counter-intuitive
ordering, and it exercises the new depth-stated parameterisation end to end.
