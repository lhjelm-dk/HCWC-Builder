# Lowry, Suttill & Taylor (2005) — what it settles, and what it does not

**Lowry, D.C., Suttill, R.J. and Taylor, R.J. (2005). "Advances in risking exploration prospects."**
*The APPEA Journal* **45**(1), 143–158. <https://doi.org/10.1071/AJ04012>

Reviewed 27 Aug 2026 at Lars's request: *"we need to review how Lowrey et al 2005 does the competing
limits."*

*Status, 15 Sep 2026.* Lars had the paper and took its lessons into the earlier modelling that
this tool replaced; the copy is not to hand now. The figures can be seen on the paper's Semantic
Scholar page, <https://www.semanticscholar.org/paper/d6ab492ea957fe7fc901d9504ae02231002935bb>.
The reference stays in `docs/REFERENCES.md` as it is; the four checks below still want the text.

## Read this part first: what I could actually see

**The full text is paywalled** (ConnectSci / Australian Energy Producers Journal, USD 40) and is not
in `Papers/`. Everything below is from the **abstract and the publisher's article page**, plus the
way later papers cite it. That is enough to place the paper and to state what it is precedent for,
and **not** enough to compare its arithmetic with ours line by line.

**So the one thing to do before the manuscript cites it is buy or borrow the PDF.** Specifically, the
question I could not answer is whether their "variable risk array" is built from *competing
mechanisms* or from a single monotonic seal-capacity curve. That distinction is the whole difference
between "they did this first" and "they did the level above this first", and I am not going to guess
it from an abstract.

## What the abstract establishes

Three shortcomings of conventional prospect risking, one of which is ours:

> prospect risk is dependent on reserve size

and the worked case is exactly the one this tool is written around:

> the success case value is based on the mapped closure, but which has suspect seal capacity that
> may limit the column height to something less than full-to-spill

Their remedy:

> build a variable risk array for a range of column heights and calculate the incremental risked NPV
> for each layer

## What that means for this tool

**Confirmed precedent, and it is not a small one.** *Chance is a function of column height, not a
scalar* is in print in 2005 — twenty-one years before this app. Anything we write claiming the
depth-risk curve on tab ④ is novel is wrong, and would have been caught by a reviewer who knows the
APPEA volumes. This is the same correction Beha et al. (2012) applied to the engine: the ideas here
are established, and what is new is the **censoring correction on the empirical record**, not the
architecture.

**It also independently states the rule on tab ①.** "Prospect risk is dependent on reserve size" is
Lars's *"the risk criterion is hard-linked to the min HCWC depth"*, arrived at separately and stated
first by them. Tab ① should say so rather than presenting it as a house rule.

**Where the two part company, on the evidence I have.** Their layer is an **economic** object —
incremental *risked NPV* per column-height slice, summed to an EMV. Ours is a **geological** one —
`P(column ≥ h | G)` from competing mechanisms, exported for someone else to value. Two consequences:

- Their array appears to be *assembled*: a risk stated for each column-height band. Ours is
  *derived*: the bands fall out of `min(active limits)` and the tool can say **which** limit produced
  each one, which is the controlling-limit diagnostic and the reason for keeping the argmin
  bookkeeping. Whether their array is also derived from competing mechanisms is the open question
  above.
- Theirs terminates in money. Ours deliberately stops at the contact distribution and hands off to
  SCOPE-HC and WellVolPOS, because a tool that computes an NPV invites its column-height assumptions
  to be argued about in NPV terms, which is where they stop being checkable.

**The honest sentence for the manuscript**, pending the PDF:

> Chance as a function of column height rather than a scalar is not new: Lowry et al. (2005) built a
> variable risk array over column heights for exactly the fill-to-spill-versus-seal-capacity case,
> and Beha et al. (2012) sampled competing limits to produce the contact distribution. What this
> work adds is the correction of the empirical column-height record for right-censoring by
> fill-to-spill discoveries.

## What to check when the PDF arrives

1. **Is the array derived from competing mechanisms, or stated per band?** The one that matters.
2. **Do they take the minimum, or blend?** If they blend, the "never blend a leak into the
   background" argument on tab ① gains a named counter-example rather than being an abstract point.
3. **Do they state a risking criterion — a minimum column — or integrate over all heights?**
   Integrating to an EMV means never having to name a minimum, which is a real alternative to the
   position tab ① takes, and it deserves a paragraph rather than silence.
4. **Anything on right-censoring of the observed column-height record.** Almost certainly not, but a
   2005 paper about "column height is less than full-to-spill" is the most likely place for someone
   to have noticed it first, and the paper's core claim depends on nobody having.

## Related, and easier to get

- **Sawamura & Nakayama (2005)**, *Estimating the amount of oil and gas accumulation from top seal
  and trap geometry*, in AAPG Memoir "Faults, Fluid Flow, and Petroleum Traps" — classifies traps by
  **which limit controls** them (pure spillpoint-limited, capillary-limited, mixed) and gives the
  worked competing-limits case: 285 m held by top seal against a 302 m fill-to-spill. That is our
  `min(seal, spill)` as a deterministic statement, from the same year, and it is a better citation
  for the *competition* than Lowry is.
- **Sales (1997)** on seal strength versus trap closure is the older statement of the same
  competition and is worth having in `REFERENCES.md` alongside it.
