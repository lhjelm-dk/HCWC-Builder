# Development notes (archive)

Working notes that shaped the model, kept for their history and because docstrings and tests
cite them by name. None is rendered by the app.

| file | what | where the content lives now |
|---|---|---|
| `DHI_alignment.md` | the signed working note of 25 Aug 2026 on the DHI update; its §0 records the corrected chain of 14 Sep, its later sections the earlier construction. Names a proprietary source the user-facing text does not | `docs/THEORY.md` 8.1.4 to 8.1.6; `docs/DHI_AUDIT_2026-09-16.md`; `tests/test_dhi_audit.py` |
| `EXPLANATION_MAP_2026-09-16.md` | the map of where each explanation lived before tab 8.1 became the single statement | the map paragraph under 8.1 and `CLAUDE.md` |
| `IFT_CHECK_2026-09-15.md` | the interfacial-tension check behind the elicited 18–28 dyne/cm range | `hcwc/core/seals.py` docstrings, `docs/SEAL_CAPACITY_REVIEW.md`, `tests/test_seals.py` |

Read when a docstring cites one; otherwise safe to ignore.
