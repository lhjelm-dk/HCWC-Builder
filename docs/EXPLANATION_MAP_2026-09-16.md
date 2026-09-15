# Explanatory material: audit and map to the Tab 8 structure

**16 September 2026.** Before the restructure that makes Tab 8 the single source of scientific
explanation. Every explanatory block of 25 words or more in the operational tabs was inventoried
by parsing the `st.markdown` / `caption` / `info` / `warning` / `expander` / `n.plot` / `n.table`
calls (245 blocks, 18 500 words), together with the section structure of `docs/*.md`. Each block
is mapped below to one of three fates:

- **KEEP** — operational: what is entered, what the output means, what to check. Stays, trimmed
  to that.
- **REF** — the block stays as one or two sentences plus `Method: see 8.1.x`, and its argument
  goes to 8.1.x.
- **MOVE** — the block leaves the tab; its content becomes part of 8.1.x.

Blocks under 25 words (widget help, short captions) are operational by construction and are not
listed. Nothing is deleted: every MOVE and every REF has a named destination.

Word counts of explanatory text today, by file: app.py 2 700 (tab 1: 1 300; tab 7: 900; tab 8:
500), prospect_tab 1 100, limiters_tab 800, results_tab 1 500, depth_risk_tab 1 000, dhi_tab
4 000, dhi_walkthrough 900, sources 2 000, empirical 4 400, trust_panel 100.

---

## 1 · The Tab 8 structure, and what feeds each section

The story runs 8.1.1 → 8.1.6; 8.1.7 to 8.1.9 are supporting. Each section names its sources; a
source listed under two sections is split, not duplicated.

### 8.1 The model in one page

One figure and about 300 words: limits sampled → shallowest active limit sets the contact →
controller recorded → chance read at a threshold → evidence reweights. **Sources:** tab 1 §1
(app.py 146, 201–205: the concept figure and its caption), the abstract of the paper. **New
text**, written once; nothing on the operational tabs restates it.

### 8.1.1 Why HCWC is an output, not a generic distribution

**Sources:** app.py 146 (tab 1 intro, 185 w); `COMPETING_LIMITS.md` "Why the limits are not
blended"; limiters_tab 408 (the tab 3 intro's second paragraph, "Limits are sampled, not
blended … Hood 2024"); results_tab 605 and 652 (the "all limits on one axis" explanation of why
flattening levels are P(active) and why blending suppresses realisations, 275 w between them);
paper §2 and §6. **Duplicates:** the blending argument is stated four times (tab 1, tab 3 intro,
tab 4.1.7 twice). One statement, here.

### 8.1.2 Competing geological limits

**Sources:** tab 1 §1 caption (app.py 205, the six mechanisms); tab 3 intro (limiters_tab 408,
first paragraph: each limit has a probability of being present and a depth or capacity);
`COMPETING_LIMITS.md` "The construction" and "What recording the controller adds"; tab 1 §3
(app.py 241–247, the controlling-limit ranking as where the effort goes); results_tab 362 (the
controlling-limit-by-depth caption, 195 w, of which the E-POS colour key is operational and the
rest is method); results_tab 479, 576 (ranking and the selection effect); paper §2–§4 and §8;
Beha et al. (2012) as the published precedent for the competing trapping-element logic, with the
worked example reproduced in `tests/test_engine.py` (`BEHA_2012_REVIEW.md`, tab 1 §3 app.py 293).
**Duplicates:** "which limit controls, and it changes with depth" is explained on tab 1 §3,
tab 3.1, tab 4.1.2 and tab 4.1.5. One explanation, here; the tabs keep the reading instruction.

### 8.1.3 HCWC, column height and POS

**Sources:** tab 1 §2 (app.py 215, 221: the assessment minimum, 220 w); prospect_tab 259 (the
minimum restated, 88 w) and 268 (zero minimum); prospect_tab 363 (P(G) as the product of element
chances, 103 w) and 286 (elements at the crest, 102 w); results_tab 151, 167, 177 (the product
`POS = P(G) × P(column ≥ h | G)` and the threshold, 200 w); results_tab 414 and 450 (chance
against threshold; P(well) at the entry depth); depth_risk_tab 83 (WellVolPOS's one location
factor against the derived per-element curves), 95 (reservoir effectiveness, two effects), 265,
433 (three readings at a well); dhi_tab 289, 1065 (the chance is a curve, not a number); the
walkthrough 73, 301, 309; `DHI_alignment.md` §2 (POS is a reading); paper §5, §16.3, §19.2.
**Duplicates:** the product identity and the threshold are stated on tabs 1, 2, 4.1 (three
times), 4.2, 5.2 (twice), 5.1 and in the paper. Once, here; every tab keeps the label "read at
h_min = … m, includes / excludes element risk" beside the number, which is content, not
explanation.

