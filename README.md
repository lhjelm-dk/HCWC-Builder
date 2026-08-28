# HCWC Distribution Builder

**A hydrocarbon–water contact distribution built from competing geological limits.**

> 🚧 **Phase 6.** Every modelling branch runs — charge, seals, correlated limits, the
> competing-limits engine, the per-element decomposition and the DHI update — define limits, get a contact distribution, the controlling-limit
> diagnostics, and a genuine chance-versus-depth curve for each risk element. Still to
> Still to come: the exports to WellVolPOS and the write-up. The
> design is in [`docs/HCWC_Builder_PLAN.md`](docs/HCWC_Builder_PLAN.md) and is still open
> for challenge. Nothing here should be used for an assessment yet.

---

## Why a third tool

The contact depth is the single largest driver of prospect volume. It is also the only
input that converts a *prospect* chance into a *well-location* chance. Three tools, one
pipeline, and each owns exactly one thing:

```
E-POS                 HCWC Distribution Builder        WellVolPOS
element risk       →     contact distribution    →    well-location chance
(play + conditional,     (competing limits,           (r_location, P_well,
 Bayesian DHI/DFI)        argmin diagnostic)           at-the-well volume)
```

The **repository** and the Python package keep the shorter `HCWC-Builder` / `hcwc`
names — renaming them would break the remote, every clone and every import for a
display string.

**Every depth-dependent risk mechanism lives here and only here.** If the same
mechanisms were also modelled as a "risk rises with depth" overlay downstream, they
would be counted twice. One home for vertical risk, and this is it.

