# Half the evidence for seal capacity is not evidence for seal capacity

**Draft. Written to be read on LinkedIn, and to be argued with.**

---

If you have ever put a hydrocarbon column height into a prospect assessment, you have almost
certainly used a number that came, directly or by inheritance, from a compilation of discoveries.
It is the sensible thing to do. Somebody measured 242 real accumulations; why would you not use
them?

Here is the problem, and it took me a while to see it.

**A trap that filled to spill does not tell you what the seal could hold. It tells you what the
closure could hold.**

The hydrocarbons stopped at the spill point because they ran out of trap, not because the seal
gave up. The seal might have held twice as much. It might have held ten times as much. The
observation is silent on the question — it is a *lower bound* on seal capacity, not a measurement
of it.

In the statistics of survival analysis this has a name. It is a **right-censored observation**, and
there is a hundred years of method for handling it. What you must not do is treat it as a
measurement.

## How much of the record is like this

In Edmundson et al.'s open dataset of 242 Norwegian Continental Shelf discoveries — published
under CC-BY, which is why any of this is checkable — **111 are filled to spill.**

Forty-six per cent of the evidence for how much seal capacity a rock has, is not evidence about
seal capacity.

## What it does to the numbers

Fit column height against trap height and burial depth the ordinary way, and against the same data
with the filled traps treated as censored:

| | trap height | burial depth |
|---|---|---|
| ordinary least squares | 0.880 | 0.143 |
| censoring-corrected | **0.701** | **0.277** |

Two things happen, and the second is the one that changes what you would say in a meeting.

**Censoring inflates the trap-height term.** Of course it does: every filled trap is a point where
column *equals* trap by construction, so a fit that takes them at face value is partly fitting an
identity rather than a relationship.

**And it nearly doubles the burial-depth term.** "Burial depth is the weaker control" is a
reasonable reading of the uncorrected fit. It does not survive the correction. Burial depth comes
out about twice as important as the naive fit suggests, and trap height about a fifth less.

*Before anyone quotes the third decimal: the trap-height coefficient moves with the tolerance you
use to decide when a column counts as "at" its spill — 0.720 at half a metre, 0.701 at one metre,
0.697 at two. The direction and the size of the effect are robust. The third digit is not.*

## The check that convinced me

A coefficient moving is not, by itself, an argument. Anyone can produce a different number with a
different estimator.

So here is a test the model has to pass on its own terms. Take the fitted relationship, sample seal
capacities from it, apply the same `min(capacity, closure)` the geology applies, and ask: **what
fraction of the resulting traps fill to spill?** The answer has to match the fraction actually
observed, or the model is not describing the data it was fitted to.

```
observed in the dataset        45.9 %
censoring-corrected model      47.2 %
the published relationship     32.1 %
```

The corrected fit reproduces the fill rate. The uncorrected one is out by fourteen points — it
predicts a third of traps filling where nearly half of them do.

*Both are computed exactly rather than simulated, and both are given the same spread so that only
the mean function differs. That choice is the one less flattering to my argument: let the naive fit
use its own narrower residual spread instead and it predicts 24.1 %, which is worse still.*

## Why this is not an academic point

Column height is the largest single driver of prospect volume, and the only input that turns a
prospect-level chance into a chance at a *specific well location*. A biased column-height prior
propagates into every volume you quote and every well you rank.

And the direction is not neutral. Overweighting trap height and underweighting burial depth makes
your big shallow structures look better than they are and your deep ones worse.

## What I am not claiming

**The competing-limits model is not new.** Sample every mechanism that could stop the column — the
spill point, capillary failure of the top seal, a leaking fault, tilting after charge — take the
shallowest active one in each realisation, and never blend them. Hood set that out in 2019 and
2024. Beha et al. (2012) sampled it. Grant (2020) published the diagnostic that says which
mechanism won. Lowry et al. (2005) had chance-as-a-function-of-column-height in print two decades
ago. I have implemented their idea, not had it.

**The dataset is not mine.** Edmundson and co-authors did the hard part: an apex and a spill point
picked off depth-converted maps for 242 fields. Then they published the raw table openly, which is
rare and is the only reason I could check anything at all. Nothing here detracts from that. It is a
disagreement about **one estimator**, not about the data.

**And it is one basin.** I went looking for a second public dataset relating column height to
closure height, outside Norway, and could not find one. Not a paywalled one — *any* one. The
reason is in Edmundson's own introduction: measuring a closure height means picking an apex and a
spill off a depth-converted 3D volume, per field, which is months of interpretation rather than a
database query. So they say, in as many words, that "few studies of this kind have been carried out
before". Every other compilation I could find reports column-height *distributions* with no trap
geometry at all, which cannot answer this question.

If you know of one, I would genuinely like to hear about it.

## The tool

I have built the whole thing as a free, open-source app: the competing-limits engine, the
censoring correction, the comparison of your own prospect against the corrected record, and an
importer so a company can run the same correction on its own confidential trap-fill database
without the data leaving the browser.

It is one of four tools I maintain, each doing one job: **E-POS** for element risk, **SCOPE-HC**
for volumetrics, **HCWC Distribution Builder** for the contact, and **WellVolPOS** for the chance
at a well location.

It will not tell you whether to drill. It produces one input to that decision, honestly, with its
provenance attached.

---

*Lars Hjelm. The app, the code and the data are open — links in the comments.*