### 8.1.4 Correlation and dependence

**Sources:** limiters_tab 291 (pairs rather than a matrix; rank to Gaussian), 300 (apex–spill,
33 m against 11 m), 312 (presence draws outside the copula); sources 346 (calculator inputs
independent; density–temperature), 696 (top and base seal sampled independently), 1069 (stress
and pore pressure independent); depth_risk_tab 330 (the shared apex draw and the two spaces);
tab 1 §4 (app.py 283, the presence-independence limitation); trust_panel (realised correlation
reporting); paper §4, §7, §15 (the two DHI channels update different factors), §17. **Duplicates:**
the shared-apex coupling is explained on tab 3 sub-tab E, tab 4.2.3, tab 6 §5 and in the paper.
Once, here.

### 8.1.5 DHI updating

**Sources:** dhi_tab 250 (the no-DHI intro, 144 w), 516–537 (the two-curve strength model and
E-POS's construction, 165 w), 582–591 (the single-channel ceiling), 599–635 (Kjønsberg et al.
2010 as the one external referent, 400 w), 686–700 (Simm's bands), 1047, 1216, 1228, 1235 (the
two factors and the chance curve, 340 w), 1337 (sensitivity: two kinds of input), 1392–1416
(re-attribution of the shallowest limit, not the risk), 1462–1480 (the scenario switch as the
older method); the whole of `dhi_walkthrough.py` (932 w: Bayes' rule term by term on the live
prospect); `DHI_alignment.md` §0–§2, §5–§7; paper §9, §11, §13–§15. **Duplicates:** "character
updates P(G), geometry updates p(h | G), the product is the chance" is stated on 5.2 §5, §5b, the
walkthrough step 6, 5.3's banner, 5.4's banner and the paper. Once, here. **Decision needed:**
the walkthrough renders the derivation on the *current prospect's numbers*; it can move to 8.1.5
intact (tab 8 can read the session) or stay as 5.1. Recommendation: move it, since it is the
derivation and 8.1.5 is where a derivation belongs; 5.1 then disappears and 5.2–5.4 renumber.

### 8.1.6 Detection, contact attribution and absence

**Sources:** dhi_tab 729 (what a flat event can be), 739–755 (Monigle's body and contact
attributes; the geometric mean as a heuristic), 783 (c and the floor, 111 w), 795 (anchors for
c, 126 w), 811–851 (the detection function and its shape), 448, 502 (pick shape and partial
conformance captions, 235 w), 465 (disagreement warning), 1301 (the modelling-choices list,
240 w: logistic D(h), one fluid, absence within G and on the chance, spurious density, pick and
well multiplied, the floors); the walkthrough steps 2–4; `DHI_alignment.md` §3–§4; paper §10, §10.1–§10.3, §12, §14.1. **Duplicates:** the floor `1 − c` and what it bounds is
stated on 5.2 §3 (twice), 5.2 §6, walkthrough step 4, the paper §14.1. Once, here.

### 8.1.7 Empirical benchmarks and censoring

**Sources:** empirical.py 228 (the dataset and the names), 353 (the two crossings, 285 w),
426–520 (§3–§5: what the published regression measures, the calibration, the shared-apex bias,
about 550 w), 508 (the Graham correction), 580 (the search for a second dataset, 144 w), 598–608
(why the axis is column height; the point mass at spill), 742 (probit and log), 749, 775, 784
(why the benchmarks cannot be conditioned on a DHI, 204 w), 820 (the published estimator, 225 w),
950, 1151 (a weight, not a Bayesian update), 1227 (a sanity check, not a score), 1238, 1345,
1361, 1377 (base rates), 1387–1401 (scope of the claims, 210 w); sources 418 (the shrinkage
prior), 447, 526–553; `LIKELIHOOD_OR_PRIOR.md`, `WEIGHT_NOT_BAYES.md`, `BASE_RATE_NEGLECT.md`,
`BENCHMARK_SOURCES.md` in full; paper §7. **Duplicates:** "a benchmark is a second prior, not a
likelihood" is stated on tab 6 §7 (twice), §8 (twice), §9, tab 3's seal shrinkage, tab 8's
worked example, and in three theory notes. Once, here; tab 6 keeps the reading of each figure and
`Method: see 8.1.7`.

