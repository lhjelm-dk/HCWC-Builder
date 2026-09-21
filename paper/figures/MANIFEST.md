# Figures of the article: manifest

Written 2026-09-21 by `scripts/post_images.py`. Every figure below is drawn by code from the shipped prospect at the settings stated; regenerate with the scripts named and the same settings and the files are byte-for-byte the same.

## The run

| setting | value |
|---|---|
| prospect | the shipped default (Tiramisu-C4), `paper/figures/prospect.json` |
| seed | 20260825 |
| realisations | 10000 |
| assessment minimum h_min | 120 m |
| DHI evidence index | 20.0 |
| pick sigma | 10 m |
| contact attribution c | 0.36 |
| detection | h50 25 m, width 8 m, ceiling 0.90, false positive 0.5 |

## The figures

| article | file | source | caption |
|---|---|---|---|
| tab 1 / 8.1.1 | `fig0_workflow.png` | `scripts/workflow_figure.py`, the conceptual version | The model as two rows: geological, the prior; DHI evidence, the update; each ending in the probability of meeting the threshold. |
| Figure 1 | `paper_fig1_competing_limits.png` | `scripts/paper_figures.py`, hcwc/plotting/paper/figures.py | Each limit's chance of permitting a contact at least this deep, the contact as their lower envelope, and the contact distribution that follows. |
| Figure 2 | `paper_fig2_controlling_mechanism.png` | `scripts/paper_figures.py`, hcwc/plotting/paper/figures.py | The contact distribution stacked by the limit that set it, and the controlling shares. |
| Figure 3 | `paper_fig3_dhi_update.png` | `scripts/paper_figures.py`, hcwc/plotting/paper/figures.py | The contact distribution before and after the DHI, with the indicated contact band. |
| Figure 4 | `paper_fig4_chance_against_depth.png` | `scripts/paper_figures.py`, hcwc/plotting/paper/figures.py | The chance a well finds hydrocarbons against its entry depth, geological and given the DHI. |
| Figure 5 | `paper_fig5_empirical_check.png` | `scripts/paper_figures.py`, hcwc/plotting/paper/figures.py | The prospect beside the NCS record at its burial depth; inset, the filled-to-spill points. |
| manuscript Figure 2 | `fig1_competing_limits.png` | `scripts/post_images.py`, the app's Figure 4.1.1a | The competition, realisation by realisation. Left: every active limit's sampled depth in 50 realisations, the shallowest ringed in the colour of the limit that set it; the slider walks the window through all 10,000. Right: the whole distribution, its exceedance curve on the top axis, read on the realised contacts, and the 50 shown marked at their depths. Method: see 8.1.3. |
| manuscript Figure 3 | `fig2_controlling_mechanism.png` | `scripts/post_images.py`, the app's Figure 4.1.2a | The controlling mechanism at each depth, which changes down structure. Hue is the risk element in E-POS's colours (salmon charge, blue closure, yellow reservoir, green retention); lightness separates the limits within an element. Method: see 8.1.3. Bars are shares of all realisations, so bin height carries the contact distribution and each limit's bars sum across depth to its overall share. |
| manuscript Figure 3 | `fig3_chance_against_depth.png` | `scripts/post_images.py`, the app's Figure 4.1.3a | The chance against depth, and what makes it. Blue is P(z_HCWC ≥ z | G), the chance the contact lies at or below each depth, read on the realised contacts, with the contact's P90, P50, P10 and mean marked on it (h ≥ h_min). Red is the prospect chance, P(G) = 0.408 times the blue curve; the gap between the two is the element risk. The bars are the controlling limit per depth bin as shares of all realisations, the scaled view of 4.1.2. The assessment minimum is a column height; its mark is drawn at the median apex and carries the headline POS, read in column space. Read at the well entry depth the red curve is P(well). Method: see 8.1.4. |
| manuscript Figure 4 | `fig4_dhi_update.png` | `scripts/post_images.py`, the app's Figure 5.1.4a | Where the contact is, before and after the pick. Both histograms are over every realisation and conditional on the elements having worked; the lines are the posterior percentiles over the realisations above the assessment minimum. The amplitude character does not enter this figure: it updates the chance of hydrocarbons, not where the contact is given that there are. The shaded intervals are the outcomes of 8.1.8 relative to the indicated contact band, 2,227 to 2,273 m (the P99 to P1 of the pick); each carries its chance as a share of all outcomes, hydrocarbons or not. |
| manuscript Figure 5 | `fig6_chance_before_after.png` | `scripts/post_images.py`, the app's Figure 5.1.5a | The chance against threshold: P(G) × F(h) geological, P(G | s) × F(h | G, geometry) updated. The evidence index scales the whole curve; the geometry reshapes it, raising the chance near and above the indicated contact and lowering it below. The open circle is the posterior median, which lands on the pick. Method: see 8.1.8. |
| manuscript Figure 5 | `fig5_truncate_vs_terminate.png` | `scripts/paper_figures.py`, drawn from a two-limit sketch | Terminating versus truncating at spill. |
