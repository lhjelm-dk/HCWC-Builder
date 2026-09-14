# A second public column-height dataset: searched 28 Aug 2026

Short answer: none found. Edmundson et al. (2021) appears to be the only openly redistributable
dataset that relates hydrocarbon column height to closure height. This note records the search so
it is not repeated, and so the tool's NCS-only coverage is a stated limitation rather than an
accident.

The search excluded Norway: the NCS is covered by Edmundson, and the point was coverage beyond it.

---

## Why the negative result is credible

The evidence is not any single dead end but three independent lines converging.

Edmundson's own literature review says so, and explains why. From the preprint (lines 75–82):

> This data- and time-intensive approach may explain why few studies of this kind have been
> carried out before.

and of the prior work it names, Fosvold et al. (2000), NCS; Niemann (2000), Gulf of Mexico;
Tanjung (2014), Malay Basin, it says they

> all conclude that the observed column heights follow a lognormal distribution.

Those are column-height distributions with no trap geometry. They cannot answer column against
closure, which is the only question the tool asks of a benchmark.

The reason is structural. A closure height means an apex and a spill point picked off a
depth-converted 3D volume, per field. It is months of interpretation rather than a database query,
which is why the data does not exist rather than merely not being published.

A consultancy writing on this topic cites Edmundson alone: Rose & Associates' two-part
column-height article uses it as its sole empirical source.

---

## Ranked, should a second dataset be funded

Nothing here is a download. All three are build projects.

| | Source | Has both fields? | Blocker |
|---|---|---|---|
| **1** | **NLOG** (Netherlands, TNO/EBN) — <https://www.nlog.nl/en/fields> | In principle yes | Column from contact + top-reservoir depth; closure only by mapping the spill contour off the per-field structural maps NLOG publishes. ~150–250 fields, manual, months. Licence not stated — confirm before redistributing. |
| **2** | **Australian Petroleum Accumulations Reports** (Bureau of Resource Sciences), e.g. [Carnarvon, GA9154](https://www.ga.gov.au/bigobj/GA9154.pdf) | Partly | The only public regulator product with a tabulated `VERTICAL CLOSURE:` field — but 9 populated entries against ~100 accumulations, and the depth field gives a contact *or* a top, never both, so column height is not derivable. 1993 Crown copyright, not redistributable. |
| **3** | **Schofield (2016)**, Durham MSc — <https://etheses.durham.ac.uk/id/eprint/11876/> | No | 129 NW European fields classified by fill, with columns. No appendix; field values exist only inside figures. Would give `filled_to_spill` and `hc_column_m` by digitising plots, never `trap_height_m`. |

---

## Checked and not usable

The recurring failure is one that looks like success: contact depths without closure geometry.
Many regulators publish contacts. Without a closure height, or a spill depth and an apex depth to
derive one from, the data cannot enter this analysis.

- **BOEM/BSEE Atlas of Gulf of America Gas and Oil Sands** — 10,235 sands in 1,042 fields, the
  largest public reservoir dataset there is. The 89-field record layout has no contacts, no crest,
  no spill, no closure, no column height: only average subsea depth, net thickness, and a trap
  *mechanism* code. Definitively dead.
- **UK NSTA** — column height is in principle derivable (well tops give reservoir top, the pressure
  database gives gradients → free water levels). Closure height is published in no form; the
  regional depth grids are far too coarse for individual traps. Doubly a shame, because the licence
  (OGL / NSTA Open User Licence) would have been ideal.
- **Belabed (2017)**, TU Delft/EBN, offshore Netherlands K & L blocks — 122 fields with contacts,
  columns compiled for 73. Looked ideal; the report itself says operator isochore maps were *"not
  suitable for spill point analysis"*. Contacts and columns, no closure.
- **Niemann (2000)** — 804 GoM reservoirs, abstract only, Chevron-internal. Haeberle's related OGJ
  treatment of 2,543 GoM traps is aggregated by trap type, no per-field rows.
- **Tanjung (2014)** — IPA abstract only. **Graham et al. (2015)** — abstract only, confirmed again.
- **Sales (1997)**, AAPG Memoir 67 Ch.5, *Seal Strength vs. Trap Closure* — the classic reference
  for this exact relationship. Paywalled, and presents cross-plots of proprietary Marathon data
  rather than a table.
- **AAPG Datashare** — no entries on column height, trap fill, closure or seal capacity.
- **Zenodo / OSF** — nothing beyond the Edmundson deposit itself.
- **Denmark (GEUS/DEA)**, **New Zealand (NZP&M)**, **Brazil (ANP)**, **Canada (C-NLOPB/CNSOPB)** —
  production, reserves, licences, well headers, narrative geology. No per-field contact or closure
  tables.

One lead not run to ground: the CNSOPB/OERA Nova Scotia Play Fairway Analysis (2011) released a
public package including mapped structural closures. Unverified. Its closures are for prospects, so
it probably fails the "discoveries with measured columns" test.

Confidence caveat. Lyell Collection, Datapages and EarthDoc all returned 403 to automated requests.
Every positive claim above was verified by fetching and reading the document, but a paywalled paper
with an appendix table could have escaped the search.

---

## What this means for the tool

The limitation is stated. Edmundson is NCS-only and the app does not imply otherwise. A prospect
in the Gulf of Mexico compared against it is compared against Norwegian rock.

The import path is the answer rather than a workaround. Since no redistributable non-Norwegian
dataset exists, the realistic source of a non-NCS benchmark is a company's own trap-fill database,
which is what `hcwc/io/datasets.py` reads.

A repeat search needs new information. The only route to a second public dataset is NLOG, scoped as
a months-long mapping project with an open licence question rather than a data-ingestion task.