### 8.1.8 Validation and numerical checks

**Sources:** trust_panel 86, 96 (what the checks do and do not cover); depth_risk_tab 300–330
(the consistency test: factorised against direct, the residual); results_tab 514, 576 (thin
tornado bars; the selection effect one level up); app.py 293 (Beha's example reproduced);
`AUDIT_2026-09-14.md` (the probes and the verified-correct list); paper §16.3, §16.5. **New
text** summarising what is checked automatically and what a reader should check by hand.

### 8.1.9 Assumptions and limitations

**Sources:** tab 1 §4 (app.py 283, 403 w: the seven things the model does not do); dhi_tab
1292–1301 (5.2.6, elicited judgements and modelling choices, 305 w); sources 365 (one fluid at a
time, 243 w), 346, 1069 (independence within calculators); prospect_tab 460 (a proven column is
a discovery); empirical.py 1401 (the two uncorrected selection effects); `IFT_CHECK` (the
tension inputs are elicited, uncalibrated); paper §17. **Duplicates:** the one-fluid limitation
is on tab 1 §4, tab 3's seal calculator, tab 5.2 §6 and the paper. Once, here. **Note:** CLAUDE.md
(15 Sep) says assumptions are stated in the open on 5.2.6. That stands as a *list* with the
label on each item (elicited / heuristic / modelling choice) and `Method: see 8.1.9`; the
reasoning behind each item moves.

### 8.2 The paper

Unchanged for now. It restates most of 8.1.1–8.1.9 at length; after the LinkedIn article it is
replaced by a technical note, at which point 8.1 is the only statement of the method and 8.2 the
only long-form one.

### 8.3 References

Unchanged. The theory notes' references fold into it as their text moves into 8.1.

---

## 2 · Per-tab map

Verdicts: KEEP / REF / MOVE, with the destination. Lines are today's.

### Tab 1 · Concept (app.py)

| Line | Block | Words | Verdict |
|---|---|---:|---|
| 146 | Intro: why the contact is derived, three questions, what the tabs do | 185 | REF → 8.1, 8.1.1. Keep the three questions and the tab order (60 w). |
| 172, 196 | Tab list, examples | 150 | KEEP. |
| 201–205 | §1 the concept figure and its caption | 78 | KEEP the figure; caption REF → 8.1.2. |
| 215–221 | §2 the assessment minimum | 220 | MOVE → 8.1.3. Tab 1 keeps one sentence: success is a column of at least h_min, set on tab 2. |
| 241–247 | §3 where the effort goes; tab 6 comparison | 94 | MOVE → 8.1.2 (ranking), 8.1.7 (comparison). |
| 258–274 | §5 companion tools | 150 | MOVE → 8.3.7 (already there; duplicate). Tab 1 keeps one line with the three names. |
| 283 | §4 limitations, seven items | 403 | MOVE → 8.1.9. Tab 1 keeps `Limitations: see 8.1.9`. |
| 293–299 | Beha validation; the model is not new | 90 | MOVE → 8.1.2 (precedent) and 8.1.8 (validation). |

Tab 1 after: the title question, the tab order, the two example buttons, the concept figure with
a one-line caption, and three references. About 250 words.

### Tab 2 · Prospect (prospect_tab.py)

| Line | Block | Words | Verdict |
|---|---|---:|---|
| 164 | Save/load semantics | 58 | KEEP. |
| 202 | §1 apex is the datum; spill seeds the closure; minimum is success | 47 | KEEP (what is entered). |
| 259, 268 | Success restated; zero minimum | 125 | REF → 8.1.3. Keep the live numbers line. |
| 279 | §2 play × conditional | 75 | KEEP. |
| 286 | Elements at the crest, minimum volume | 102 | REF → 8.1.3. |
| 298 | E-POS file format | 90 | KEEP. |
| 363 | P(G) is the product; what it does not carry | 103 | REF → 8.1.3. Keep the number and "the product of the four". |
| 388 | The DHI switch and what tab 5 does | 74 | KEEP, trimmed to 40. |
| 404, 460 | Offset well as evidence; a proven column is a discovery | 110 | 404 KEEP; 460 REF → 8.1.9. |
| 144 | The floor caption | 44 | KEEP (a live reading). |
| 472, 499 | Further inputs; temperature and the tension lines | 92 | KEEP. |

### Tab 3 · HCWC limiters (limiters_tab.py, sources.py, limit_block.py)

| Line | Block | Words | Verdict |
|---|---|---:|---|
| limiters 408 | Tab intro: mechanisms grouped; sampled not blended | 92 | First paragraph KEEP; second REF → 8.1.1. |
| limiters 387, 398, 518 | Ranking caption; never sets the contact; per-limit share | 164 | KEEP, trimmed; the "elicitation effort" sentence REF → 8.1.2. |
| limiters 220, 271 | Retention is capacity not chance; no reservoir limit | 85 | KEEP. |
| limiters 291, 300, 312 | Correlation editor: pairs; apex–spill; presence outside the copula | 246 | 291 KEEP (what is entered); 300 and 312 REF → 8.1.4, each to one sentence. |
| limiters 547, 553, 568 | Summary table; phase mismatch; always-active | 191 | KEEP (checks). |
| sources 51, 69, 161 | Charge calculator: what it computes; the product; the not-limiting share | 137 | KEEP. |
| sources 195, 315, 328, 336, 346, 365 | Seal calculator: the formula; tension; density mismatch; independence; one fluid | 583 | 195, 315, 328, 336 KEEP; 346 REF → 8.1.4; 365 REF → 8.1.9. |
| sources 418, 447, 489, 496, 526, 553 | Shrinkage toward the NCS; published envelopes | 452 | 418 REF → 8.1.7 (two sentences stay); 447, 489, 496 KEEP (readings); 526, 553 KEEP. |
| sources 672–696 | Base seal as top; the offset | 141 | KEEP; 696 REF → 8.1.4. |
| sources 781, 883, 892, 917 | Area–depth table, crest and spill checks | 228 | KEEP (checks). |
| sources 1014–1104 | Mechanical seal: Grant eq. 8; gradients; independence; far from limit | 336 | 1014, 1092, 1104 KEEP; 1069 REF → 8.1.4. |
| limit_block 279 | Percentile convention | 45 | KEEP. |

### Tab 4 · HCWC (geological) and Tab 5.3 / 5.4 (results_tab.py, depth_risk_tab.py)

| Line | Block | Words | Verdict |
|---|---|---:|---|
| results 100, 106 | Basis banners | 70 | KEEP. |
| results 151, 167, 177 | Undefined chance; the product; every chance carries its threshold | 202 | REF → 8.1.3. Keep the labelled numbers and one sentence. |
| results 232 | Exceedance curve caption | 40 | KEEP. |
| results 347, 362 | Controlling limit by depth; the difference view | 343 | The colour key and the reading KEEP (60 w); the rest REF → 8.1.2 and 8.1.5. |
| results 414, 450 | Chance against threshold; P(well) | 152 | KEEP the reading; the identity REF → 8.1.3. |
| results 479, 500, 514, 549, 576 | Ranking; geological tornado; thin bars; tornado caption; selection effect | 377 | 479, 500, 514 KEEP; 549 trim to the reading; 576 REF → 8.1.8. |
| results 598 | Group minima | 27 | KEEP. |
| results 605, 652 | All limits on one axis | 275 | The view key KEEP (50 w); the blending argument REF → 8.1.1. |
| depth_risk 60, 69, 76, 83 | Banners; the decomposition and WellVolPOS's one factor | 228 | 69, 76 KEEP; 83 REF → 8.1.3. |
| depth_risk 95 | Reservoir effectiveness: two effects | 85 | REF → 8.1.3, one sentence stays. |
| depth_risk 265, 287 | Per-element curves; the DHI moves the curve | 176 | KEEP the reading; 287 REF → 8.1.5. |
| depth_risk 300–330 | Consistency test; the two spaces | 195 | 300 KEEP as the check; 324, 330 REF → 8.1.8, 8.1.4. |
| depth_risk 393, 433 | Derived against allocated; three readings | 222 | KEEP, trimmed to the readings. |
| trust_panel 86, 96 | What the checks are | 126 | KEEP; the scope sentence REF → 8.1.8. |

### Tab 5.2 · DHI (dhi_tab.py) and 5.1 (dhi_walkthrough.py)

| Line | Block | Words | Verdict |
|---|---|---:|---|
| 250 | No-DHI intro | 144 | MOVE → 8.1.5. Keep two sentences: the switch is on tab 2; what the tab does. |
| 289, 414, 465 | Threshold warning; absent-above-crest; disagreement | 231 | KEEP (checks). |
| 448, 502 | Pick shape and partial conformance captions | 234 | KEEP the reading (80 w); the rest REF → 8.1.6. |
| 516, 523, 537 | Two kinds of evidence; the E-POS construction; the populations | 210 | 516 KEEP; 523, 537 REF → 8.1.5. |
| 582, 591 | Clamp notice; the ceiling | 97 | KEEP (checks). |
| 599, 619, 635 | Kjønsberg | 400 | MOVE → 8.1.5. The expander stays as one sentence and a reference. |
| 666, 686, 700 | Strength figure; the two dots; Simm's bands | 237 | 666 KEEP; 686, 700 trim to the reading, bands REF → 8.1.5. |
| 729, 739, 755 | What a flat event can be; Monigle's attributes; the geometric mean | 202 | 729 KEEP one sentence; 739, 755 REF → 8.1.6. |
| 783, 795 | c and the floor; anchors | 237 | 783 REF → 8.1.6, keep the number and one sentence; 795 KEEP (an elicitation aid). |
| 811, 851 | Detection function | 101 | KEEP one sentence; the shape argument REF → 8.1.6. |
| 893, 904, 919, 990 | Well control; disagreement; ESS; no element risk | 219 | KEEP (checks). |
| 998, 1031 | Posterior contact | 88 | KEEP. |
| 1047, 1065, 1216, 1228, 1235 | The two factors; the chance curve; POS and threshold | 403 | KEEP the readings and the labelled numbers (120 w); the argument REF → 8.1.5. |
| 1292, 1301 | 5.2.6 assumptions | 305 | KEEP as a labelled list (120 w); reasoning MOVE → 8.1.9. |
| 1329–1480 | Diagnostics: sensitivity; re-attribution; cross-checks; scenario switch | 620 | 1337, 1374 KEEP the reading; 1392 REF → 8.1.5; 1462, 1480 MOVE → 8.1.5. |
| 1540–1573 | Well-only path | 215 | KEEP (readings and checks). |
| walkthrough (all) | Bayes' rule term by term on the live prospect | 932 | MOVE → 8.1.5 intact, or KEEP as 5.1. See the decision under 8.1.5. |

### Tab 6 · Benchmarks (empirical.py)

| Line | Block | Words | Verdict |
|---|---|---:|---|
| 228 | Edmundson; one estimator; names | 120 | KEEP, trimmed to 60. |
| 261, 335, 409 | The prospect against the population; the two figures | 199 | KEEP the readings; the 1:1 argument REF → 8.1.7. |
| 353 | The two crossings | 285 | MOVE → 8.1.7. |
| 421–520 | §3–§5 the estimator's defence (folded) | 550 | MOVE → 8.1.7 as text; the calibration and bias figures stay on tab 6 with a reading caption each. |
| 561, 578, 580 | Benchmark families; one dataset; the search | 222 | 561 KEEP; 578, 580 REF → 8.1.7. |
| 598, 608, 742, 749, 775 | The family figure and its axis | 500 | KEEP the readings (150 w); the axis argument and the point mass REF → 8.1.7. |
| 782, 784, 950, 1353 | Benchmarks cannot be conditioned on a DHI | 413 | One sentence stays at each site; the argument MOVE → 8.1.7. |
| 805, 818, 820 | The C&C series; the published estimator | 368 | 805 KEEP (what the series is); 818 KEEP; 820 MOVE → 8.1.7. |
| 876, 910, 1055, 1115, 1131, 1151, 1201, 1227 | Calibration readings; a weight not Bayes; a sanity check | 725 | KEEP the readings (250 w); 1151, 1227 REF → 8.1.7. |
| 1238, 1345, 1361, 1377 | Base rates | 304 | 1238, 1361 KEEP one sentence each; 1345, 1377 REF → 8.1.7. |
| 1387–1401 | Scope of the claims; the two selection effects | 210 | MOVE → 8.1.7 and 8.1.9. |
| 173 | Import format | 125 | KEEP. |

### Tab 7 · Export (app.py 444–674)

All KEEP: it is entirely operational. Trim 663 (two documents, 131 w) and 674 (HTML not PDF,
67 w) to half.

### Tab 8 today (app.py 683–864)

The intro (683), the theory intro (696) and the six notes are replaced by 8.1 and 8.1.1–8.1.9.
The worked base-rate example (731–817, 260 w) moves under 8.1.7. The paper and references stand.

### docs/*.md

| Document | Fate |
|---|---|
| `COMPETING_LIMITS.md` | Becomes the text of 8.1.1 and 8.1.2. |
| `LIKELIHOOD_OR_PRIOR.md`, `WEIGHT_NOT_BAYES.md`, `BASE_RATE_NEGLECT.md`, `BENCHMARK_SOURCES.md` | Become the text of 8.1.7 (four sub-parts; the negative search result as a paragraph). |
| `DHI_alignment.md` | A signed working note. Its §0 status and §2–§4 are mined for 8.1.5 and 8.1.6; the note itself leaves tab 8 and stays in `docs/` as history. |
| `ARTICLE.md` | 8.2, unchanged. |
| `REFERENCES.md` | 8.3, unchanged. |
| The five paper reviews, the audit, the plans, the checks, the open questions | Off screen, as now. 8.1.8 cites the audit; 8.1.9 cites the tension check. |

---

## 3 · Duplicates, ranked by count

| Explanation | Stated today at | Canonical home |
|---|---|---|
| `POS = P(G) × P(column ≥ h_min | G)` and the threshold | 1 §2, 2 §1, 2 §2, 4.1 ×3, 4.2, 5.2 ×2, 5.1, 6 §8, paper | 8.1.3 |
| A benchmark is a prior, not a likelihood; weight, not Bayes | 3 seal, 6 §7 ×2, 6 §8 ×2, 6 §9, 8 worked example, three notes | 8.1.7 |
| Limits are sampled, not blended | 1 intro, 3 intro, 4.1.7 ×2, note, paper §6 | 8.1.1 |
| Character updates P(G), geometry updates p(h | G) | 5.2 §5, §5b, 5.1 step 6, 5.3 banner, 5.4 banner, paper | 8.1.5 |
| The floor `1 − c` and what the pick can say | 5.2 §3 ×2, 5.2 §6, 5.1 step 4, paper §14.1 | 8.1.6 |
| The shared apex couples the picks | 3 E, 4.2.3, 6 §5, paper §7 | 8.1.4 |
| Which limit controls, and it changes with depth | 1 §3, 3.1, 4.1.2, 4.1.5 | 8.1.2 |
| One fluid at a time | 1 §4, 3 seal, 5.2 §6, paper §17 | 8.1.9 |
| Benchmarks cannot be conditioned on a DHI | 6 §7, 6 §8 ×2, 6 §9 | 8.1.7 |

---

## 4 · What the operational tabs look like after

Each figure and table keeps a caption of one to three sentences: what it shows, how to read it,
what to check. Each control keeps its help. Each section opens with at most two sentences and a
`Method: see 8.1.x` where the concept is not intuitive. Estimated explanatory words after: tab 1
250, tab 2 500, tab 3 1 200, tab 4 600, tab 5.2 1 300, tab 6 1 400, tab 7 500; about 5 800 against
18 500 today, with 8.1 carrying about 4 000 words once, and the paper as it is.

---

## 5 · Decisions before code

1. **The walkthrough (5.1).** Move to 8.1.5 with its live numbers, or keep as 5.1. Recommended:
   move.
2. **5.2.6 assumptions.** Keep as a labelled list with `Method: see 8.1.9` (recommended), or
   move whole.
3. **Tab 6 §3–§5.** The figures (calibration, bias curve) stay on tab 6 with reading captions;
   the argument moves to 8.1.7. Confirm, since it inverts the earlier decision to leave them
   folded in place.
4. **`DHI_alignment.md` off screen.** Its content is absorbed into 8.1.5 and 8.1.6; the note
   stays in `docs/` as a dated record. Confirm.
5. **Order of work.** Write 8.1 first (all nine sections, from the sources above), then trim
   the tabs against it, one tab per PR, with the render tests updated as each tab changes. The
   250-word-per-block test stays and will pass more easily.
