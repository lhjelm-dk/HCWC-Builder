# HCWC Distribution Builder

Streamlit app deriving hydrocarbon–water contact distributions from competing geological limits.
Core in `hcwc/core/`, tabs in `hcwc/ui/` and `app.py`, tests in `tests/` (run with the anaconda
interpreter at `C:/Users/lhjel/anaconda3/python.exe`; the Store `python` stub on PATH is not one).
The full suite runs locally before every PR; CI runs `-m "not render"` on pull requests and
everything on `main`, because Actions minutes are scarce. A test that renders `app.py` through
AppTest carries `@pytest.mark.render`.

## Tone of user-facing text

Set 14 Sep 2026 by Lars, with tab 1 as the reference. It applies to every string a user reads:
tab body text, captions, widget help, warnings, theory notes. Docstrings and code comments are
not covered.

**Report voice, third person.** "The tool models…", "Each limiter is assigned…", "the assessor".
No *you*, no *I*, no *we*. Instructions are stated as what the control does, not as an address to
the reader: "The assessment minimum on tab 2.0 sets…" rather than "Set the assessment minimum…".

**State, do not argue.** The app says what it does and what the result means. The case for the
method — why limits are sampled rather than blended, why the reference data are censored, why
a base rate is not evidence — lives in the tab 8.1 theory notes and the paper, not in the tabs
where the work is done. No rhetorical turns ("which is not geology", "derived, not allocated",
"nobody has corrected before").

**One idea per paragraph, one to three sentences.** Cut connective filler: *yet*, *actually*,
*really*, *simply*, *of course*, *it is worth noting*. If a sentence survives without a word,
the word goes.

**Hedge where the claim is usual rather than universal.** *often*, *may*, *where present*,
*in most cases*. Flat statements are for things that are always true.

**No bold for emphasis.** Bold is for tab references (**2.0 Prospect**) and control names only.
Italics are for the titles of theory notes and papers. Never bold a phrase to make it land.

**Numbers stay.** A measured value beside a control is content, not rhetoric — keep it, state it
plainly, and give the unit.

Rewrite status: all eight tabs done. Since 16 Sep 2026 the method is stated once, in
`docs/THEORY.md` rendered as tab 8.1 (8.1.2 to 8.1.9); tabs 2 to 6 say what is entered, what the
output means and what to check, and point at "Method: see 8.1.1.x". The notes 8.1 replaced are
kept in `docs/superseded/`. `docs/DHI_alignment.md` keeps its voice: it is a signed, dated working note.

## Structure, 15 Sep 2026

The tabs answer four questions in order: where is the contact (4.1.1), what controls it
(4.1.2, 3.1), how the chance changes with depth (4.1.3), what that means for the assessment
minimum and the well (4.1.4); run checks close the tab (4.1.5). Tab 5.1 answers seven: evidence
present, evidence strength (updates P(G)), contact attribution (updates HCWC | G), the HCWC
distribution, POS, effective sample size, assumptions; diagnostics are folded after them. A first model needs tab 2
sections 1–2 and tab 3 defaults; everything else has a default. Every probability shown says
whether it is conditional on G, whether it includes the element risk, and the threshold it is
read at. Assumptions are stated in the open (5.1.6), each labelled elicited, heuristic or
modelling choice; expanders hold diagnostics and derivations, never assumptions.

## Standing constraints

- `_private/` and `reference/private/` are gitignored and stay untracked. The app never mentions
  the workbook.
- Imported datasets are never written to disk or sent over the network.
- Captions are not folded into expanders.
- Files are moved, not deleted.
