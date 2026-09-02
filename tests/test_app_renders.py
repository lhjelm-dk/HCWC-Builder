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


@pytest.mark.parametrize("anomaly", ["Seen", "Seen over the crest only",
                                     "Absent where one was expected"])
def test_every_dhi_observation_type_renders(anomaly):
    """Partial conformance — bright over the crest, reliably absent below — is the third case, and
    the walkthrough on sub-tab ⑤.1 reads the observation too. It called `pick_pdf` on an
    observation that has no pick and took the page down."""
    _no_exception(_run(dhi_in_seen=anomaly), f"DHI observation {anomaly!r}")


def test_a_cutoff_above_the_apex_is_refused_in_place():
    at = _run(dhi_in_seen="Seen over the crest only", dhi_in_absent_below=1900.0)
    _no_exception(at, "a cutoff above the apex")
    assert any("absent below" in e.value for e in at.error), "nothing explained the refusal"


def test_the_partial_conformance_bound_survives_a_reload():
    import json

    from hcwc.io import prospect

    at = _run(dhi_in_seen="Seen over the crest only", dhi_in_absent_below=2200.0)
    _no_exception(at, "partial conformance")
    saved = prospect.document(at.session_state.filtered_state)
    assert saved["inputs"]["dhi_in_absent_below"] == 2200.0
    reloaded = _run(**prospect.read(json.dumps(saved)))
    assert (reloaded.session_state["dhi_overlay"]["posterior_pos"]
            == at.session_state["dhi_overlay"]["posterior_pos"])


def _well(**extra):
    base = dict(well_toggle=True, well_in_water_on=True, well_in_water=2250.0)
    return _run(**(base | extra))


def test_well_control_renders_and_moves_the_contact():
    """A penetration is the sharpest evidence about a contact, and it reweights the realisations
    rather than adding a limit — so the controlling-limit bookkeeping has to survive it."""
    import numpy as np

    plain = _run()
    withwell = _well()
    _no_exception(withwell, "well control")
    before = np.asarray(plain.session_state["dhi_overlay"]["contact_samples"], float)
    after = np.asarray(withwell.session_state["dhi_overlay"]["contact_samples"], float)
    assert np.percentile(after, 90) < np.percentile(before, 90), \
        "water at 2,250 m should pull the deep tail up"
    assert len(withwell.session_state["limit_set"].limits) == len(plain.session_state["limit_set"].limits)


def test_a_bracketing_penetration_is_the_sharpest_evidence_the_tool_takes():
    import numpy as np

    def spread(at):
        c = np.asarray(at.session_state["dhi_overlay"]["contact_samples"], float)
        return float(np.percentile(c, 90) - np.percentile(c, 10))

    bracket = _well(well_in_hc_on=True, well_in_hc=2230.0)
    _no_exception(bracket, "a bracketing penetration")
    assert spread(bracket) < spread(_well())
    assert spread(bracket) < spread(_run())


def test_evidence_that_disagrees_widens_the_answer():
    """Not a defect, and the first version of the test above assumed otherwise.

    The example prospect's DHI picks the contact *at* 2,250 m; a water leg at 2,250 m says the
    contact is *above* it. Two sources pulling opposite ways should leave the reader less certain,
    not more, and the combination widens accordingly. Agreement is what narrows.
    """
    import numpy as np

    def spread(at):
        c = np.asarray(at.session_state["dhi_overlay"]["contact_samples"], float)
        return float(np.percentile(c, 90) - np.percentile(c, 10))

    dhi_only = spread(_run())
    assert spread(_well(well_in_water=2250.0)) > dhi_only, "a well contradicting the pick"
    assert spread(_well(well_in_hc_on=True, well_in_hc=2245.0,
                        well_in_water_on=False)) < dhi_only, "a well agreeing with the pick"


def test_hydrocarbons_below_the_water_leg_is_refused_where_it_is_typed():
    at = _well(well_in_hc_on=True, well_in_hc=2300.0, well_in_water=2250.0)
    _no_exception(at, "a contradictory penetration")
    assert any("must be above the water" in e.value for e in at.error)


def test_a_penetration_the_model_finds_impossible_says_so():
    """Same saturation as partial conformance: a flat penalty and no evidence look identical, and
    only the warning tells them apart."""
    at = _well(well_in_water=2100.0)
    _no_exception(at, "a contradicting penetration")
    assert any("disagree almost completely" in w.value for w in at.warning)


def test_well_control_survives_a_reload():
    import json

    from hcwc.io import prospect

    at = _well(well_in_water=2210.0, well_in_connected=0.8)
    saved = prospect.document(at.session_state.filtered_state)
    assert saved["inputs"]["well_in_water"] == 2210.0
    reloaded = _run(**prospect.read(json.dumps(saved)))
    assert (reloaded.session_state["dhi_overlay"]["posterior_pos"]
            == at.session_state["dhi_overlay"]["posterior_pos"])


@pytest.mark.parametrize("tab", [4, 5])
def test_the_reservoir_decline_opens_on_the_deepest_part_of_the_closure(tab):
    """It used to open at the P25 and P95 contact, which put the start of the decline in the middle
    of the answer — switching it on immediately penalised three-quarters of the realisations."""
    at = _run(**{f"r1_on_{tab}": True})
    _no_exception(at, f"the reservoir decline on tab {tab}")
    got = {w.key: w.value for w in at.number_input
           if w.key in (f"r1_full_{tab}", f"r1_none_{tab}")}
    assert got[f"r1_none_{tab}"] == 2400.0, "should default to the spill point from tab ②"
    assert got[f"r1_full_{tab}"] == 2350.0, "and start one decline interval above it"


def test_the_decline_default_follows_the_spill_point():
    """Anchored on a property of the closure the assessor stated, not on an output of the run —
    so it does not move when the limits move."""
    at = _run(spill_input=2600.0, r1_on_4=True)
    got = {w.key: w.value for w in at.number_input if w.key in ("r1_full_4", "r1_none_4")}
    assert (got["r1_full_4"], got["r1_none_4"]) == (2550.0, 2600.0)
