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


# ---------------------------------------------------------------------------------------------
# Regressions from the hostile QA pass. Each of these took the whole page down, or silently
# changed the answer, from an input the app itself offers.
# ---------------------------------------------------------------------------------------------

def _run(**state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP), default_timeout=900)
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def _no_exception(at, what):
    assert not at.exception, f"{what}: " + "\n".join(str(e.value) for e in at.exception)


@pytest.mark.parametrize("minimum", [300.0, 350.0, 1000.0, 2000.0])
def test_an_unreachable_assessment_minimum_is_answered_not_raised(minimum):
    """A minimum above every achievable column is a real question with a real answer: *no*.

    It used to be an ``IndexError`` out of ``np.percentile`` on an empty array, from two separate
    sites — the benchmark calibration on tab ⑥ and the fusion table on tab ⑧. 2000 is the widget's
    own maximum, so every one of these is a value the slider offers.
    """
    _no_exception(_run(min_column_input=minimum), f"assessment minimum {minimum:g} m")


@pytest.mark.parametrize("key", ["lim_Charge_kind", "lim_Fault leakage 1_kind"])
def test_a_column_limit_restated_as_a_depth_reports_instead_of_crashing(key):
    """One selectbox. Charge is elicited in metres of column, so *Stated as → m TVDSS* makes
    100/220/400 depths hundreds of metres above the apex — and the engine raises, correctly. The
    message it raises is written for a reader; it just has to be shown rather than thrown."""
    at = _run(**{key: "depth"})
    _no_exception(at, f"{key} switched to m TVDSS")
    assert any("cannot be sampled" in e.value for e in at.error), \
        "the limit set is unsamplable and nothing said so"


@pytest.mark.parametrize("mode", ["Exceedance curves", "Violin", "Half violin",
                                  "Histogram", "Points"])
@pytest.mark.parametrize("tab", [4, 5])
def test_every_stack_mode_draws(mode, tab):
    """Five options in a visible dropdown, on two tabs. *Half violin* was a hard crash in all of
    them: the lane's left edge was a bare float where the polygon needed an array."""
    _no_exception(_run(**{f"stack_mode_{tab}": mode}), f"stack mode {mode!r} on tab {tab}")


def test_the_dhi_observation_survives_a_save_and_reload():
    """The critical one. Every DHI widget was unkeyed, so a saved prospect carried `dhi_toggle`
    and nothing else: it reopened claiming a DHI and quietly used the default one, 21 points of
    POS away from the assessment that was saved."""
    import json

    from hcwc.io import prospect

    at = _run(dhi_in_strength=25.0, dhi_in_contact=2205.0, dhi_in_sigma=30.0)
    _no_exception(at, "a DHI at strength 25")
    saved = prospect.document(at.session_state.filtered_state)
    assert saved["inputs"]["dhi_in_strength"] == 25.0, "the DHI strength was not saved"

    reloaded = _run(**prospect.read(json.dumps(saved)))
    _no_exception(reloaded, "the reloaded prospect")
    assert (reloaded.session_state["dhi_overlay"]["posterior_pos"]
            == at.session_state["dhi_overlay"]["posterior_pos"]), \
        "the reloaded prospect gives a different posterior POS than the one that was saved"


def test_realisations_reaches_the_dhi_posterior():
    """The geological run honoured the trial count and the posterior did not — it was resampled at
    a hard-coded 20 000, so at 1 000 it was better resolved than its own prior, and at 100 000 it
    ignored the precision asked for. Tab ⑦ exports this sample."""
    import numpy as np

    for trials in (1_000, 25_000):
        at = _run(n_trials_input=trials)
        _no_exception(at, f"{trials} realisations")
        drawn = np.asarray(at.session_state["dhi_overlay"]["contact_samples"], dtype=float)
        assert drawn.size == trials, f"asked for {trials}, the posterior drew {drawn.size}"
