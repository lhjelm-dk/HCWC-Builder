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
| **2** | **Move the estimator's defence off tab ⑥** | §§3–5 — why the published regression measures the wrong thing, whether the corrected model fits, and the second bias — argue for *the method*. They are about half of the largest tab in the app and they are not the user's question. Tab ⑧ Theory is where they belong; tab ⑥ then answers "am I optimistic?" in four sections instead of nine. | small |

---

## A1b · Small and aligned (done 15 Sep 2026)

**An MICP displacement-pressure route into the seal calculator.** ZetaWare's quick seal-capacity
calculator, which Lars likes (15 Sep 2026), takes a mercury–air displacement pressure from MICP
(480 dyne/cm, 140°) and converts it to the largest connected pore-throat radius, then applies the
same balance this calculator does. Ours takes the radius directly. Accepting a displacement pressure
as an alternative input is one conversion, `r = 2·γ_Hg·cos θ_Hg / P_d`, beside the radius slider;
where a lab MICP exists it is the number the assessor has. Small.

## A2 · Planned in detail, not started, and not wanted yet (Lars, 15 Sep 2026)

**Capillary-controlled two-phase columns** — the one real gap the Hood (2019) review found (`docs/HOOD_2019_REVIEW.md`). The app has no seal-capacity route to a gas–oil contact, and the charge-driven route exists in `hcwc.core.charge` but is wired to no widget. Fully planned in **`docs/PLAN_DUAL_PHASE_SEAL.md`**, including the one thing to settle first: the derivation gives a 45 % gas cap on this app's own interfacial-tension correlations where Hood quotes 20 %, and the disagreement is entirely in oil–water tension.

Its cheap sibling — commodity scenarios from realisation proportions, Hood's slide 19 — needs no new physics and would go first. Both wait: Lars, 15 Sep 2026, does not want the two-phase seal implemented yet, and step 0 (the oil–water tension) is closed by `archive/development_notes/IFT_CHECK_2026-09-15.md`.

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
| `LINKEDIN_POST.md` | The post that links to the article: text, eleven images from `docs/post/` (exported from the app by `scripts/post_images.py`), captions and posting notes. Placeholders for the three URLs. |
| `ARTICLE_LONG_2026-09.md` | The 9 700-word manuscript the LinkedIn article (`ARTICLE.md`, tab 8.2) was shortened from on 16 Sep 2026; kept for a journal version. Its five figures stay in `docs/figures/`. |
| `DHI_AUDIT_2026-09-16.md` | Mathematical audit of the DHI chain (p_valid, seen/partial/absent likelihoods, strength, dependence, limiting cases, the POS identity). No inconsistency found; three documentation defects corrected; 22 tests added in `tests/test_dhi_audit.py`. |
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
`archive/superseded_notes/BENCHMARK_SOURCES.md` (now 8.1.8 of `docs/THEORY.md`). Edmundson appears to be the only openly redistributable dataset
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

- **Caption density (was A4): not to be built.** A Full/Brief control folds the second half of
  every caption, and Lars removed exactly that on 28 Aug 2026: the second half is where the
  caveats are, and a caption that can be half-read is one whose second half nobody reads. The
  tone pass of 14 Sep 2026 shortened the captions instead, which was the answer. 15 Sep 2026.

- **A second worked prospect**, spill-limited (`reference/example_prospect_spill.hcwc.json`,
  "Vestre Low"): the spill point sets the contact in about seven realisations in ten where the
  first example is seal-dominated. 15 Sep 2026.
- **One-click example loading on tab ①**, both examples, beside the tab list. The shipped
  example had been unreadable since the stack views became per-tab (two dead keys the reader
  refused); the reader now drops them. 15 Sep 2026.

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
