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

## A2 · Planned in detail, not started

**Capillary-controlled two-phase columns** — the one real gap the Hood (2019) review found (`docs/HOOD_2019_REVIEW.md`). The app has no seal-capacity route to a gas–oil contact, and the charge-driven route exists in `hcwc.core.charge` but is wired to no widget. Fully planned in **`docs/PLAN_DUAL_PHASE_SEAL.md`**, including the one thing to settle first: the derivation gives a 45 % gas cap on this app's own interfacial-tension correlations where Hood quotes 20 %, and the disagreement is entirely in oil–water tension.

Its cheap sibling — commodity scenarios from realisation proportions, Hood's slide 19 — needs no new physics and should go first.

---

## A3 · The paper reviews, kept off the screen

Lars's call on 7 Sep 2026, restructuring tab 8.0: a user browsing the theory tab does not want
five documents auditing other people's papers. They are **not deleted** — they are the working
behind several of the app's design decisions, and each one changed something. They are indexed
here because `NEXT_PLAN.md` is the internal document by design and is deliberately not offered in
the app.

| | What it settles |
|---|---|
| `BEHA_2012_REVIEW.md` | The closest published precedent to the engine, and what can still be claimed as new. Scenario enumeration, not min-of-samples — the distinction the paper's §1.1 draws. |
| `HOOD_2019_REVIEW.md` | The source deck the engine is built on, read in full rather than through the Rose blog. Truncating vs terminating; fill-to-spill as an output. One real gap found: capillary-controlled two-phase columns, planned in `PLAN_DUAL_PHASE_SEAL.md`. |
| `AUDIT_2026-09-14.md` | Full numerical audit of the eleven core modules. Two defects found and fixed the same day (the derived P(well) dropped the Reservoir chance; the recommended Apex|spill correlation crashed the trust panel); fifteen limitations and polish items recorded with proposed fixes and the test each needs. |
| `MONIGLE_2025_REVIEW.md` | The closest published work to the DHI half. Supplies the empirically calibrated contact weight `min(2 x DHI score, 0.95)` — the external referent the strength axis lacked — and the question of whether `R_CAP = 50` should come down — settled 9 Sep 2026 by splitting it into a single-channel ceiling of 10 and a combination guard of 50, since the one constant was bounding two different quantities. |
| `LOWRY_2005_REVIEW.md` | What the paper behind the DHI update settles and what it does not. |
| `SEAL_CAPACITY_REVIEW.md` | Whether the capillary maths in `hcwc/core/seals.py` is right, including the two unit traps. |

`tests/test_app_renders.py::TestTheArgumentsLiveInDocuments::test_the_paper_reviews_are_kept_but_not_shown`
enforces all three halves of this: each file still exists, none is registered in `app.py`, and
each is named above.

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

**Units: metric, and that is settled.** Metres throughout, decided 28 Aug 2026 — not deferred and
not a gap waiting to be filled. Every depth, column and capacity in the tool is metres; every
density is g/cm³; interfacial tension is dyne/cm because that is how laboratories report it. A
field-unit mode was considered and rejected: two unit systems in a tool whose central argument is
that a *unit conversion error* made published seal capacities ten times too optimistic would be
buying the exact risk the tool exists to warn about.

**An imported benchmark does not travel.** It lives in the browser session and is deliberately
excluded from a saved prospect, because the file may be a company's confidential field list and a
prospect sent to a colleague must not carry it. Consequence worth remembering: a saved prospect
reopened elsewhere shows three benchmark families, not four, and nothing says a fourth was ever
there. Load the dataset beside the prospect.

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
the comparison against independent benchmark families. The tool is the apparatus; the paper is
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
