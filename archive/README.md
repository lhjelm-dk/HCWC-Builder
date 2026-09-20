# Archive

Material the application no longer uses, kept rather than deleted (Phase 2 of the clean-up,
18 September 2026). Nothing under `archive/` is imported by the application or read by a test
that exercises the application; a test may check that a file listed here still exists.

| directory | what | superseded by |
|---|---|---|
| `superseded_notes/` | the five theory notes absorbed into `docs/THEORY.md` on 16 Sep 2026, with their index | tab 8.1 (`docs/THEORY.md`) |
| `old_figures/` | the raster workflow figure of 16 Sep, the matplotlib paper figures and the script that drew them, an unused concept sketch | `docs/figures/` drawn by `scripts/workflow_figure.py`, `scripts/post_images.py`, `scripts/paper_figures.py` |
| `development_notes/` | signed working notes and checks that shaped the model and are cited by docstrings for their history | `docs/THEORY.md` 8.1.3 to 8.1.6, `docs/REFERENCES.md`, the audits in `docs/` |

Safe to ignore when reading the application. Read when a docstring cites a note by name.
