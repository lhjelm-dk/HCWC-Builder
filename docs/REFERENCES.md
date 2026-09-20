# References

Every entry below was checked on **25 August 2026**. DOIs were validated against the Crossref API,
which returned the author, year, journal and pages shown, so the metadata here is the publisher's,
not this project's. Links marked **⚠ bot-blocked** return 403/405 to an automated request but open normally in
a browser; that is a publisher anti-scraping setting, not a dead link.

Access is marked from the position of someone with **no institutional subscription**, which is the
situation this project is in.

---

## Method — how to represent column height

**Beha, A., Christensen, J. E. & Young, R. (2012)** · *A general method for the consistent volume assessment of complex hydrocarbon traps.*
**Journal of Petroleum Geology 35(1), 85–98.** DONG E&P and Rose & Associates.

**The closest published precedent to this tool's engine.** Enumerates every combination of trapping
elements working or failing, weights each scenario, and collapses the result onto leak-point
frequencies — which is what the competing-limits argmin computes by simulation. Their worked example
(0.60 / 0.12 / 0.28 at 2050 / 2100 / 2150 m) is reproduced exactly by
`tests/test_engine.py::TestBeha2012PublishedExample`, and is the only **external** validation this
project has.

Also the clearest published statement of the POS/volume split this tool is built on: down-dip
trapping elements *"will not reduce the probability of finding hydrocarbons at the prospect
location [but] will influence the probability of deeper hydrocarbon-water contacts"*, and scenario
weighting is *"normalised to the success rate of the prospect"*. Full review in
`docs/reviews/BEHA_2012_REVIEW.md`.

