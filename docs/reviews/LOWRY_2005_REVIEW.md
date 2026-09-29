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

## A secondary account, 29 Sep 2026

Lars supplied a long summary of the paper's method: 19 geological risk factors, a Level of Knowledge
rating beside each probability, the variable risk array, incremental risked NPV by layer, and an EMV
sensitivity to the chance of success.

**It is second-hand, and it says so.** It hedges throughout — "I have not found evidence that the
paper presents a full formal Bayesian network", "the exact risk factors should be read from the
original article's tables" — and its most specific claims, the 19 factors and the
knowledge-against-probability plot, are attributed to *later papers citing Lowry* rather than to
Lowry. It therefore **does not close the four questions below**, and nothing in it may be written
into the manuscript as a statement about what the paper does. If anything it deepens the doubt on
question 1: it describes the array as *stated per band*, which is the assembled form, but only from
secondary sources.

Two ideas in it are worth keeping on their own merits, whoever they belong to.

**Monotonicity is an argument for a derived array.** A chance-against-column-height array must be
non-increasing: `P(H ≥ h₂) ≤ P(H ≥ h₁)` for `h₂ > h₁`, since a column that reaches the deeper level
has reached the shallower one. Ours has that property by construction, because it is read off one
sample of `min(active limits)`. An array assembled band by band, a risk stated for each
column-height slice, can violate it without the assessor noticing. That is a cleaner argument for
deriving the array than the ones in 8.1.3, and it costs a sentence.

**Level of Knowledge is the one idea this tool has no equivalent of.** The tool labels each
assumption elicited, heuristic or a modelling choice (5.1.6), which says *what kind* of number it
is, and reports an effective sample size, which says how far the *seismic* update displaced the
geology. Neither says how well an elicited input is known. A seal capacity from one analogue and one
from a calibrated dataset enter the same distribution and are treated alike. Carried per limit, a
knowledge rating would let the run checks flag an extreme probability resting on thin evidence,
which is the failure the LOK idea exists to prevent. Recorded as future work in the paper's
Section 15.3.

The rest — the 19-factor taxonomy, the NPV and EMV arithmetic, the oil-against-gas optimism finding
— is outside what this tool does. The volume and value handoff is deliberate (see above), and the
taxonomy question is already answered here by the element-against-limit table of 8.1.2, which exists
to stop one uncertainty being entered as several.

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
