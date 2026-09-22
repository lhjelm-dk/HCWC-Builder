# Old figures (archive)

| file | what | superseded by |
|---|---|---|
| `fig0_workflow_2026-09-16.png` | the first, raster workflow figure | `docs/figures/fig0_workflow.svg` (hand-laid SVG, `scripts/workflow_figure.py`) |
| `fig1_competing_limits_mpl_2026-09-17.png` … `fig6_paper_mpl_2026-09-17.png` | the matplotlib paper figures | the app's own figures exported by `scripts/post_images.py` into `docs/figures/` |
| `paper_figures_mpl_2026-09-17.py` | the script that drew them; imports `hcwc.core` and is not run by anything | `scripts/paper_figures.py` (prospect.json and the concept sketch) |
| `concept_full.png` | a concept sketch nothing references | `reference/concept.png` on tab 1 |

Safe to ignore. Kept so the article's earlier figure set can be regenerated if wanted.

`article_draft_2026-09-01/`: the six app screenshots the first article draft referenced
(`archive/superseded_notes/ARTICLE_DRAFT_2026-09-01.md`); superseded by `paper/figures/`.

`superseded_2026-09-22/`: what `paper/figures/` and `paper/post/` held before the app's own
exhibits were exported there by `scripts/export_exhibits.py` — the eleven post images, the six
app exports the long manuscript used, and the five bespoke paper figures drawn by
`hcwc/plotting/paper/figures.py`. Kept because the drafts reference them.

`post_images_2026-09-22.py`: the script that exported a chosen eleven of the app's figures to
`paper/post/` and six to `paper/figures/`. Superseded by `scripts/export_exhibits.py`, which
exports every exhibit at the browser's ratio and names each by its number.