- [E-POS](https://github.com/lhjelm-dk/E-POS) — evidence-supported probability of success
- [WellVolPOS](https://github.com/lhjelm-dk/WellVolPOS) — well probability of success and volume

## The method

For each realisation, sample the apex, sample every limit that is active in that
realisation, and take the shallowest:

```
apex        ~ D_apex
h_L         ~ D_L         for each limit L active this realisation
h            = min(h_L)
controller   = argmin      ← recorded, per realisation
HCWC         = apex + h
```

Limits fall in three groups — **charge**, **trap geometry** (closure/spill, fault
juxtaposition, stratigraphic pinchout) and **retention** (fault leakage, capillary and
continuity failure of top and base seal, tilt-related spillage).

Taking the minimum of *separately sampled* limits, rather than blending them into one
weighted input distribution, is the construction Hood (2019, 2024) argues for: a leak
500 m below the crest must not suppress realisations *above* it, and a blended input
distribution does exactly that — it can even make apparent prospect volume increase.

The `argmin` bookkeeping is what makes the model answer a question the distribution
alone cannot: **which limit actually controlled the contact, and how does that change
with depth.**

## What is new here, and what is not

Honest accounting, because it matters for the paper:

| | |
|---|---|
| The competing-limits engine | **Not new.** Hood published this method. |
| Recording which limit controls the contact | **Not new.** Grant (2020, *Petroleum Geoscience* 27(2)) reports "column height control statistics". |
| Deriving **per-element** POS-vs-depth curves from group-level minima, replacing an *allocation* with a *derivation* | No published equivalent found. |
| Testing that the factorised depth-dependent POS equals the direct one — a built-in check for dependence and double-counting | No published equivalent found. |
| Treating filled-to-spill observations as **right-censored** when comparing against empirical column-height datasets | No published equivalent found. Hood names the problem in words; nobody applies the statistics. |
| Recognising that column height and trap height **share the apex pick**, so depth-conversion error manufactures a correlation between them that censoring cannot remove | No published equivalent found. |

**Two unit traps in the seal-capacity calculation are documented and asserted rather
than left to be rediscovered.** Converting interfacial tension from dyne/cm with `/100`
instead of `× 1e-3` makes capillary entry pressure **10× too high**; dropping `g` from
the buoyancy balance compounds it to **98.1×**. Both fail upward and both produce
capacities that look entirely plausible on a chart. See `hcwc/core/seals.py`.

## Status

| Phase | Content | State |
|---|---|---|
| 0 | Repo, CI, deploy path | ✅ |
| 1a | The elicited distributions | ✅ |
| 1b | Seal capacity calculators | ✅ |
| 2 | Competing-limits engine + argmin | ✅ |
| 3 | Charge–volume matching | ✅ |
| 4 | Per-element POS vs depth + consistency test | ✅ |
| 5 | Gaussian-copula correlation | ✅ |
| 6 | Exports to GeoX and WellVolPOS | — |
| 7 | DHI branch + E-POS contract | ✅ branch built; contract pending |
| 8 | Censoring-aware benchmark comparison | partly — the Statistics tab is built |

Also landed ahead of the engine, because the argument had to be settled first:
the **censored seal-capacity estimator** (`hcwc/core/censoring.py`), the **Edmundson
re-analysis** (Statistics tab), and the **GeoX percentile export** (`hcwc/io/geox.py`).

## Validation, and what it does not claim

A Monte Carlo cannot be validated trial-for-trial against anything. Saying what *is* checked, and
how, is a stronger position than a vague claim of parity.

| Layer | Validated | How |
|---|---|---|
| Distributions | exactly | analytically — `RiskNormalAlt(1%, 340, 99%, 360)` *is* the normal whose 1% point is 340 |
| Seal capacity, GRV integration | exactly | against hand-computed values, and against the published entry-pressure models as an independent second route |
| DHI Bayesian arithmetic | exactly | against E-POS, which is separately tested |
| The competing-limits engine | structurally | analytic special cases: one active limit reproduces that limit; two independent limits satisfy `P(min > z) = P(A > z)·P(B > z)`; `p_active = 0` never binds |
| The engine's *answer* | once, externally | Beha et al. (2012) enumerate a two-fault closure by hand and publish 0.60 / 0.12 / 0.28 at three leak points; the engine reproduces all three to Monte Carlo error |

The last row is the only check against a number somebody else computed, and internal checks cannot
catch a shared misconception — which is why it is listed separately rather than folded in.

## Known limitations

- **Seal capacity is treated as phase-independent.** `h_max = P_c/(Δρ·g)`, so a gas column and an oil
  column below the same seal are very different heights (Sales, 1997). Phase is carried in the charge
  branch; the capillary limits are not phase-resolved. Run phases as separate cases. Deferred to v2 as
  a deliberate scope decision.
- **Hydrodynamics and tilted contacts are not modelled.** Grant (2020) includes them; this tool assumes
  a hydrostatic, horizontal contact.
- **The empirical benchmarks are conditioned on discovery**, censored above and truncated below. The
  Statistics tab sets out what that does.

## Run it

```bash
pip install -r requirements-dev.txt
```

```bash
streamlit run app.py
```

```bash
pytest -q
```

Python 3.11 or newer — the `numpy>=2.1` / `scipy>=1.14` floors publish no wheels for
older interpreters. On Streamlit Community Cloud set the Python version under
*Advanced settings* when you create the app; it cannot be changed afterwards.

## Data and provenance

The repository carries **no** proprietary or third-party data.

- Source material — the third-party papers and the manuscript drafts — lives under
  `_private/` in the working folder and is excluded by `.gitignore`. None of it is an
  input the app reads: **a clone with none of it is a working clone.**
- `reference/edmundson_2021_ncs_columns.csv` — the 242 measured NCS discoveries — is
  **open data, CC-BY 4.0**, from the authors' own supplement at https://osf.io/6ysbv/.
  Redistributed with attribution in the file header. Their published probability matrix
  reproduces from it exactly.
- The "C&C" reservoir statistics come from an unpublished study and are read from
  `reference/private/`, which is git-ignored. The app omits that comparison series when
  the file is absent, so a clone still runs.

## References

- Hood, K.C. (2024) *Hydrocarbon Column Heights, Parts 1 & 2.* Rose & Associates blog, from Hood (2019), Risk Coordinators Workshop #17.
- Grant, N.T. (2020) *Using Monte Carlo models to predict hydrocarbon column heights and to illustrate how faults influence buoyant fluid entrapment.* Petroleum Geoscience 27(2), doi:10.1144/petgeo2019-156.
- Graham, C.B. et al. (2015) *Improving Hydrocarbon Column Height Estimates: Results From a Global Synthesis.* AAPG Search & Discovery #90216.
- Edmundson, I., Davies, R., Frette, L.U., Mackie, S., Kavli, E.A., Rotevatn, A., Yielding, G. & Dunbar, A. (2021) *An empirical approach to estimating hydrocarbon column heights for improved pre-drill volume prediction.* AAPG Bulletin 105(12), 2381–2403, doi:10.1306/03122119223. [Open preprint](https://doi.org/10.31223/osf.io/zsakb) · [data, CC-BY 4.0](https://osf.io/6ysbv/)
- Edmundson, I. et al. (2020) *Key controls on hydrocarbon retention and leakage from structural traps in the Hammerfest Basin, SW Barents Sea.* Petroleum Geoscience 26(4), 589–606. [Open preprint](https://doi.org/10.31223/osf.io/uzg64)
- Bretan, P. (2017) *Trap Analysis: an automated approach for deriving column height predictions in fault-bounded traps.* Petroleum Geoscience 23(1), 56.

Full reference list and access routes: `Papers/_Reference-sources-index.md` (working folder).

## Licence

MIT — see [LICENSE](LICENSE).