**Monigle, P.W., Hedayati, T.S. & Goulding, F.J. (2025)** · *Integrated and improved direct
hydrocarbon indicators: a step forward in petroleum risk discrimination.* AAPG Bulletin
**109**(5), 617–636. doi:[10.1306/04042524030](https://doi.org/10.1306/04042524030)
🟢 **Gold Open Access, CC-BY.**
> **The closest published work to the DHI half of this tool**, from ExxonMobil, with Ken Hood
> among the editors. Bayesian integration of a DHI score with a geological prior by the same
> Simm & Bacon update this app uses; absence of an expected anomaly as negative evidence; and
> an **empirically calibrated contact weight** — `w = min(2 x DHI score, 0.95)` — from 400+
> drilled DHI prospects. That 0.95 is the external referent the strength axis lacked; see
> `docs/reviews/MONIGLE_2025_REVIEW.md`. Also states the element-attribution rule as policy.

**Hood, K.C. (2024)** · *Hydrocarbon Column Heights, Part 1* and *Part 2*. Rose & Associates blog,
7 May 2024, from Hood (2019), Risk Coordinators Workshop #17, Houston. Released by ExxonMobil.
🟢 **Free** · https://www.roseassoc.com/hydrocarbon-column-heights-part-1/ ·
https://www.roseassoc.com/hydrocarbon-column-heights-part-2/
> The method this tool implements: build background column height and geometric limits as
> *separate* distributions and take the minimum per realisation. Part 1 shows why merging them into
> one weighted input distribution "produces non-geologic and erroneous results" — apparent volume
> can increase when a leak is added. Part 1 also gives the assessment-minimum rule: link it to a
> minimum column height, not a minimum volume, because only that connects to seal capacity.

**Grant, N.T. (2020)** · *Using Monte Carlo models to predict hydrocarbon column heights and to
illustrate how faults influence buoyant fluid entrapment.* Petroleum Geoscience **27**(2),
petgeo2019-156. doi:[10.1144/petgeo2019-156](https://doi.org/10.1144/petgeo2019-156)
🔴 **Paywalled** ⚠ bot-blocked · *Crossref: Grant, 2020, Petroleum Geoscience*
> **The closest prior art.** Monte Carlo over fault seal capacity, fault orientation, regional
> stress tensor and trap geometry; models juxtaposition *and* membrane seal, plus hydrodynamics and
> reactivation risk; 1D, referenced to the crest. Outputs the column-height distribution **and
> "column height control statistics"** — i.e. the argmin diagnostic, already published. Also reports
> gas/oil phase partitioning by leak mechanism.

**Grant, N.T. (2019)** · *Stochastic modelling of fault gouge zones: implications for fault seal
analysis.* Geological Society, London, Special Publications **496**, 163–197.
doi:[10.1144/SP496-2018-135](https://doi.org/10.1144/SP496-2018-135)
🔴 **Paywalled** ⚠ bot-blocked
> Populates a fault zone with a random assemblage of shale smears, shaly gouge, cataclastic gouge
> and low-strain host-rock lenses; harmonic-averages permeability, arithmetic-averages Vshale.
> Produces a **distribution** of fault-rock permeability where this tool has a single SGR-derived
> value. The strongest available upgrade to the fault-leakage limits.

**Bretan, P. (2016)** · *Trap Analysis: an automated approach for deriving column height predictions
in fault-bounded traps.* Petroleum Geoscience **23**, 56–69.
doi:[10.1144/10.44petgeo2016-022](https://doi.org/10.1144/10.44petgeo2016-022)
🔴 **Paywalled** ⚠ bot-blocked · *note the unusual DOI — `10.1144/10.44petgeo2016-022`, not `10.1144/petgeo2016-022`, which is unregistered*
> Deterministic. All faults bounding a trap must be analysed as **one coherent structural element**;
> derives the **Fault Leak Point**, the weakest point across all of them, which is "trap-critical"
> if it supports a contact shallower than structural spill. The right way to think about the fault
> leakage limit.

**Lowry, D.C., Suttill, R.J. & Taylor, R.J. (2005)** · *Advances in risking exploration prospects.*
The APPEA Journal **45**(1), 143–158. doi:[10.1071/AJ04012](https://doi.org/10.1071/AJ04012)
🔴 **Paywalled** (USD 40) · reviewed from the abstract only — see `docs/reviews/LOWRY_2005_REVIEW.md`
> **Chance as a function of column height, in print in 2005.** One of their three named shortcomings
> of conventional risking is that *"prospect risk is dependent on reserve size"*, and the worked case
> is this tool's exactly: a mapped closure *"which has suspect seal capacity that may limit the column
> height to something less than full-to-spill."* Their remedy is to *"build a variable risk array for
> a range of column heights"* and sum incremental risked NPV over the layers. **The depth-risk curve
> on tab ④ is therefore not novel, and neither is the rule on tab ① linking the risk criterion to a
> minimum column.** What could not be established from the abstract is whether their array is derived
> from *competing mechanisms* or stated band by band — the difference between prior art for the
> engine and prior art for the level above it. Get the PDF before citing.

**Sawamura, K. & Nakayama, K. (2005)** · *Estimating the amount of oil and gas accumulation from top
seal and trap geometry*, in **Faults, Fluid Flow, and Petroleum Traps**, AAPG Memoir 85.
🔴 **Paywalled** · not yet read in full
> Classifies traps by **which limit controls them** — pure spillpoint-limited, capillary-limited,
> mixed — and gives the deterministic competing-limits case: a hanging wall that can only reach 285 m
> before top-seal entry pressure binds, against a 302 m fill-to-spill. `min(seal, spill)` as a
> statement about trap type, and a cleaner citation for the *competition* than Lowry.

**Ogilvie, S.R., Dee, S.J., Wilson, R.W. & Bailey, W.R. (2020)** · *Integrated Fault Seal Analysis:
An Introduction.* GSL Sp. Pub. **496**, 1–8.
doi:[10.1144/SP496-2020-51](https://doi.org/10.1144/SP496-2020-51) · 🟡 **Introduction often free**
> Context for the whole SP496 volume, which is where Grant (2019) sits.

---

## DHI evidence

**Simm, R. & Bacon, M. (2014)** · *Seismic Amplitude: An Interpreter's Handbook.* Cambridge
University Press. Chapter 11, amplitudes in prospect evaluation.
🔒 **Book.**
> The two-state Bayesian update of a prior chance by a likelihood ratio, `P(G | s) = R·P(G) /
> (R·P(G) + 1 − P(G))`, which is `hcwc.core.dhi.simm_update`; the interpreter's DHI checklist.
> Also the source Monigle *et al.* (2025) cite for their integration.

**Simm, R. (2020)** · *DHI scenarios in exploration: a personal view.* First Break **38**(2),
37–42. doi:[10.3997/1365-2397.fb2020008](https://doi.org/10.3997/1365-2397.fb2020008)
🔒 **Paywalled.**
> High-grade DHI scenarios, with characteristics consistent with the trap and indicative of a
> fluid contact, warrant an uplift to the chance; low-grade ones, amplitude and AVO anomalies or
> low-confidence fluid indications, generally do not. The verbal bands on `LR` in
> `dhi.strength_bands` and the single-channel ceiling of 10 are attributed to Simm; the page
> that carries them is to be confirmed against the handbook and this paper.

**Kjønsberg, H., Hauge, R., Kolbjørnsen, O. & Buland, A. (2010)** · *Bayesian Monte Carlo method
for seismic predrill prospect assessment.* Geophysics **75**(2), O9–O19.
> The one published measurement of a combined likelihood ratio: prior 0.53, posteriors 0.76,
> 0.97 and 0.44 at three locations offshore Norway, implied ratios 2.8, 28.7 and 0.70, from a
> full prestack inversion. `R_CAP = 50` sits above the 29.

**Roden, R., Forrest, M. & Holeywell, R. (2012)** · *Relating seismic interpretation to
reserve/resource calculations: Insights from a DHI consortium.* The Leading Edge **31**(9),
1066–1074.
> The drilled-prospect database behind the paper (217 prospects then, 400+ now): amplitude down-dip
> conformance to structure is the most diagnostic characteristic, flat spots rank high, and
> a DHI Index above 20 % approached full success. Also the list of what is misread as a flat
> spot: channel bases and edges, low-angle faults, diagenetic boundaries, processing artefacts.
> These are the characteristics `c` grades, so this ranking is why `c` and `LR` move
> together at elicitation (8.1.6, Figure 5.1.3a).

**Nixon, S., Hallam, T. & Constantine, A. (2018)** · *Ranking DHI attributes for effective
prospect risk assessment applied to the Otway Basin, Australia.* ASEG Extended Abstracts, AEGC
2018, Sydney. Held in `_private/papers/`.
> Concur with Roden et al.'s ranking, with flat spots raised to "highly definitive"; conformance
> with depth structure "uncommon in the absence of hydrocarbons", while AVO anomalies and bright
> spots have many non-hydrocarbon causes. Bayes' theorem applied with basin-calibrated DHI
> statistics.

## Empirical column-height data

**Edmundson, I., Davies, R., Frette, L.U., Mackie, S., Kavli, E.A., Rotevatn, A., Yielding, G. &
Dunbar, A. (2021)** · *An empirical approach to estimating hydrocarbon column heights for improved
pre-drill volume prediction in hydrocarbon exploration.* AAPG Bulletin **105**(12), 2381–2403.
doi:[10.1306/03122119223](https://doi.org/10.1306/03122119223)
🟢 **Preprint free:** doi:[10.31223/osf.io/zsakb](https://doi.org/10.31223/osf.io/zsakb) ·
🟢 **DATA FREE, CC-BY 4.0:** https://osf.io/6ysbv/ (project https://osf.io/953cy)
> 242 NCS discoveries with column height, trap height, burial depth and trap-fill ratio. A 3×3×4
> forward-probability matrix over burial depth × trap height → trap fill. **The raw table is open**
> and is in this repo at `reference/edmundson_2021_ncs_columns.csv`. Reported r = 0.86 (column vs
> trap height) and r = 0.31 (column vs burial depth); both reproduce exactly from the data.
> ⚠ **Discoveries only, and 111/242 are filled to spill and therefore right-censored.** See
> `hcwc/core/censoring.py`.

**Edmundson, I., Davies, R., Frette, L., Kavli, E., Rotevatn, A. & Dunbar, A. (2019)** · *An
Empirical Approach to Reduce Uncertainty when Predicting Hydrocarbon Column Heights during Prospect
Evaluation.* Fifth International Conference on Fault and Top Seals, 1–5.
doi:[10.3997/2214-4609.201902297](https://doi.org/10.3997/2214-4609.201902297) ⚠ bot-blocked
> The conference version of the above.

**Graham, C.B., Savrda, A.M., Davis, S., Walker, P.E., Sykes, M.A. & Corona, F.V. (2015)** ·
*Improving Hydrocarbon Column Height Estimates: Results From a Global Synthesis.* AAPG Search &
Discovery #90216, ACE Denver. 🟢 **Abstract free** ·
https://www.searchanddiscovery.com/abstracts/html/2015/90216ace/abstracts/2088450.html
> ExxonMobil global compilation. **40% of structures shorter than 250 m fill to synclinal spill.**
> For 250–800 m traps, a uniform column-height distribution blended with filled-to-spill "weighted
> between zero and 0.4". Reports that fill patterns for broad, low-relief traps **contradict** the
> hypothesis that cryptic-leak probability rises exponentially down structure. Suggests a
> shallow-leak contact model where prospect area ≫ effective seal area.
> ⚠ Only the abstract is public — the actual distributions were never published.

**Niemann, J.C. (2000)** · *Statistical Distributions of Hydrocarbon Column Heights for Gulf of
Mexico Trap Types and Seals.* AAPG Discovery Series No. 1 (abstract).
🟡 **Abstract only** ⚠ bot-blocked ·
http://archives.datapages.com/data/specpubs/discovery1/D0127/D0127001.HTM
> **804 reservoirs in 305 fields.** P5/P10/P50/P90/P95 column heights by trap type and lateral-seal
> combination. Fault-seal traps in hydrostatic/low-overpressure sections — nearly half the
> population — show a relatively narrow distribution; salt-flank traps and high-pressure-gradient
> sections are much broader. Concludes lognormal.
> The **second-largest published column-height dataset** after Graham, and the only one that
> stratifies by trap type. Worth chasing for the actual tables.

**Tanjung, B.A. (2014)** · *Statistical Distributions of Hydrocarbon Column Heights for Determining
Acreage of Prospect to Estimate Hydrocarbon Resources in Kakap Block.* IPA (abstract).
🟡 **Abstract only** · http://archives.datapages.com/data/ipa_pdf/2014/IPA14-G-173.htm

**Atakan, K.A. (2016)** · *Controls on hydrocarbon column-heights in the Eastern province of
Haltenbanken, the Norwegian Sea.* MSc thesis, University of Bergen.
🟢 **Free, open PDF** · https://hdl.handle.net/1956/15381
> 15 Haltenbanken structures with contacts mapped against spill points and hand-classified: 9 filled
> to spill, 1 underfilled, 1 mixed, 1 with a contact *below* spill, 4 indeterminate.
> **An open answer key for a censoring pipeline.**

---

## Retention and leak mechanisms

**Edmundson, I., Rotevatn, A., Davies, R., Yielding, G. & Broberg, K. (2020)** · *Key controls on
hydrocarbon retention and leakage from structural traps in the Hammerfest Basin, SW Barents Sea:
implications for prospect analysis and risk assessment.* Petroleum Geoscience **26**(4), 589–606.
doi:[10.1144/petgeo2019-094](https://doi.org/10.1144/petgeo2019-094)
🟢 **Preprint free:** doi:[10.31223/osf.io/uzg64](https://doi.org/10.31223/osf.io/uzg64)
> **Ranks the retention mechanisms empirically.** Across-fault and top-seal capillary breach, and
> top-seal mechanical failure, are *unlikely* to have caused leakage; **top-seal breach by tectonic
> reactivation of faults**, plus fault dilation from de-glaciation, is the probable mechanism. A
> direct, open, empirical prior on the retention limits — and the argument for adding a
> reactivation limit row.

**Swarbrick, R., Lahann, R. & O'Connor, S. (2019)** · *Estimating Hydrocarbon Column Heights Based
on Seal Capacity.* AAPG ACE, San Antonio (abstract). 🟢 **Abstract free** ·
https://www.searchanddiscovery.com/abstracts/html/2019/ace2019/abstracts/466.html
> Challenges three assumptions behind capacity-based column prediction: that buoyancy can cause
> hydraulic failure, the proportion of hydrocarbon lost at seal failure, and the sensitivity to
> input uncertainty. Argues fracture pressures **overestimate** the pressure needed to reopen
> existing faults. A caution to read against the seal-capacity calculation.

**Pillar, J. (2019)** · *Hydrocarbon Column Height Modelling for Prospect Resource Assessment. A New
Innovative Approach.* 81st EAGE Conference & Exhibition, 1–5.
doi:[10.3997/2214-4609.201901555](https://doi.org/10.3997/2214-4609.201901555)
🔴 **Paywalled** ⚠ bot-blocked
> A **Poisson** forward model of hydrocarbon–water contacts integrating trap geometry — a genuinely
> different formalism for cryptic leaks, and worth implementing as an alternative limit type.

---

## Sources for the seal-capacity calculation

| Reference | For |
|---|---|
| **Sperrevik, S. et al. (2002)** | fault permeability: `Kf = 80000·exp(−(19.4·SGR + 0.00403·Zmax + (0.0055·Zf − 12.5)·(1−SGR)^7))` |
| **Manzocchi, T. et al.** | fault permeability: `log Kf = −A1·SGR − A2·log(D)·(1−SGR)^A3` |
| **Yang, Y. & Aplin, A.C. (1998)** | pore-throat radius from porosity / void ratio. Not the source of the gas–water tension line once attributed to it; the oil–water line was replaced on 15 Sep 2026 (`archive/development_notes/IFT_CHECK_2026-09-15.md`) |
| **Sales, J.K. (1997)** | closure height / seal capacity / fluid type interplay; cited by Graham |
| **Hansen (1996)** | depth calibration of the fitted entry-pressure distributions |

---

## Statistical method

**Milkov, A.V. (2017)** · *Integrate instead of ignoring: Base rate neglect as a common fallacy of
petroleum explorers.* AAPG Bulletin **101**, 1905–1916.
doi:[10.1306/0327171622817003](https://doi.org/10.1306/0327171622817003) 🔴 Paywalled

**Wand, M.P. (1997)** · *Data-Based Choice of Histogram Bin Width.* The American Statistician **51**,
59–64. 🟡 Third-party copy: https://www.stat.cmu.edu/~rnugent/PCMI2016/papers/WandBinWidth.pdf
> Cited by Edmundson for bin selection but not actually applied — they use the square-root rule and
> then hand-pick unequal bins.

**Tobit / right-censored regression** — the statistical machinery behind
`hcwc/core/censoring.py`. Standard survival analysis; the relevant construction is a normal
likelihood for uncensored observations plus a survival term `P(S ≥ H)` for censored ones. No
petroleum-specific reference exists, which is the gap this project fills.

---

## Data sources

| Source | What | Access |
|---|---|---|
| **Edmundson supplement** | the 242 NCS rows | 🟢 https://osf.io/6ysbv/ CC-BY 4.0 |
| **Sodir (ex-NPD) FactPages** | discoveries, wellbores, formation tops, well histories | 🟢 open, NLOD 2.0 · https://www.sodir.no/en/facts/data-and-analyses/open-data/ |
| **Sodir ArcGIS Data Service** | same, programmatically — 47 layers, 68 tables | 🟢 https://factmaps.sodir.no/api/rest/services/DataService/Data/MapServer |
| **Sodir CO2 Storage Atlas surfaces** | ZMAP depth grids for NCS reservoir horizons — the only open route to apex and spill | 🟢 `https://www.sodir.no/4a612b/globalassets/1-sodir/fakta/co-to/20190906_co2_surfaces.zip` |
| **Diskos** | Norwegian national data repository | 🟡 index open, data by order |

⚠ **Sodir publishes no fluid contacts, no apex and no spill point as structured data** — confirmed
by schema inspection. Contacts *are* stated in the free-text `wellbore_history` narratives and are
recoverable by text mining at perhaps 50–70% coverage.

FactPages CSV export pattern (the `IpAddress`/`CultureCode` pair is mandatory; without it the server returns HTTP 500):

```
https://factpages.sodir.no/public?/Factpages/external/tableview/<REPORT>&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used&CultureCode=en&rs:Format=CSV&Top100=false
```

---

## Companion tools

- **E-POS** — evidence-supported probability of success, ESL/Italian-flag, Bayesian DFI update.
  Supplies the element chances on tab 2.0; the DHI strength model on tab 5.1 is adapted from its
  custom-R tool. App https://e-pos.streamlit.app · code https://github.com/lhjelm-dk/E-POS
- **SCOPE-HC** — probabilistic volumes from GRV, reservoir and fluid inputs; the resource column
  the WellVolPOS export on tab 7.0 leaves out. Planned: reading the 101-percentile contact
  distribution exported there. App https://scope-hc.streamlit.app · code
  https://github.com/lhjelm-dk/SCOPE-HC
- **WellVolPOS** — well probability of success and volume from a stochastic prospect model;
  consumes the trial table and the per-element curves from tab 7.0. App
  https://wellvolpos.streamlit.app · code https://github.com/lhjelm-dk/WellVolPOS
- **SLB GeoX** — commercial prospect assessment; the export target.
  https://www.slb.com/products-and-services/delivering-digital-at-scale/software/geox
- **Rose & Associates RoseRA** — commercial prospect risk. https://www.roseassoc.com/
- **ArianeLogiX, Ariane for Oil & Gas** — commercial risk and volume assessment of prospects,
  integrating subsurface uncertainty, seal integrity, charge and phase prediction across
  segments. https://ariane-logix.com/oil-gas/
