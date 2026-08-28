# What to build next

*Rewritten 27 Aug 2026. The previous version listed six accessibility items and three analytical
ones; all of them are built, and it still described a ten-tab app that no longer exists. A plan
that describes a finished thing as future work is worse than no plan — someone reads it on the
Theory tab and concludes the tool is half done.*

---

## Where this stands

**The tool is feature-complete for its own purpose.** It builds a contact distribution from
competing limits, says which limit produced it, carries that through to per-element chance against
depth, updates on a DHI without letting the update edit the geological model, compares the result
against the empirical record with the censoring corrected, and exports to GeoX, WellVolPOS and a
printable page. It audits its own arithmetic and says when a number should not be quoted.

What follows is not a list of gaps in that. It is a list of things that would make it **used**.

---

## A · Before anyone outside is asked to use it

| | Item | Why | Cost |
|---|---|---|---|
| **1** | **A second worked prospect** | One example teaches the mechanics; two teach the *judgement*, because the interesting question is what changes between them. A spill-limited closure beside the seal-limited one would show the controlling-limit diagnostic actually doing its job — which the current example, seal-dominated at 79 %, demonstrates only in one direction. | small |
| **2** | **Move the estimator's defence off tab ⑥** | §§3–5 — why the published regression measures the wrong thing, whether the corrected model fits, and the second bias — argue for *the method*. They are about half of the largest tab in the app and they are not the user's question. Tab ⑧ Theory is where they belong; tab ⑥ then answers "am I optimistic?" in four sections instead of nine. | small |
| **3** | **A *load the worked example* button on tab ①** | It is currently a sentence on ① pointing at a collapsed expander on ②. One click, on the first screen, is the difference between meeting the tool and reading about it. | small |
| **4** | **Caption density** | Three paragraphs under every figure is reassuring on the first prospect and noise on the tenth, and there is no way to turn it down. A single *brief / full* control in the header would let the tool be both. | medium |

---

## B · Open questions, not open work

**The Lowry (2005) PDF.** `docs/LOWRY_2005_REVIEW.md` is written from the abstract because the full
text is paywalled at USD 40. What the abstract cannot settle is whether their variable risk array is
derived from *competing mechanisms* or stated band by band — the difference between prior art for
the engine and prior art for the level above it. **Buy or borrow it before the manuscript cites the
paper.** The review lists the four things to check when it arrives.

**A second public benchmark: answered, and the answer is no.** Searched 28 Aug 2026 — see
`docs/BENCHMARK_SOURCES.md`. Edmundson appears to be the only openly redistributable dataset
relating column height to closure height, for a structural reason rather than an accidental one:
closure height needs an apex and a spill picked off depth-converted 3D per field, which is months
of interpretation rather than a database query. **Do not repeat the search without new
information.** The import path is the response.

**Units.** Metres throughout. Correct for the NCS, and a hard stop anywhere else. Not worth doing
until someone outside the NCS actually asks.

**The C&C benchmark is machine-local.** It loads from `reference/private/` and the app degrades
silently without it — three benchmark families instead of four, with no indication a fourth ever
existed. That is the right behaviour and it is worth remembering: nobody else's run will look like
this one on tab ⑥ §6.

---

## C · What would make it a contribution rather than a tool

The paper. The engine is not novel — Beha et al. (2012) describe it, Grant (2020) publishes the
controlling-limit diagnostic, and Lowry et al. (2005) had chance-as-a-function-of-column-height in
print two decades ago. **What is new is the censoring correction**, and it is a real finding:

> Of 242 NCS discoveries, 111 are filled to spill and therefore **right-censored** observations of
> seal capacity. Fitting them as though they measured capacity biases the column-height regression,
> and correcting for it moves the self-consistent fill rate from an observed 45.9 % to 47.4 % where
> the published figure is 32.3 %.

Everything needed to write that is in the repo: the estimator, the fit, the diagnostic figures, and
the comparison against three independent benchmark families. The tool is the apparatus; the paper is
the result.

---

## Done, so it stops being asked for

Kept short deliberately. The commit history has the detail.

- **The competing-limits engine**, with the argmin diagnostic, correlated by Gaussian copula.
- **Per-element chance against depth**, derived rather than allocated, with the independence
  consistency test and the apex-contribution split.
- **The DHI branch**: detection function, likelihood reweighting, the strength channel adapted from
  E-POS, and the two channels combined — on its own tab, unable to edit the geological model.
- **The censoring correction** and the re-analysis of the published record.
- **The benchmark comparison**: three families at the prospect's own relief, the Q–Q with named
  optimistic and conservative zones, a ±15 % corridor, and the ratio curve.
- **Save and load**, a worked example, exports to GeoX and WellVolPOS.
- **The one-page report** and the **trust panel**.
- **The workflow fixes**: the ranking on the tab where you elicit, no chance printed without a
  criterion to read it at, and ten tabs merged to eight so nothing sits off-screen.
