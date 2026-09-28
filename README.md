# HCWC Distribution Builder

A hydrocarbon–water contact distribution derived from competing geological limits, with the
controlling mechanism kept per realisation, the chance read against depth, and a DHI entered as
evidence rather than as a replacement contact. A Streamlit application with its scientific core
importable on its own.

## The model in one line each

- `P(G)`: the geological accumulation chance, the product of the element chances (tab 2.0).
- Given an accumulation, every limit (charge, spill, fault, seal capacity, seal continuity,
  mechanical failure, reservoir) is drawn for presence and depth; the shallowest active one sets
  the contact and is recorded (tab 3.0, 4.0).
- `F(h) = P(H ≥ h | G)` and `POS(h) = P(G) × F(h)`, read at the assessment minimum and at the well.
- A DHI's evidence index gives a likelihood ratio that updates `P(G)`; its contact geometry
  reweights the same realisations (tab 5.0). Posterior HCWC, controlling shares and POS all read
  one weighted sample.
- Empirical benchmarks are compared beside the result, censoring corrected, never joined (tab 6.0).

The method is stated once, on tab 8.1 (`docs/THEORY.md`); the operational tabs refer to it by
section number. The article is tab 8.2; the bibliography is 8.1.11.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tests, with the anaconda interpreter this repository is developed on:

```bash
python -m pytest -q
```

The `render` marker selects the tests that render the whole app; `-m "not render"` is the
two-minute subset CI runs on pull requests.

## Layout

| path | what |
|---|---|
| `app.py` | the Streamlit shell: the tab strip and the prospect restore; each tab is a module |
| `hcwc/core/` | the scientific model; no Streamlit import |
| `hcwc/ui/` | the tabs |
| `hcwc/io/` | prospect files, imports, exports, the report, reference data loaders |
| `reference/` | shipped data: Edmundson (2021) columns, area–depth table, examples |
| `docs/` | theory (8.1, the references as 8.1.11), audits, reviews, plans, the workflow SVGs |
| `paper/` | the article (8.2), the manuscript, the post, their figures and images |
| `scripts/` | figure and image generators, censoring analysis |
| `tests/` | the suite; `docs/BASELINE.md` records what it pins |
| `archive/` | superseded notes and figures, kept and never imported |

`docs/ARCHITECTURE_CURRENT.md` describes the structure and `docs/REPO_AUDIT.md` classifies every
file. The tone of user-facing text, the exhibit numbering and the standing constraints are stated
in `docs/ASSUMPTIONS.md` and enforced by the tests.

## Companions

E-POS supplies the element chances the builder starts from; WellVolPOS takes the contact
percentiles and per-element curves it exports (tab 7.0).

MIT licence.
