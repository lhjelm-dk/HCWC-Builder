"""The app actually renders, top to bottom, with no exception on any tab.

**This file exists because the suite had a hole exactly the shape of a refactor.** Every other test
imports modules or calls functions; none of them rendered a page. So a name that moved between
modules and was never imported back — `CLOSURE_FAMILY`, during the split of `empirical.py` — passed
573 green tests and would have been a `NameError` on tab ⑥ in the browser.

`AppTest` runs the real script against a real session, so anything that raises inside a tab body
surfaces here. It costs about fifteen seconds, which is the cheapest fifteen seconds in the suite:
a Streamlit exception is a red page, and a red page is the failure mode a user reports rather than
one CI reports.

Two runs, not one. Several things on tab ⑤ deliberately read state written by a sibling sub-tab, so
the first render is a cold start and the second is the steady state the user actually sees.
"""
from __future__ import annotations

import pathlib

import pytest

APP = pathlib.Path(__file__).resolve().parent.parent / "app.py"


@pytest.fixture(scope="module")
def rendered():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP), default_timeout=900).run()
    at.run()
    return at


def test_no_tab_raises(rendered):
    assert not rendered.exception, "\n".join(str(e.value) for e in rendered.exception)


def test_the_engine_actually_ran(rendered):
    """A page that renders without running the model would pass the check above and be empty."""
    assert rendered.session_state["limit_set"] is not None
    assert rendered.session_state["_figures"], "no figure was registered on any tab"


def test_every_tab_registered_its_figures(rendered):
    """One number per tab that draws, so a tab silently dropping its content is visible here."""
    labels = rendered.session_state["_figures"]
    tabs = {label.split()[-1].split(".")[0] for label in labels}
    assert {"3", "4", "5", "6"} <= tabs, f"tabs missing from the figure registry: {sorted(tabs)}"


def test_figure_numbers_are_unique(rendered):
    """The invariant sub-tab numbering exists to protect: two `Figure 4.1`s collide as element keys."""
    labels = list(rendered.session_state["_figures"])
    assert len(labels) == len(set(labels))


def test_the_dhi_update_reaches_the_tabs_that_read_it(rendered):
    """Tab ⑤'s sub-tabs pass state between them; a broken hand-off is silent otherwise."""
    for key in ("dhi_posterior", "dhi_overlay", "dhi_r_strength"):
        assert key in rendered.session_state, f"{key} never reached session state"
