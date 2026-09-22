"""The app actually renders, top to bottom, with no exception on any tab.

**This file exists because the suite had a hole exactly the shape of a refactor.** Every other test
imports modules or calls functions; none of them rendered a page. So a name that moved between
modules and was never imported back — `CLOSURE_FAMILY`, during the split of `empirical.py` — passed
573 green tests and would have been a `NameError` on tab 6.0 in the browser.

`AppTest` runs the real script against a real session, so anything that raises inside a tab body
surfaces here. It costs about fifteen seconds, which is the cheapest fifteen seconds in the suite:
a Streamlit exception is a red page, and a red page is the failure mode a user reports rather than
one CI reports.

Two runs, not one. Several things on tab 5.0 deliberately read state written by a sibling sub-tab, so
the first render is a cold start and the second is the steady state the user actually sees.
"""
from __future__ import annotations

import functools
import pathlib

import pytest

#: Every test here renders the app, so the whole module carries the marker CI keys on.
pytestmark = pytest.mark.render

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
    """Tab 5.0's sub-tabs pass state between them; a broken hand-off is silent otherwise."""
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
    sites — the benchmark calibration on tab 6.0 and the fusion table on tab 8.0. 2000 is the widget's
    own maximum, so every one of these is a value the slider offers.
    """
    _no_exception(_run(min_column_input=minimum), f"assessment minimum {minimum:g} m")


@pytest.mark.parametrize("key", ["lim_Fault leakage 1_kind", "lim_Top seal (continuity)_kind"])
def test_a_column_limit_restated_as_a_depth_reports_instead_of_crashing(key):
    """One selectbox. These limits are elicited in metres of column, so *Stated as → m TVDSS*
    makes a capacity of a hundred-odd metres into a depth hundreds of metres above the apex — and
    the engine raises, correctly. The message it raises is written for a reader; it just has to be
    shown rather than thrown.

    Charge used to be the first case here and is not any more: it opens on its own calculator now,
    so its *Stated as* control no longer decides what the limit set contains.
    """
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
    ignored the precision asked for. Tab 7.0 exports this sample."""
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
    the walkthrough on sub-tab 5.0.1 reads the observation too. It called `pick_pdf` on an
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


@functools.lru_cache(maxsize=1)
def _contact_quantiles() -> tuple[float, ...]:
    """P90/P50/P10 of the shipped prospect's contact, for tests that need a depth *in* the answer.

    Cached because it costs a full render. Derived rather than typed because typed depths have now
    been stranded three times by changes to the defaults — the charge and seal fluids moved the
    contact 76 m, and the DHI pick default moved it again. A test that hard-codes 2,250 m is
    really asserting where the default prospect happens to sit, which is not what any of these
    tests are about.
    """
    import numpy as np

    contacts = np.asarray(_run().session_state["dhi_overlay"]["contact_samples"], float)
    return tuple(float(np.percentile(contacts, p)) for p in (10.0, 50.0, 90.0))


def _well(water_at=None, **extra):
    """A prospect with a water leg, placed at the contact median unless told otherwise."""
    _, p50, _ = _contact_quantiles()
    base = dict(well_toggle=True, well_in_water_on=True,
                well_in_water=p50 if water_at is None else water_at)
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

    # Hydrocarbons proven 40 m above the water, from a well taken as connected: a real bracket.
    # With the proven depth at the contact's own P90 the bracket excluded almost nothing, and at
    # the shipped connection chance of 0.6 the floor of 0.4 under the likelihood dominates both
    # cases, so the two spreads differed by a fraction of a metre and the comparison was decided
    # by the resample's noise -- which the weaker shipped pick of 15 Sep 2026 (c = 0.36) tipped
    # the wrong way. The proposition is about the bracket, so the floor is lowered to show it.
    _, p50, _ = _contact_quantiles()
    bracket = _well(well_in_hc_on=True, well_in_hc=p50 - 40.0, well_in_connected=0.95)
    _no_exception(bracket, "a bracketing penetration")
    assert spread(bracket) < 0.9 * spread(_well(well_in_connected=0.95))
    assert spread(bracket) < 0.9 * spread(_run())


def test_hydrocarbons_below_the_water_leg_is_refused_where_it_is_typed():
    _, p50, _ = _contact_quantiles()
    at = _well(water_at=p50, well_in_hc_on=True, well_in_hc=p50 + 50.0)
    _no_exception(at, "a contradictory penetration")
    assert any("must be above the water" in e.value for e in at.error)


def test_a_penetration_the_model_finds_impossible_says_so():
    """Same saturation as partial conformance: a flat penalty and no evidence look identical, and
    only the warning tells them apart."""
    p90, _, _ = _contact_quantiles()
    at = _well(water_at=p90 - 120.0)
    _no_exception(at, "a contradicting penetration")
    assert any("disagree almost completely" in w.value for w in at.warning)


def test_well_control_survives_a_reload():
    import json

    from hcwc.io import prospect

    _, p50, _ = _contact_quantiles()
    at = _well(water_at=p50, well_in_connected=0.8)
    saved = prospect.document(at.session_state.filtered_state)
    assert saved["inputs"]["well_in_water"] == pytest.approx(p50)
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
    assert got[f"r1_none_{tab}"] == 2400.0, "should default to the spill point from tab 2.0"
    assert got[f"r1_full_{tab}"] == 2350.0, "and start one decline interval above it"


def test_the_decline_default_follows_the_spill_point():
    """Anchored on a property of the closure the assessor stated, not on an output of the run —
    so it does not move when the limits move."""
    at = _run(spill_input=2600.0, r1_on_4=True)
    got = {w.key: w.value for w in at.number_input if w.key in ("r1_full_4", "r1_none_4")}
    assert (got["r1_full_4"], got["r1_none_4"]) == (2550.0, 2600.0)


#: The top-seal capillary block opens *Typed* since 8 Sep 2026, so anything that reads the
#: seal calculator -- or reads it through the base seal's *Same as the top seal* shortcut --
#: has to switch the source on first. Named once so the next default change moves one line.
TOP_SEAL_COMPUTED = {"lim_Top seal (capillary)_src": "seal"}


@pytest.mark.parametrize("thickness", [0.0, 50.0, 120.0])
def test_the_base_seal_sits_a_reservoir_thickness_below_the_top_seal(thickness):
    """Same shale, same capacity — different place.

    Every capacity here is measured downward from the structural apex, which is the crest of the
    *top* reservoir. The base seal's crest is one reservoir thickness below that, so borrowing the
    top seal's inputs without the offset would enter it as though it sat at the crest, which is the
    one place it certainly does not.
    """
    import numpy as np

    from hcwc.ui import run as engine_run

    key = "lim_Base seal (capillary)"
    at = _run(**TOP_SEAL_COMPUTED,
              **{f"{key}_src": "seal_as_top", f"{key}_pa": 1.0,
                 f"{key}_thickness": thickness})
    _no_exception(at, f"the base seal at {thickness:g} m thickness")
    limits = at.session_state["limit_set"]
    result = engine_run.current(limits)
    where = {name: i for i, name in enumerate(limits.names)}
    top = float(np.median(result.sampled_m[:, where["Top seal (capillary)"]]))
    base = float(np.median(result.sampled_m[:, where["Base seal (capillary)"]]))
    # Sampled independently, so the medians agree only to within Monte Carlo noise.
    assert abs((base - top) - thickness) < 8.0


def test_the_reservoir_thickness_defaults_to_fifty_metres():
    key = "lim_Base seal (capillary)"
    at = _run(**TOP_SEAL_COMPUTED, **{f"{key}_src": "seal_as_top", f"{key}_pa": 1.0})
    got = [w.value for w in at.number_input if w.key == f"{key}_thickness"]
    assert got == [50.0]


@pytest.mark.parametrize("source", ["seal", "seal_as_top"])
def test_both_routes_to_the_base_seal_put_it_in_the_same_place(source):
    """*Same as the top seal* and *From seal capacity* are two entry points to one limit. If only
    one carried the reservoir-thickness offset they would disagree about where that limit sits."""
    import numpy as np

    from hcwc.ui import run as engine_run

    key = "lim_Base seal (capillary)"
    at = _run(**TOP_SEAL_COMPUTED,
              **{f"{key}_src": source, f"{key}_pa": 1.0, f"{key}_thickness": 50.0})
    _no_exception(at, f"the base seal via {source}")
    limits = at.session_state["limit_set"]
    result = engine_run.current(limits)
    where = {name: i for i, name in enumerate(limits.names)}
    top = float(np.median(result.sampled_m[:, where["Top seal (capillary)"]]))
    base = float(np.median(result.sampled_m[:, where["Base seal (capillary)"]]))
    assert abs((base - top) - 50.0) < 8.0


def test_the_top_seal_is_the_datum_and_is_not_offset():
    """It defines the surface everything else is measured from, so asking it for a thickness would
    be asking how far it sits below itself."""
    at = _run()
    assert not [w for w in at.number_input if w.key == "lim_Top seal (capillary)_thickness"]


def test_changing_the_dhi_strength_updates_tab_four_in_the_same_interaction():
    """The trust panel on tab 4.0 reports the effective sample size behind the DHI update, and that
    posterior is built on tab 5.0 — which renders *after* tab 4.0. Reading it there showed the previous
    frame: 28 % where the answer was 10 %, then 10 % where it was 24 %, with nothing saying so.

    The panel is now written into a container tab 4.0 reserves and app.py fills after tab 5.0. This
    asserts the fix the only way that means anything: a second rerun with nothing touched must not
    change a single rendered line.
    """
    import re

    from streamlit.testing.v1 import AppTest

    def page(at):
        return [re.sub(r"\s+", " ", m.value) for m in at.markdown]

    at = AppTest.from_file(str(APP), default_timeout=900)
    at.run()
    for strength in (50.0, 12.0):
        at.session_state["dhi_in_strength"] = strength
        at.run()
        once = page(at)
        at.run()
        assert once == page(at), f"tab 4.0 was stale after changing the DHI strength to {strength}"


def test_a_neutral_dhi_strength_does_not_move_the_headline_chance():
    """End to end, on the shipped prospect: strength 0 is a likelihood ratio of exactly 1, and an
    observation that says nothing must leave the answer where it found it."""
    at = _run(dhi_in_strength=0.0)
    _no_exception(at, "a neutral DHI strength")
    overlay = at.session_state["dhi_overlay"]
    assert overlay["posterior_pos"] == pytest.approx(overlay["prior_pos"], abs=1e-9)


class TestTheAreaDepthTableIsAnInput:
    """It used to be read off a CSV on every render and shown only as a chart — the single most
    consequential input to the charge calculation, invisible as numbers and impossible to change."""

    @staticmethod
    def _frame(depths, top, base=None):
        import pandas as pd
        return pd.DataFrame({"Depth (m TVDSS)": depths, "Top area (km²)": top,
                             "Base area (km²)": base if base is not None else [0.0] * len(depths)})

    def test_the_grid_opens_on_the_shipped_example(self):
        from hcwc.ui import sources

        at = _run()
        _no_exception(at, "the area-depth panel")
        rows = at.session_state[sources.AREA_DEPTH_ROWS]
        assert len(rows) == 37
        assert list(rows.columns) == ["Depth (m TVDSS)", "Top area (km²)", "Base area (km²)"]

    def test_a_thickness_reproduces_the_mapped_base_on_the_shipped_prospect(self):
        """The best available check that the derivation is right: the shipped example's base
        surface *is* its top shifted down 50 m, so the two methods must agree exactly."""
        from hcwc.ui import sources

        surfaces = _run()
        derived = _run(**{sources.AREA_DEPTH_METHOD: sources.THICKNESS,
                          sources.AREA_DEPTH_THICKNESS: 50.0})
        _no_exception(derived, "the thickness method")
        grv = lambda at: [m.value for m in at.metric if "Gross rock volume" in m.label]
        assert grv(surfaces) == grv(derived) != []

    def test_editing_the_grid_changes_the_answer(self):
        from hcwc.ui import sources

        at = _run()
        doubled = at.session_state[sources.AREA_DEPTH_ROWS].copy()
        doubled["Top area (km²)"] = doubled["Top area (km²)"] * 2.0
        edited = _run(**{sources.AREA_DEPTH_ROWS: doubled})
        _no_exception(edited, "an edited table")
        grv = lambda at: [m.value for m in at.metric if "Gross rock volume" in m.label]
        assert grv(edited) != grv(at)

    @pytest.mark.parametrize("depths,top,base,why", [
        ([2000.0, 2100.0, 2100.0], [0.0, 5.0, 6.0], None, "depths must increase"),
        ([2000.0, 2100.0], [1.0, 2.0], [0.0, 9.0], "base area exceeds top area"),
        ([2000.0], [1.0], None, "at least two depths"),
    ])
    def test_a_table_that_cannot_be_integrated_says_why(self, depths, top, base, why):
        from hcwc.ui import sources

        at = _run(**{sources.AREA_DEPTH_ROWS: self._frame(depths, top, base)})
        _no_exception(at, "an unusable table")
        assert any(why in e.value for e in at.error), f"nothing said {why!r}"

    def test_rows_out_of_order_are_sorted_rather_than_refused(self):
        """Mapping software exports either direction and neither is wrong."""
        from hcwc.ui import sources

        at = _run(**{sources.AREA_DEPTH_ROWS:
                     self._frame([2200.0, 2100.0, 2000.0], [9.0, 5.0, 0.0])})
        _no_exception(at, "a descending table")
        assert not [e for e in at.error if "cannot be integrated" in e.value]

    def test_it_travels_with_the_prospect_only_when_the_calculator_is_used(self):
        """Lars's rule: a prospect whose Charge limit is typed has no use for 37 rows of somebody
        else's structure, and carrying them would invite the reader to think they meant something."""
        import json

        from hcwc.io import prospect

        used = prospect.document(_run(**{"lim_Charge_src": "charge"}).session_state.filtered_state)
        typed = prospect.document(_run(**{"lim_Charge_src": "Typed"}).session_state.filtered_state)
        assert [k for k in used["inputs"] if k.startswith("charge_ad_")]
        assert not [k for k in typed["inputs"] if k.startswith("charge_ad_")]
        assert len(used["inputs"]["charge_ad_depth_m"]) == 37
        assert prospect.read(json.dumps(used))["charge_ad_depth_m"][0] == 2040.0

    def test_an_edited_table_survives_save_and_reload(self):
        import json

        from hcwc.io import prospect
        from hcwc.ui import sources

        at = _run()
        doubled = at.session_state[sources.AREA_DEPTH_ROWS].copy()
        doubled["Top area (km²)"] = doubled["Top area (km²)"] * 2.0
        edited = _run(**{sources.AREA_DEPTH_ROWS: doubled})
        saved = prospect.document(edited.session_state.filtered_state)
        reloaded = _run(**prospect.read(json.dumps(saved)))
        _no_exception(reloaded, "the reloaded table")
        grv = lambda at: [m.value for m in at.metric if "Gross rock volume" in m.label]
        assert grv(reloaded) == grv(edited)


class TestTheSealDensitiesAreInSitu:
    """Lars asked what the HC density means — gas or oil, reservoir or standard conditions.

    The formula settles it: `h = P_c / (Δρ·g)` with `Δρ` taken straight from the two sliders and no
    conversion anywhere, so both are **in situ at reservoir conditions**. The interfacial tension is
    already a function of the sampled reservoir temperature, which is the same answer from the other
    direction. That is now said on the slider, and paired with a check that the fluid and the
    density agree — the shipped default used to be gas tension against an oil density contrast.
    """

    KEY = "lim_Top seal (capillary)"

    def test_the_help_says_which_conditions(self):
        at = _run(**TOP_SEAL_COMPUTED)
        rho = [w for w in at.slider if w.key == f"{self.KEY}_rh"]
        assert rho, "the HC density slider is missing"
        assert "reservoir pressure and temperature" in (rho[0].help or "")
        assert "stock-tank" in (rho[0].help or "")

    @pytest.mark.parametrize("fluid,rho,should_warn", [
        ("Oil", (0.70, 0.85), False),
        ("Gas", (0.15, 0.35), False),
        ("Gas", (0.70, 0.85), True),
        ("Oil", (0.15, 0.35), True),
    ])
    def test_a_fluid_and_a_density_that_disagree_are_flagged(self, fluid, rho, should_warn):
        at = _run(**TOP_SEAL_COMPUTED,
                  **{f"{self.KEY}_fluid": fluid, f"{self.KEY}_rh": rho})
        _no_exception(at, f"{fluid} at {rho}")
        fired = any("density against" in w.value for w in at.warning)
        assert fired is should_warn

    def test_the_shipped_capacity_matches_the_elicited_ranges(self):
        """Pins the calculator's own defaults: 162 / 302 / 880 m. The block no longer opens
        on it -- the capillary limit is typed at PERT(100, 250, 500) since 8 Sep -- but the
        calculator is still what the *Computed* source runs.

        Until 15 Sep 2026 these were 79 / 148 / 433 m, from an oil-water tension line that gave
        11.7 dyne/cm at 70 C; the elicited 18-28 dyne/cm that replaced it (archive/development_notes/IFT_CHECK_2026-09-15.md)
        roughly doubles the capacity, which is the finding.
        """
        at = _run(**TOP_SEAL_COMPUTED)
        got = [m.value for m in at.metric if m.label.endswith("capacity")]
        assert got == ["162 m", "302 m", "880 m"], got


class TestTheBenchmarkFiguresCanShowWhatTheToolProduced:
    """Lars asked whether the *empirical prior* violin is what the statistics predict for this
    prospect — it is — and whether the built distributions could sit beside it. They can now."""

    @staticmethod
    def _violins(at):
        import base64
        import json

        import numpy as np

        def decode(v):
            if isinstance(v, dict) and "bdata" in v:
                return np.frombuffer(base64.b64decode(v["bdata"]),
                                     dtype=np.dtype(v.get("dtype", "f8")))
            return np.asarray(v, dtype=float)

        out = {}
        for el in at.get("plotly_chart"):
            for trace in json.loads(el.proto.spec).get("data", []):
                name = str(trace.get("name"))
                if trace.get("type") == "violin" and "this prospect" in name:
                    out.setdefault(name, decode(trace.get("y")))
        return out

    def test_the_comparison_is_drawn_on_arrival(self):
        """Lars, 4 Sep 2026, turning this on by default. The empirical prior alone is a statement
        about the NCS record; the comparison is the reason anyone is on this tab, and a toggle
        defaulting off made the more interesting figure the one you had to know to ask for."""
        names = set(self._violins(_run()))
        assert "this prospect — empirical prior" in names
        assert any("geological" in name for name in names), names

    def test_the_toggle_still_takes_the_comparison_away(self):
        """A default is not a fixture. Turned off, the tab is the record on its own again."""
        names = set(self._violins(_run(empirical_show_models=False)))
        assert names == {"this prospect — empirical prior"}

    def test_the_toggle_adds_the_geological_and_dhi_distributions(self):
        at = _run(empirical_show_models=True)
        _no_exception(at, "the model overlay")
        names = set(self._violins(at))
        assert "this prospect — geological (tab 4.0)" in names
        assert "this prospect — given the DHI (tab 5.0)" in names

    def test_all_three_are_column_height_in_metres_and_comparable(self):
        """The point of putting them on one axis. If any were a *depth* rather than a column the
        medians would differ by an apex, which is two thousand metres rather than a hundred."""
        import numpy as np

        violins = self._violins(_run(empirical_show_models=True))
        medians = {k: float(np.median(v)) for k, v in violins.items()}
        assert len(medians) == 3
        assert all(0.0 < m < 1000.0 for m in medians.values()), medians

    def test_the_empirical_prior_cannot_exceed_the_closure(self):
        """It is seal capacity capped by `min(S, H)` — the same spill cap the geology applies —
        which is what makes it a prior for *this* prospect rather than the raw population."""
        import numpy as np

        prior = self._violins(_run())["this prospect — empirical prior"]
        assert np.max(prior) <= 350.0 + 1e-6


class TestTheLimitStackSaysWhichContactItIsDrawing:
    """Lars, 3 Sep 2026, of Figure 5.3.6: *"is the resulting hc the geological or | dhi?"*

    It was the geological one, on a tab whose banner says everything below it carries the amplitude
    evidence \u2014 and the dashed line that claimed to be the DHI was the **weight vector itself**.
    `posterior` is one weight per realisation; it was handed straight to a trace's `x` against 260
    depths, and plotly zips to the shorter of the two, so the curve was the first 260 raw weights
    read as probabilities: values between 0.1\u202f% and 2\u202f% drawn on a 0\u2013100\u202f% axis. In the four
    density modes the posterior never arrived at all.
    """

    @staticmethod
    def _traces(at):
        import base64
        import json

        import numpy as np

        def decode(v):
            if isinstance(v, dict) and "bdata" in v:
                return np.frombuffer(base64.b64decode(v["bdata"]),
                                     dtype=np.dtype(v.get("dtype", "f8")))
            return np.asarray(v)

        for el in at.get("plotly_chart"):
            traces = {str(t.get("name")): t for t in json.loads(el.proto.spec).get("data", [])}
            if any(k.startswith("Resulting HC depth") for k in traces):
                yield {k: {a: decode(t[a]) for a in ("x", "y") if a in t}
                       for k, t in traces.items()}

    def test_no_trace_anywhere_pairs_two_axes_of_different_lengths(self):
        """The bug class, caught across the whole page rather than at the one place it happened.
        Plotly draws a mismatched pair silently, truncated to the shorter, which is how a weight
        vector passed for a curve produced a plausible-looking line instead of an error."""
        bad = []
        for chart in self._traces(_run()):
            for name, axes in chart.items():
                if "x" in axes and "y" in axes and axes["x"].size != axes["y"].size:
                    bad.append(f"{name}: x={axes['x'].size} y={axes['y'].size}")
        assert not bad, f"traces with mismatched axes: {bad}"

    def test_the_dhi_tab_draws_both_contacts_and_names_each(self):
        charts = [c for c in self._traces(_run())
                  if any("given the DHI" in k for k in c)]
        assert charts, "tab 5.0's limit stack shows no DHI-updated contact at all"
        for chart in charts:
            assert "Resulting HC depth | geological" in chart
            assert "Resulting HC depth | given the DHI" in chart

    def test_the_geological_tab_draws_one_contact_and_does_not_call_it_a_basis(self):
        """Tab 4.0 has nothing to compare against, so the bare name is right there."""
        plain = [c for c in self._traces(_run()) if "Resulting HC depth" in c]
        assert plain, "tab 4.0's limit stack has no contact curve"

    def test_the_two_curves_are_different_distributions(self):
        """If they coincided the figure would be decoration. The amplitude concentrates rather
        than shifts, so the medians stay close and the separation shows up mid-curve."""
        import numpy as np

        for chart in self._traces(_run(**{"stack_mode_5": "Exceedance curves"})):
            if "Resulting HC depth | given the DHI" not in chart:
                continue
            if chart["Resulting HC depth | given the DHI"]["x"].size != 260:
                continue
            geological = chart["Resulting HC depth | geological"]["x"]
            updated = chart["Resulting HC depth | given the DHI"]["x"]
            assert np.abs(geological - updated).max() > 0.02, \
                "the DHI curve is indistinguishable from the geological one"
            return
        raise AssertionError("no exceedance-mode limit stack was drawn on tab 5.0")

    def test_the_answer_is_the_lower_envelope_of_the_limits_it_is_drawn_with(self):
        """The caption's promise, and the reason every thin curve is reweighted too. The identity
        holds under any *one* weighting; mixing geological limits with a DHI answer would let the
        bold line cross above a thin one, which the caption then reads as impossible."""

        checked = 0
        for chart in self._traces(_run(**{"stack_mode_4": "Exceedance curves",
                                          "stack_mode_5": "Exceedance curves"})):
            bold = [k for k in chart if k.startswith("Resulting HC depth")]
            answer = chart[bold[-1]]["x"]
            if answer.size != 260:
                continue
            for name, axes in chart.items():
                if name.startswith("Resulting HC depth") or axes["x"].size != 260:
                    continue
                assert (axes["x"] >= answer - 1e-9).all(), \
                    f"{name} runs shallower than the contact it is supposed to bound"
                checked += 1
        assert checked, "no limit curves were checked"

    @pytest.mark.parametrize("mode", ["Exceedance curves", "Violin", "Half violin",
                                      "Histogram", "Points"])
    def test_every_mode_carries_the_posterior(self, mode):
        """Four of the five silently drew the geological sample: `_density_mode` was never given
        the weights. *Points* shows it by importance resampling, the other three exactly."""
        at = _run(**{"stack_mode_5": mode})
        _no_exception(at, f"stack mode {mode!r} on tab 5.0")
        assert any("Resulting HC depth | given the DHI" in c for c in self._traces(at)), \
            f"{mode} on tab 5.0 shows no DHI-updated contact"


class TestTheLimitStackGroupsWhatItDraws:
    """Lars, 3 Sep 2026: *"could we see the limit distributions and then the dhi distribution (not a
    limit) and then the one or two resulting distributions, maybe with just a bit of visual
    separation"*.

    Three groups, in that order, with a gap and a dotted rule between them and a heading over each.
    The middle one is the point of the exercise: the amplitude is **not** a competing mechanism, so
    it does not belong among them, and it is not a sample either, so it is not drawn like one.
    """

    LANE_MODES = ["Violin", "Half violin", "Histogram", "Points"]

    @staticmethod
    def _stack(at):
        """The lane-mode limit stack on tab 5.0, as (lane name -> lane centre) plus its layout.

        Read off the **x-axis ticks**, not off the traces. A bar's ``x`` is its length from ``base``
        and a half violin's left edge *is* the lane centre, so deriving a position from the trace
        geometry means a different rule per mode -- and the ticks are what the reader is actually
        matching a lane to.
        """
        import json

        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            names = [str(t.get("name")) for t in spec.get("data", [])]
            if not any(n.startswith("Resulting HC depth |") for n in names):
                continue
            axis = spec.get("layout", {}).get("xaxis", {})
            ticks = axis.get("tickvals") or []
            labels = axis.get("ticktext") or []
            if not ticks:
                continue
            return {str(k): float(v) for k, v in zip(labels, ticks)}, spec.get("layout", {})
        return None, None

    @pytest.mark.parametrize("mode", LANE_MODES)
    def test_the_amplitude_gets_its_own_lane_between_the_limits_and_the_answer(self, mode):
        at = _run(**{"stack_mode_5": mode})
        _no_exception(at, f"grouped lanes in {mode!r}")
        centres, _ = self._stack(at)
        assert centres is not None, f"{mode} drew no lane-mode stack on tab 5.0"
        assert "The evidence, on its own" in centres, "the amplitude has no lane of its own"

        evidence = centres["The evidence, on its own"]
        limits = [x for name, x in centres.items()
                  if not name.startswith("Resulting HC depth") and name != "The evidence, on its own"]
        results = [x for name, x in centres.items() if name.startswith("Resulting HC depth")]
        assert limits and results
        assert max(limits) < evidence < min(results), \
            "the three groups are not in the order limits / amplitude / result"

    @pytest.mark.parametrize("mode", LANE_MODES)
    def test_the_groups_are_separated_by_a_gap_and_a_rule(self, mode):
        """A gap alone reads as an accident and a rule alone is easy to miss, so both. The rule has
        to land *in* the gap -- between the two lanes it separates, not on top of one of them."""
        centres, layout = self._stack(_run(**{"stack_mode_5": mode}))
        rules = sorted(float(s["x0"]) for s in layout.get("shapes", [])
                       if s.get("yref") == "paper" and s.get("type") == "line")
        assert len(rules) == 2, f"expected two group rules, found {len(rules)}"

        ordered = sorted(centres.values())
        for rule in rules:
            below = [x for x in ordered if x < rule]
            above = [x for x in ordered if x > rule]
            assert below and above, "a group rule sits outside the lanes"
            gap = min(above) - max(below)
            assert gap > 1.5, f"the group boundary at {rule:.2f} has no visible gap ({gap:.2f})"

    @pytest.mark.parametrize("mode", LANE_MODES)
    def test_each_group_carries_a_heading(self, mode):
        _, layout = self._stack(_run(**{"stack_mode_5": mode}))
        headings = {str(a.get("text")) for a in layout.get("annotations", [])
                    if a.get("yref") == "paper"}
        from hcwc.plotting.app import limit_stack
        assert {limit_stack.LIMITS_GROUP, limit_stack.EVIDENCE_GROUP,
                limit_stack.RESULT_GROUP} <= headings, f"headings found: {headings}"

    def test_the_geological_tab_has_no_amplitude_group(self):
        """Nothing to show there, and a group heading over an empty gap would be worse than none."""
        at = _run(**{"stack_mode_4": "Violin"})
        import json

        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            names = [str(t.get("name")) for t in spec.get("data", [])]
            if "Resulting HC depth" in names and not any("given the DHI" in n for n in names):
                assert "The evidence, on its own" not in names
                rules = [s for s in spec.get("layout", {}).get("shapes", [])
                         if s.get("yref") == "paper" and s.get("type") == "line"]
                assert len(rules) == 1, "tab 4.0 should have one group boundary, not two"
                return
        raise AssertionError("tab 4.0 drew no lane-mode stack")

    def test_the_amplitude_lane_is_a_shape_not_a_frequency(self):
        """It is a likelihood ratio, peak-normalised. Nothing about it should be readable as a
        count: it is the only lane drawn as a dotted outline, and that is deliberate."""
        import base64
        import json

        import numpy as np

        at = _run(**{"stack_mode_5": "Violin"})
        for el in at.get("plotly_chart"):
            for trace in json.loads(el.proto.spec).get("data", []):
                if str(trace.get("name")) != "The evidence, on its own":
                    continue
                assert trace.get("line", {}).get("dash") == "dot", \
                    "the amplitude lane is drawn like a sample"
                x = np.frombuffer(base64.b64decode(trace["x"]["bdata"]),
                                  dtype=np.dtype(trace["x"].get("dtype", "f8")))
                # Peak-normalised into a lane of width LANE_FILL, so it spans at most that.
                from hcwc.plotting.app import limit_stack
                assert (x.max() - x.min()) <= limit_stack.LANE_FILL + 1e-6
                return
        raise AssertionError("the amplitude lane was not drawn")

    def test_the_amplitude_lane_prefers_the_depth_that_was_picked(self):
        """The sanity check that says the lane is the evidence and not something else: its peak
        should sit near the picked contact, because that is what the likelihood is about."""
        import base64
        import json

        import numpy as np

        pick = 2_150.0
        at = _run(**{"stack_mode_5": "Violin", "dhi_in_contact": pick})
        _no_exception(at, "the amplitude lane at a moved pick")
        for el in at.get("plotly_chart"):
            for trace in json.loads(el.proto.spec).get("data", []):
                if str(trace.get("name")) != "The evidence, on its own":
                    continue

                def dec(v):
                    return np.frombuffer(base64.b64decode(v["bdata"]),
                                         dtype=np.dtype(v.get("dtype", "f8")))

                x, y = dec(trace["x"]), dec(trace["y"])
                # The polygon is right edge then reversed left edge; the widest point is the peak.
                centre = float((x.min() + x.max()) / 2)
                peak_at = float(y[np.argmax(np.abs(x - centre))])
                assert abs(peak_at - pick) < 150.0, \
                    f"the amplitude lane peaks at {peak_at:,.0f} m for a pick at {pick:,.0f} m"
                return
        raise AssertionError("the amplitude lane was not drawn")


class TestTheDhiOpensOnTheProspectsPick:
    """Lars, 3 Sep 2026: *"default picked dhi: set Picked contact to 2250 m"*.

    It was a fixed 2 250 m, then the model's median after that default turned out to open at the
    **P94** of the geological contact. The number is back because it is the prospect's actual pick;
    the guard that made the old version wrong is not.
    """

    def test_the_pick_opens_at_two_two_five_zero(self):
        assert _run().session_state["dhi_in_contact"] == pytest.approx(2_250.0)

    def test_it_is_inside_the_prior_it_is_updating(self):
        """The whole failure mode of a hard-coded default. Outside the central 98 % of the prior the
        update rests on a handful of realisations, and the fallback exists for that case."""

        at = _run()
        contacts = _contact_quantiles()
        assert min(contacts) <= 2_250.0 <= max(contacts), \
            f"2 250 m is outside the contact range {min(contacts):,.0f}-{max(contacts):,.0f} m"
        assert not at.exception

    def test_moving_the_pick_moves_the_contact_and_the_effective_sample_size(self):
        """Both directions matter: a pick further from the prior median buys a sharper answer from
        fewer realisations, and the tab has to report that trade rather than hide it."""
        seen = {}
        for pick in (2_185.0, 2_250.0):
            at = _run(**{"dhi_in_contact": pick})
            _no_exception(at, f"a pick at {pick:,.0f} m")
            seen[pick] = {str(m.label): m.value for m in at.get("metric")}["Contact P50"]
        assert seen[2_185.0] != seen[2_250.0], "the picked contact does not move the answer"


class TestTheLimitStackHonoursItsControls:
    """Two things Lars caught on 3 Sep 2026 looking at the rendered figure."""

    @staticmethod
    def _traces(at, name_startswith):
        import base64
        import json

        import numpy as np

        def decode(v):
            if isinstance(v, dict) and "bdata" in v:
                return np.frombuffer(base64.b64decode(v["bdata"]),
                                     dtype=np.dtype(v.get("dtype", "f8")))
            return np.asarray(v, dtype=float)

        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            names = [str(t.get("name")) for t in spec.get("data", [])]
            if not any(n.startswith("Resulting HC depth |") for n in names):
                continue
            for trace in spec["data"]:
                if str(trace.get("name")).startswith(name_startswith):
                    yield trace, decode(trace.get("y")), spec.get("layout", {})

    def test_points_stays_inside_the_depth_window(self):
        """*"the selected depth range is not honored when plotting points"*. Two causes, and the
        second is the one that would have come back: the points were not clipped, **and**
        `update_yaxes(autorange="reversed", range=[hi, lo])` let autorange win, so the axis stretched
        to fit them. The other four modes clip their own data, which is why they looked correct."""
        at = _run(**{"stack_mode_5": "Points"})
        _no_exception(at, "points mode")
        seen = 0
        for trace, y, layout in self._traces(at, "Resulting HC depth"):
            top, bottom = layout["yaxis"]["range"]
            assert y.min() >= min(top, bottom) - 1e-6, "a point sits above the window"
            assert y.max() <= max(top, bottom) + 1e-6, "a point sits below the window"
            seen += 1
        assert seen, "points mode drew no contact lane"

    def test_the_axis_is_pinned_rather_than_auto_ranged(self):
        """The root cause, asserted directly: with `autorange` set, `range` is advisory."""
        for mode in ("Violin", "Points", "Histogram"):
            for _, _, layout in self._traces(_run(**{"stack_mode_5": mode}),
                                             "Resulting HC depth"):
                axis = layout["yaxis"]
                assert axis.get("autorange") is False, f"{mode}: the depth axis still auto-ranges"
                assert axis.get("range"), f"{mode}: the depth axis has no explicit range"
                break

    @pytest.mark.parametrize("mode,kind", [("Violin", "scatter"), ("Half violin", "scatter"),
                                           ("Histogram", "bar"), ("Points", "scatter")])
    def test_the_amplitude_lane_follows_the_chosen_mode(self, mode, kind):
        """*"the amp alone is a violin even if you select half-violin or histogram or points"*. It
        looked like the control had failed on one lane. The geometry follows the mode now and the
        distinction is carried by style -- hollow shape, hollow bars, open markers."""
        at = _run(**{"stack_mode_5": mode})
        _no_exception(at, f"the amplitude lane in {mode!r}")
        found = [t for t, _, _ in self._traces(at, "The evidence, on its own")]
        assert found, f"{mode} drew no amplitude lane"
        for trace in found:
            assert trace.get("type") == kind, \
                f"{mode}: the amplitude lane is a {trace.get('type')}, not a {kind}"
            if mode == "Points":
                assert trace["marker"].get("symbol") == "circle-open", \
                    "the amplitude's markers are drawn from a likelihood and must not look observed"
            elif mode == "Histogram":
                assert trace["marker"].get("line", {}).get("color"), "the bars are not outlined"
            else:
                assert trace["line"].get("dash") == "dot"

    def test_half_violin_draws_the_amplitude_on_one_side_only(self):
        """The mode's whole point, and the lane was ignoring it."""
        import base64

        import numpy as np

        for trace, _, _ in self._traces(_run(**{"stack_mode_5": "Half violin"}),
                                        "The evidence, on its own"):
            x = np.frombuffer(base64.b64decode(trace["x"]["bdata"]),
                              dtype=np.dtype(trace["x"].get("dtype", "f8")))
            # A half violin's flat edge is the lane centre, so half the outline is a constant.
            flat = np.isclose(x, x.min())
            assert flat.sum() >= x.size // 2 - 1, "the amplitude lane is not drawn as a half"
            return
        raise AssertionError("no amplitude lane in half violin mode")

    def test_violin_is_the_opening_view_on_both_tabs(self):
        """Lars's call. A default that differed between 4.0 and 5.0 would make flipping between
        them a hunt rather than a comparison."""
        at = _run()
        for tab in (4, 5):
            assert at.session_state[f"stack_mode_{tab}"] == "Violin"


class TestTheAllocationTableSaysWhichBasisItIs:
    """Lars, 4 Sep 2026, of tables 4.2.3 and 5.4.3: *"I want a clear statement on whether this are
    geological or given dhi ... and maybe for the 5.4.3 I want a geological AND |dhi allocation"*.

    The two tables were drawn identically and neither said which it was — while 5.4.3 was silently
    the DHI-updated one. They differ through `r` alone, and by a lot: derived Retention moves 0.449
    to 0.597 on the shipped prospect.
    """

    @staticmethod
    def _allocation_tables(at):
        out = []
        for el in at.get("dataframe"):
            frame = el.value
            columns = list(getattr(frame, "columns", []))
            if "Prospect POS" in columns:
                out.append(frame)
        return out

    def test_the_geological_tab_shows_one_pair_of_columns(self):
        frames = self._allocation_tables(_run())
        assert frames, "no allocation table was drawn"
        geological = frames[0]
        assert "Derived at the well" in geological.columns
        assert not any("given the DHI" in c for c in geological.columns), \
            "tab 4.0 is showing a DHI column"

    def test_the_dhi_tab_shows_both_bases(self):
        frames = self._allocation_tables(_run())
        assert len(frames) >= 2, "tab 5.0 drew no allocation table of its own"
        updated = frames[-1]
        for column in ("Derived · geological", "Allocated · geological",
                       "Derived · given the DHI", "Allocated · given the DHI"):
            assert column in updated.columns, f"{column} missing from table 5.4.3"

    def test_the_two_bases_actually_differ(self):
        """If they matched, the extra columns would be clutter. They differ through the location
        factor `r`, which is read off the contact distribution — the one thing the amplitude
        moves — while the element chances above it are untouched."""
        updated = self._allocation_tables(_run())[-1]
        pairs = [(g, d) for g, d in zip(updated["Derived · geological"],
                                        updated["Derived · given the DHI"]) if g != "—"]
        assert pairs, "no derived values to compare"
        assert any(g != d for g, d in pairs), \
            "the geological and DHI allocations are identical, so one of them is not being used"

    def test_the_element_chances_are_the_same_in_both_halves(self):
        """The claim the caption makes, asserted. A fluid indicator moves the total and may not
        re-attribute it between elements, so `Prospect POS` is one column, not two."""
        updated = self._allocation_tables(_run())[-1]
        assert sum(c == "Prospect POS" for c in updated.columns) == 1

    @pytest.mark.parametrize("tab,expected", [(4, "GEOLOGICAL"), (5, "GIVEN THE DHI")])
    def test_each_table_carries_its_basis_chip(self, tab, expected):
        """The statement Lars asked for, in the caption where the number is read."""
        at = _run()
        captions = [str(c.value) for c in at.get("caption")]
        assert any(expected in c and "Prospect POS" not in c for c in captions), \
            f"no {expected} chip found on the allocation captions"


# ---------------------------------------------------------------------------------------------
# Grant (2020) eq. 8, offset well control, and the basis vocabulary that had to follow them.
# ---------------------------------------------------------------------------------------------

WELL_ONLY = dict(dhi_toggle=False, well_toggle=True, well_in_water_on=True, well_in_water=2_260.0)
WELL_AND_DHI = dict(well_toggle=True, well_in_water_on=True, well_in_water=2_260.0)


class TestTheMechanicalTopSealIsAvailableAsALimit:
    """Grant (2020) eq. 8, added 4 Sep 2026 after reviewing the paper the tool's method comes from.

    Every other Retention limit fails because the pore throats are wide enough or because there is a
    hole in the seal. This one fails because the rock parts in tension, and the two are independent.
    """

    KEY = "lim_Top seal (fracture)"

    def test_it_is_in_the_limit_set_and_off_by_default(self):
        """In the list but never biting, like every other mechanism most prospects do not have.
        Off means visible and auditable rather than silently absent."""
        limits = {lim.name: lim for lim in _run().session_state["limit_set"].limits}
        assert "Top seal (fracture)" in limits
        assert limits["Top seal (fracture)"].p_active == pytest.approx(0.0)

    def test_it_does_not_move_the_shipped_answer(self):
        """A thirteenth limit that changed the reference prospect's POS would mean it was biting,
        which at hydrostatic pressure it must not."""
        metrics = {str(m.label): m.value for m in _run().get("metric")}
        assert metrics["P(column ≥ 5 m | G)"] in ("99.9%", "100.0%")

    def test_the_calculator_renders_and_produces_a_column(self):
        at = _run(**{f"{self.KEY}_src": "fracture"})
        _no_exception(at, "the fracture-pressure calculator")
        limits = {lim.name: lim for lim in at.session_state["limit_set"].limits}
        assert "headroom" in limits["Top seal (fracture)"].note

    def test_a_normally_pressured_trap_is_told_it_cannot_fracture(self):
        """The finding, not a defect: hundreds of bar of headroom is thousands of metres of column,
        so the mechanism is correct and irrelevant — and a reader not told that will wonder why it
        never appears in the controlling-limit statistics."""
        at = _run(**{f"{self.KEY}_src": "fracture"})
        assert any("far from its fracture limit" in str(i.value) for i in at.get("info"))

    def test_overpressure_is_what_makes_it_bite(self):
        """Twenty bar of headroom instead of a hundred, and the column falls by an order of
        magnitude. The physics, asserted end to end through the UI."""
        import numpy as np

        def column(at):
            for lim in at.session_state["limit_set"].limits:
                if lim.name == "Top seal (fracture)":
                    return float(np.median(
                        lim.distribution.ppf(np.random.default_rng(1).random(4_000))))
            raise AssertionError("the fracture limit is missing")

        normal = column(_run(**{f"{self.KEY}_src": "fracture"}))
        tight = column(_run(**{f"{self.KEY}_src": "fracture",
                               f"{self.KEY}_pp": (300.0, 315.0),
                               f"{self.KEY}_shmin": (320.0, 335.0)}))
        assert tight < normal / 3.0, f"overpressure barely moved it: {normal:,.0f} -> {tight:,.0f} m"

    def test_the_source_survives_a_save_and_reload(self):
        """`fracture` had to be added to the saved-file enumeration. Streamlit does not complain
        about a stored value outside a selector's options — it silently takes the first one, so the
        prospect would reload as *Typed* and look fine."""
        import json

        from hcwc.io import prospect

        at = _run(**{f"{self.KEY}_src": "fracture"})
        saved = prospect.document(at.session_state.filtered_state)
        assert saved["inputs"][f"{self.KEY}_src"] == "fracture"
        assert prospect.read(json.dumps(saved))[f"{self.KEY}_src"] == "fracture"


class TestOffsetWellControlIsReachableWithoutADhi:
    """Lars, 4 Sep 2026, challenging what well control is *for*: at appraisal a contact is proven,
    so the model is decoration. He is right about the appraisal well and it is the wrong case —
    the channel is for the *offset* well, whose commonest result is a bracket rather than a pick.

    It was unreachable for exactly that case. The inputs live on tab 2.0 but the evidence was only
    ever used inside tab 5.0, which renders nothing unless the prospect is marked as a DHI prospect.
    """

    def test_a_well_with_no_dhi_now_produces_an_update(self):
        at = _run(**WELL_ONLY)
        _no_exception(at, "a well-only prospect")
        assert at.session_state["dhi_posterior"] is not None
        assert at.session_state["dhi_overlay"] is not None

    def test_the_update_actually_moves_the_contact(self):
        at = _run(**WELL_ONLY)
        post = at.session_state["dhi_posterior"]
        import numpy as np
        geological = float(np.percentile(post.result.contact_m, 50))
        updated = float(post.percentiles(50)[0])
        assert abs(updated - geological) > 1.0, "the penetration changed nothing"

    def test_the_overlay_carries_every_key_its_readers_use(self):
        """A partial overlay does not degrade gracefully — it raises `KeyError` in the middle of
        somebody else's figure, which is how this first failed."""
        overlay = _run(**WELL_ONLY).session_state["dhi_overlay"]
        for key in ("depths_m", "pos_curve", "prior_curve", "contact_samples", "weights",
                    "picked_contact_m", "prior_pos", "posterior_pos", "h_min"):
            assert key in overlay, f"{key} missing from a well-only overlay"

    def test_there_is_no_likelihood_ratio_without_an_amplitude(self):
        """`r_dhi` is E-POS's `r_dfi`: the seismic likelihood over tall columns against short ones.
        A number computed from a well's weights under that name would be the wrong quantity wearing
        the right label."""
        import numpy as np
        assert np.isnan(_run(**WELL_ONLY).session_state["dhi_posterior"].r_dhi)

    def test_the_tornado_falls_back_to_the_geological_one(self):
        """It perturbs the amplitude's own inputs — the pick, its σ, the detection function — and
        raised on `observation.pick_sigma_m` being `None`."""
        at = _run(**WELL_ONLY)
        _no_exception(at, "the tornado on a well-only prospect")
        assert any("This tornado is geological" in str(c.value) for c in at.get("caption"))

    def test_the_defaults_are_an_offset_wells_and_not_an_appraisals(self):
        """The tell Lars's challenge exposed: σ = 5–10 m and p_connected = 0.9 are same-well,
        same-log numbers, for the case he correctly said needs no model."""
        at = _run(well_toggle=True)
        assert at.session_state["well_in_sigma"] >= 20.0
        assert at.session_state["well_in_connected"] <= 0.75


class TestTheBasisIsNamedForTheEvidenceInIt:
    """Once a penetration alone can update a prospect, a banner reading GIVEN THE DHI on it is
    false — and the basis label is the one thing in this app that must never be."""

    @staticmethod
    def _phrases(at):
        """The basis **labels** on the page — the banners and chips, not prose about them.

        Case-sensitive on the upper-case form on purpose. `basis_tag` and `basis_banner` are the
        only things that emit `GIVEN THE DHI`, and they are the authoritative labels this test
        exists to protect. A lower-case scan swept up any sentence that *discusses* the basis —
        which broke the moment the article on tab 8.0 grew a section explaining what "given the
        DHI" means. Series names and headings carry the lower-case form and are covered by
        `TestEveryResultExhibitDeclaresItsBasis`, which reads captions specifically rather than
        every string on the page.
        """
        import json

        texts = [str(m.value) for m in
                 list(at.get("markdown")) + list(at.get("caption")) + list(at.get("subheader"))]
        for el in at.get("plotly_chart"):
            for trace in json.loads(el.proto.spec).get("data", []):
                if trace.get("name"):
                    texts.append(str(trace["name"]))
        found = set()
        for text in texts:
            for phrase in ("GIVEN THE DHI + WELL", "GIVEN THE WELL", "GIVEN THE DHI"):
                if phrase in text:
                    found.add(phrase.lower())
                    break
        return found

    def test_a_well_only_prospect_is_never_told_it_has_a_dhi(self):
        assert "given the dhi" not in self._phrases(_run(**WELL_ONLY))

    def test_a_dhi_only_prospect_is_never_told_it_has_a_well(self):
        found = self._phrases(_run())
        assert found == {"given the dhi"}, found

    def test_both_channels_are_named_when_both_are_present(self):
        found = self._phrases(_run(**WELL_AND_DHI))
        assert "given the dhi + well" in found
        assert "given the dhi" not in found, "a stale DHI-only label survived"

    def test_a_prospect_with_no_evidence_claims_none(self):
        assert not self._phrases(_run(dhi_toggle=False))

    def test_the_title_form_keeps_the_acronym(self):
        """`str.capitalize` would give *Given the dhi*, beside a chip reading *GIVEN THE DHI*."""
        from hcwc.ui import theme
        assert theme.evidence_title().startswith("Given the ")
        assert "dhi" not in theme.evidence_title() or "DHI" in theme.evidence_title()


class TestTheCalibrationComparesBothBases:
    """Lars, 4 Sep 2026: *"in section 6.8 I want the |dhi represented as well. it looks like it is
    only the geological that is being compared to stats. I want both."*

    It was. Every exhibit in sections 8 and 9 read `engine_run.current(...)` — the geological run —
    so the whole calibration exercise checked the half of the tool that had not heard the evidence.
    Which exhibit shows both at once and which asks you to pick is decided by the medium: a table
    can carry a `Basis` column, and four benchmarks against two bases on one Q-Q plot cannot.
    """

    @staticmethod
    def _frames(at, *required):
        out = []
        for el in at.get("dataframe"):
            columns = list(getattr(el.value, "columns", []))
            if all(any(name in c for c in columns) for name in required):
                out.append(el.value)
        return out

    @staticmethod
    def _named_traces(at, needle):
        import json
        for el in at.get("plotly_chart"):
            names = [str(t.get("name")) for t in json.loads(el.proto.spec).get("data", [])
                     if t.get("name")]
            if any(needle in name for name in names):
                return names
        return []

    def test_the_benchmark_table_carries_a_row_per_basis(self):
        frames = self._frames(_run(), "Benchmark", "Basis")
        assert frames, "table 6.10 has no Basis column"
        bases = set(frames[0]["Basis"])
        assert bases == {"geological", "given the DHI"}, bases

    def test_the_two_bases_land_on_different_percentiles(self):
        """If they agreed, the extra rows would be clutter. The amplitude moves the model toward
        the record here, which is the finding the comparison exists to surface."""
        frame = self._frames(_run(), "Benchmark", "Basis")[0]
        by_basis = {b: p for b, p in zip(frame["Basis"], frame["This P50 is their"])}
        assert by_basis["geological"] != by_basis["given the DHI"]

    def test_the_quantile_figures_take_one_basis_and_the_control_switches_them(self):
        """Eight curves on a figure whose whole reading is which side of one diagonal is not a
        comparison, it is a mess. So a selector — and flipping it is the comparison."""
        geological = self._named_traces(_run(), "in band")
        updated = self._named_traces(_run(calibration_basis="given the DHI"), "in band")
        assert geological and updated
        assert geological != updated, "the basis selector changes nothing"

    def test_the_quantile_captions_name_the_basis_they_are_drawn_on(self):
        at = _run(calibration_basis="given the DHI")
        _no_exception(at, "the calibration figures on the updated basis")
        captions = [str(c.value) for c in at.get("caption")]
        assert any("Matched quantiles" in c and "GIVEN THE DHI" in c for c in captions)

    def test_the_fusion_gives_every_basis_its_own_combined_curve(self):
        """*"in 6.12 is the combined just the geological?"* It was. The fusion is a weighted
        quantile average, so it applies to either basis unchanged — drawing it for only one made
        the figure read as though the evidence had been folded in when it had not."""
        names = self._named_traces(_run(fuse_benchmark=0.4), "this model")
        assert any("this model, geological" == n for n in names)
        assert any("this model, given the DHI" == n for n in names)
        assert any(n.startswith("geological, blended with the benchmark") for n in names)
        assert any(n.startswith("given the DHI, blended with the benchmark") for n in names)

    def test_the_fusion_draws_no_combined_curve_at_zero_weight(self):
        """At weight zero the combination *is* your model, and a second identical curve under a
        different name would invite reading it as a result."""
        names = self._named_traces(_run(fuse_benchmark=0.0), "this model")
        assert not any("blended with the benchmark" in n for n in names)

    def test_the_base_rate_gets_a_bar_for_each_basis(self):
        """*"in 6.13 maybe a bar for the |dhi?"*"""
        names = self._named_traces(_run(), "base rate")
        assert "this model · geological" in names
        assert "this model · given the DHI" in names

    def test_the_base_rate_table_carries_both(self):
        frames = self._frames(_run(), "Trap fill", "given the DHI")
        assert frames, "table 6.14 has no updated column"
        assert "This model · given the DHI" in frames[0].columns

    def test_a_prospect_with_no_evidence_shows_only_the_geological_one(self):
        """The whole apparatus collapses to what it was when there is nothing to compare against,
        rather than drawing an empty second series."""
        at = _run(dhi_toggle=False)
        _no_exception(at, "calibration with no evidence")
        assert set(self._frames(at, "Benchmark", "Basis")[0]["Basis"]) == {"geological"}
        assert self._named_traces(at, "base rate") == ["this model · geological",
                                                       "NCS base rate (n = 23)"]

    def test_the_updated_columns_are_resampled_rather_than_apex_subtracted(self):
        """The overlay carries *contacts*; subtracting a median apex from those is off by however
        much the apex varies, which is the quantity tab 4.0 spends a section on.
        `dhi.posterior_columns` resamples `column_m` directly, so no apex arithmetic happens.

        Driven off the app's own posterior rather than through `empirical.dhi_columns`, which reads
        session state and so returns `None` when called from outside a script run."""
        import numpy as np

        from hcwc.core import dhi as dhi_core

        posterior = _run().session_state["dhi_posterior"]
        columns = dhi_core.posterior_columns(posterior, 5_000)
        assert columns.size == 5_000
        allowed = posterior.result.column_m[posterior.result.above_minimum]
        assert np.isin(columns, allowed).all(), "a resampled column is not one the engine drew"
        # And it is a *posterior* sample, not the prior over again.
        assert abs(float(np.median(columns))
                   - float(np.median(allowed))) > 1.0, "the weights did nothing"


class TestEveryResultExhibitDeclaresItsBasis:
    """Lars, 4 Sep 2026: *"check is geological and |dhi represented! ok?"* On tabs 4.0 and 5.0 it
    was not: 3 of 32 exhibits carried a basis chip, and nineteen of the rest were **byte-identical
    captions across the two tabs** — `Figure 4.1.1` and `Figure 5.2.1` (then 5.3.1) were the same words over two
    different distributions.

    The tab-level banner said which, and its own docstring says why that was the fix: *"a reader who
    has scrolled to Figure 7.2 will not scroll back to check."* But **a caption travels and a banner
    does not.** The export on tab 7.0 ships every figure with its caption and no banner, and so does
    the camera button on any chart. So the basis lives on the sequence now, and every exhibit it
    numbers inherits it.
    """

    @staticmethod
    def _captions(at):
        import re

        out = {}
        for element in at.get("caption"):
            match = re.match(r"\*\*((?:Figure|Table) [\d.a-z]+)\*\*", str(element.value))
            if match:
                out[match.group(1)] = str(element.value)
        return out

    @staticmethod
    def _sequence(label):
        """`Figure 5.2.2f` -> `5.2` — the sub-tab sequence it belongs to."""
        parts = label.split()[-1].split(".")
        return ".".join(parts[:2])

    @pytest.mark.parametrize("sequence,expected", [("4.1", "GEOLOGICAL"), ("4.2", "GEOLOGICAL"),
                                                   ("5.2", "GIVEN THE DHI"),
                                                   ("5.3", "GIVEN THE DHI")])
    def test_every_exhibit_on_a_result_sub_tab_carries_its_chip(self, sequence, expected):
        captions = self._captions(_run())
        mine = {k: v for k, v in captions.items() if self._sequence(k) == sequence}
        assert mine, f"no exhibits found on {sequence}"
        missing = sorted(k for k, v in mine.items() if expected not in v)
        assert not missing, f"{sequence} exhibits with no {expected} chip: {missing}"

    def test_the_paired_captions_are_no_longer_identical(self):
        """The precise defect: same words, two distributions, nothing to tell them apart."""
        captions = self._captions(_run())
        # Renumbered 15 Sep 2026 when 4.1 gained the chance curve (3) and the well (4); on
        # 17 Sep the competition figure replaced the exceedance figure as 4.1.1.
        for a, b in (("Figure 4.1.1a", "Figure 5.2.1a"), ("Figure 4.1.2c", "Figure 5.2.2c"),
                     ("Table 4.1.2d", "Table 5.2.2d"), ("Figure 4.2.2a", "Figure 5.3.2a")):
            assert captions[a] != captions[b], f"{a} and {b} still read identically"

    def test_the_chip_follows_the_evidence_on_a_well_only_prospect(self):
        """The sequence is handed the token; the chip renders whatever the weights actually hold."""
        captions = self._captions(_run(**WELL_ONLY))
        updated = [v for k, v in captions.items() if self._sequence(k) in ("5.2", "5.3")]
        assert updated
        assert all("GIVEN THE WELL" in v for v in updated)
        assert not any("GIVEN THE DHI" in v for v in updated)

    def test_the_exported_figure_carries_the_chip_too(self):
        """The reason this is on the caption rather than only on screen. The report renders from
        this registry, and a figure exported without its basis is the whole problem."""
        figures = _run().session_state["_figures"]
        for label, (_, caption) in figures.items():
            sequence = self._sequence(label)
            if sequence in ("4.1", "4.2"):
                assert "GEOLOGICAL" in caption, f"{label} exports with no basis"
            elif sequence in ("5.2", "5.3"):
                assert "GIVEN THE DHI" in caption, f"{label} exports with no basis"

    def test_a_sequence_with_no_basis_adds_no_chip(self):
        """Tab 3.0 and tab 6.0 are not readings of one contact distribution, and a chip there would
        be a claim rather than a label. `None` has to stay distinguishable from *not set*."""
        captions = self._captions(_run())
        for label, caption in captions.items():
            if label.split()[-1].startswith("3."):
                assert "GEOLOGICAL" not in caption and "GIVEN THE" not in caption, label


class TestSectionNumbersHaveNoGaps:
    """Tab 6.0 read `1, 2, 3.1, 3.2, 3.3, 6, 7, 8, 9, 10` for a week.

    On 28 Aug 2026 (`9368ce5`, *tab 6 folded*) sections 3, 4 and 5 were folded into one expander and
    renumbered 3.1-3.3, and the five sections after them were not renumbered down. Nothing sat at 4
    or 5, and a caption pointed at "§4" -- into the hole. The figure numbering had a test; the
    *section* numbering did not, which is why a gap survived two numbering audits.

    Separately, tab 4.0's trust panel drew its heading without the sub-tab it lives on, so it came
    out as `4.6` beside sections `4.1.1` to `4.1.5`: two schemes on one page, and the heading is
    what a reader navigates by.
    """

    @staticmethod
    def _sections(at):
        """{tab: [section numbers rendered]}, read off the headings themselves."""
        import collections
        import re

        found = collections.defaultdict(set)
        for element in at.get("markdown"):
            for match in re.finditer(r"<h3[^>]*>(\d+)\.(\d+(?:\.\d+)?)\s", str(element.value)):
                found[int(match.group(1))].add(match.group(2))
        return found

    def test_no_tab_skips_a_section_number(self):
        sections = self._sections(_run())
        assert sections, "no headings were found at all"
        for tab, numbers in sorted(sections.items()):
            # Sub-tabbed tabs number their sections `sub.section`, so the run has to be per prefix.
            groups = {}
            for number in numbers:
                parts = number.split(".")
                groups.setdefault(".".join(parts[:-1]), []).append(int(parts[-1]))
            for prefix, seen in groups.items():
                seen.sort()
                where = f"tab {tab}" + (f" sub-tab {prefix}" if prefix else "")
                assert seen == list(range(1, len(seen) + 1)), \
                    f"{where} sections are {seen}, which skips a number"

    def test_tab_six_runs_one_to_ten(self):
        """The specific regression, named, because the fix was to restore three numbers rather than
        to renumber the five after them -- which keeps every `§6`-`§10` reference correct."""
        assert sorted(int(s) for s in self._sections(_run())[6]) == list(range(1, 11))

    def test_the_trust_panel_is_numbered_inside_its_sub_tab(self):
        """It renders into a container reserved on sub-tab 4.1 and its figures are numbered 4.1.x,
        so its heading has to be too."""
        sections = self._sections(_run())[4]
        assert "1.5" in sections, f"the trust panel is not 4.1.5: {sorted(sections)}"
        assert "5" not in sections, "a bare `4.5` heading is still being drawn"

    def test_every_section_reference_in_prose_points_at_a_real_section(self):
        """`§4` on tab 6.0 pointed into the gap. Citations of other people's papers are excluded by
        requiring the reference to name a tab -- `Edmundson's §5.2` is not a claim about this app."""
        import re

        at = _run()
        sections = self._sections(at)
        blob = "\n".join(str(e.value) for kind in ("markdown", "caption", "info", "warning")
                          for e in at.get(kind))
        broken = []
        for tab, section in re.findall(r"[Tt]ab (\d)\.0[^.§]{0,20}§\s?(\d+(?:\.\d+){0,2})", blob):
            drawn = sections.get(int(tab), set())
            # A reference may repeat the tab number — `Tab 4.0 §4.1.3` is how the heading actually
            # prints — so both spellings count as pointing at the same section.
            if section not in drawn and section.removeprefix(f"{tab}.") not in drawn:
                broken.append(f"tab {tab}.0 §{section}")
        assert not broken, f"references to sections that do not exist: {sorted(set(broken))}"


class TestTheFullReportCarriesTheTables:
    """Lars, 4 Sep 2026: *"I want the tables."*

    The document called *the full report* shipped 33 figures and none of the 17 tables. Figures were
    registered as they were drawn; tables were not registered anywhere, which is why nothing
    noticed — the limits as entered, the group minima, the allocation comparison and the whole
    benchmark section were simply absent.
    """

    @staticmethod
    def _document(at, figure_limit=2):
        """The report, with only a couple of figures so kaleido does not take a minute."""
        from hcwc.io import report
        from hcwc.ui import numbering

        figures = at.session_state[numbering.FIGURES_KEY]
        tables = at.session_state[numbering.TABLES_KEY]
        keep = {k: figures[k] for k in sorted(figures)[:figure_limit]}
        html, missing = report.build_full(
            at.session_state["dhi_posterior"].result,
            report.Provenance(prospect="T", basis="geological", trials=10_000, seed=1,
                              source_file=""),
            keep, tables=tables)
        return html, missing, tables

    def test_the_tables_are_registered_as_they_are_drawn(self):
        from hcwc.ui import numbering

        tables = _run().session_state[numbering.TABLES_KEY]
        assert len(tables) > 10, f"only {len(tables)} tables registered"
        for label in ("Table 3.2a", "Table 4.1.2d", "Table 4.2.4a", "Table 6.8a"):
            assert label in tables, f"{label} was drawn but never registered"

    def test_every_registered_table_reaches_the_document(self):
        html, _, tables = self._document(_run())
        for label in tables:
            assert f"<b>{label}</b>" in html, f"{label} is registered but absent from the report"

    def test_exhibits_are_interleaved_in_number_order(self):
        """They share one counter per tab — that is the whole point of the scheme, so that `2.3`
        names exactly one thing. A document that ran every figure and then every table would put
        `Table 3.2` after `Figure 6.13` and lose the reading order the numbers carry."""
        import re

        from hcwc.ui.numbering import figure_order

        html, _, _ = self._document(_run(), figure_limit=6)
        order = re.findall(r"<b>((?:Figure|Table) [\d.]+)</b>", html)
        assert order == sorted(order, key=figure_order), order

    def test_a_hand_written_markdown_table_renders_as_a_table(self):
        """`markdown_table` stores its pipe-table source, not HTML, so the registry keeps what the
        app drew. The report turns it into rows."""
        html, _, _ = self._document(_run())
        assert "<table class='tbl'>" in html
        assert "Censoring-corrected (MLE)" in html

    def test_the_stored_caption_carries_the_basis(self):
        """Same reason as for figures: this dict is what the report renders from, and a table
        exported without its basis is the defect that started all of this."""
        from hcwc.ui import numbering

        tables = _run().session_state[numbering.TABLES_KEY]
        assert "GEOLOGICAL" in tables["Table 4.1.2d"][1]
        assert "GIVEN THE DHI" in tables["Table 5.2.2d"][1]

    def test_a_failed_figure_is_still_reported_and_the_tables_survive_it(self):
        """The missing-figure path had to keep working once the loop walked both kinds."""
        from hcwc.io import report
        from hcwc.ui import numbering

        at = _run()
        tables = at.session_state[numbering.TABLES_KEY]
        html, missing = report.build_full(
            at.session_state["dhi_posterior"].result,
            report.Provenance(prospect="T", basis="geological", trials=10_000, seed=1,
                              source_file=""),
            {"Figure 9.1": (object(), "a figure that cannot render")}, tables=tables)
        assert missing and "Figure 9.1" in missing[0]
        assert "<b>Table 3.2a</b>" in html


class TestThePageIsNotAnEssay:
    """Lars, 5 Sep 2026: *"I think there is too much text. could some of it be hidden, reduced or
    simplified."* Measured before touching anything: **16,573 words on arrival**, of which 6,462
    were figure and table captions and **10,111 were body prose you met without clicking**.

    The app was carrying a paper inside a tool. The argument — the censoring derivation, why-not-
    Bayes, the base-rate essay — is read once, or when someone challenges you, and it was sitting
    in front of the controls. Nine blocks went into expanders with a line of lead prose left
    outside, so the page still says what was folded rather than presenting a bare clickable label.

    **Captions were left visible on purpose.** On 28 Aug Lars removed a Full/Brief control because
    *"a caption that can be half-read is a caption whose second half nobody reads, and the second
    half is where the caveats are."* That still holds; the three longest were shortened instead.

    This test is a budget, not a rule about prose. It fails when the page grows back.
    """

    #: Measured 5 Sep 2026: 10,111 words before the fold, 7,802 after it, and 8,039 after the
    #: docs split put four folded essays back on the page as visible summaries. That last move is a
    #: deliberate trade -- a conclusion at the point of use beats a bare expander label -- and it is
    #: why the budget has room in it. Raising it is a decision, not a fix: if a block has to be
    #: added, something else folds or moves to `docs/`.
    BODY_BUDGET = 8_400

    #: No single block a reader cannot click past should run past this. The worst was 412.
    LONGEST_BLOCK = 250

    @staticmethod
    def _visible():
        """Words of on-arrival prose per module, from the source, skipping expander bodies.

        Read off the AST rather than the rendered page because `AppTest` renders expander contents
        like anything else — it cannot see that they are folded, which is the whole point of them.
        """
        import ast
        import collections
        import pathlib
        import re

        TEXT = {"markdown", "info", "warning", "write", "latex", "caption", "error", "success"}
        EXHIBIT = {"plot", "table", "markdown_table"}
        CAPTIONS = {"caption"} | EXHIBIT

        def words(s):
            return len(re.findall(r"\S+", re.sub(r"<[^>]+>", " ", s)))

        def literal(node):
            total = sum(words(x.value) for x in ast.walk(node)
                        if isinstance(x, ast.Constant) and isinstance(x.value, str))
            return total - sum(
                sum(words(x.value) for x in ast.walk(kw)
                    if isinstance(x, ast.Constant) and isinstance(x.value, str))
                for kw in getattr(node, "keywords", []) if kw.arg == "help")

        class Walk(ast.NodeVisitor):
            def __init__(self):
                self.depth = 0
                self.body = collections.Counter()
                self.blocks = []

            def visit_With(self, node):
                folded = any(
                    isinstance(i.context_expr, ast.Call)
                    and getattr(i.context_expr.func, "attr", None) == "expander"
                    for i in node.items)
                self.depth += folded
                self.generic_visit(node)
                self.depth -= folded

            def visit_Call(self, node):
                name = getattr(node.func, "attr", None)
                if name in TEXT | EXHIBIT and not self.depth:
                    n = literal(node)
                    if name not in CAPTIONS:
                        self.body[name] += n
                        self.blocks.append((n, name, node.lineno))
                self.generic_visit(node)

        root = pathlib.Path(__file__).resolve().parent.parent
        out, blocks = {}, []
        for path in [root / "app.py"] + sorted((root / "hcwc" / "ui").glob("*.py")):
            walk = Walk()
            walk.visit(ast.parse(path.read_text(encoding="utf-8")))
            out[path.name] = sum(walk.body.values())
            blocks += [(n, path.name, line) for n, _, line in walk.blocks]
        return out, blocks

    def test_the_body_prose_stays_within_budget(self):
        per_module, _ = self._visible()
        total = sum(per_module.values())
        worst = sorted(per_module.items(), key=lambda kv: -kv[1])[:4]
        assert total <= self.BODY_BUDGET, (
            f"{total:,} words of on-arrival body prose, budget {self.BODY_BUDGET:,}. "
            f"Heaviest: {worst}. Fold something into an expander rather than raising the budget.")

    def test_no_single_block_is_a_chapter(self):
        """A 400-word `st.info` is not a callout. The reader cannot click past it, so it has to
        earn every word or move behind a fold."""
        _, blocks = self._visible()
        over = sorted((b for b in blocks if b[0] > self.LONGEST_BLOCK), reverse=True)
        assert not over, (
            "blocks a reader cannot click past, longer than "
            f"{self.LONGEST_BLOCK} words: "
            + ", ".join(f"{name}:{line} ({n} words)" for n, name, line in over))

    def test_the_folded_blocks_still_render(self):
        """Folding is a display change and must not lose a word. `AppTest` renders expander
        contents, so anything that vanished would show up as a missing phrase."""
        at = _run()
        _no_exception(at, "the folded pages")
        blob = "\n".join(str(e.value) for kind in ("markdown", "caption", "info", "warning")
                          for e in at.get(kind))
        for phrase in (
            # Both were on tab 1 until 16 Sep 2026; they are stated once now, on tab 8.1.
            "Beha et al. (2012)",                       # 8.1.3, the precedent
            "a few mechanisms dominate the share",      # 8.1.3, the ranking
            "A prior and a likelihood are the same kind of object",   # tab 8.1.9, and its worked example
            # Graham's own words moved from tab 6.0 §7 to 8.1.10 on 16 Sep 2026.
            "in the absence of direct hydrocarbon indicators",
            "The censored MLE crossing is a prediction",  # tab 6.0 §2, folded
        ):
            assert phrase in blob, f"folding lost: {phrase!r}"

    def test_every_fold_says_what_is_inside_it(self):
        """A bare label is worse than the text: the reader cannot tell whether it matters. Every
        expander opened by this work names its own conclusion."""
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parent.parent
        bad = []
        for path in [root / "app.py"] + sorted((root / "hcwc" / "ui").glob("*.py")):
            for line, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = re.search(r"st\.expander\(\s*[\"'](.+?)[\"']", text)
                if match and len(match.group(1).split()) < 3:
                    bad.append(f"{path.name}:{line} {match.group(1)!r}")
        assert not bad, f"expander labels too short to judge: {bad}"


class TestTheArgumentsLiveInDocuments:
    """The docs split, 5 Sep 2026, moved three essays that were pure reasoning out of the tabs
    into `docs/`. On 15 Sep 2026 they and the other theory notes were folded into one document,
    `docs/THEORY.md`, rendered on tab 8 as 8.1 and 8.1.2 to 8.1.10, with the superseded notes kept
    under `archive/superseded_notes/`. The tabs state a conclusion and point at a number.

    **The viewer fails silently by design.** A missing file gets *"not found in this checkout"*
    rather than an exception, which is right for a deployment without the docs folder and wrong as
    the only check that a registered document exists.
    """

    #: One phrase per argument that used to be its own essay, now a paragraph of 8.1.x.
    DOCS = {
        "Prior or likelihood?": ("THEORY.md", "the same kind of object"),
        "Weight, not Bayes": ("THEORY.md", "conditions on the geometry twice"),
        "Base rates": ("THEORY.md", "is symmetric in its two inputs"),
    }

    def test_every_registered_document_exists(self):
        """Including the ones that were already there — the check costs nothing and the failure
        mode is a radio option that silently shows an apology."""
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parent.parent
        # tab 8 lives in hcwc/ui/theory.py since the clean-up of 18 Sep 2026
        source = (root / "hcwc" / "ui" / "theory.py").read_text(encoding="utf-8")
        named = set(re.findall(r'"([A-Z_]+\.md|[A-Za-z_]+\.md)"', source))
        assert named, "no documents are registered at all"
        missing = sorted(name for name in named
                         if not ((root / "docs" / name).exists() or (root / "paper" / name).exists()))
        assert not missing, f"registered but absent from docs/ or paper/: {missing}"

    #: Tab 8.0 was restructured on 7 Sep 2026 into Theory / The paper / References; on
    #: 15 Sep 2026 the theory became one document with nine numbered sub-sections, so a reader
    #: can be sent to "8.1.8" rather than to a radio option.
    #: Eight sections since 18 Sep 2026 (Lars): the overview figure and the map of the sections
    #: render under the 8.1 heading, then the sections follow the figure's boxes.
    #: The eleven sections of 21 Sep 2026 (the final review's brief U), in order.
    THEORY_ORDER = ("Model overview", "P(G): accumulation chance", "Competing limits and HCWC",
                    "Column height, HCWC and POS", "Correlation and dependence",
                    "DHI evidence index and the update of P(G)",
                    "DHI geometry and the update of HCWC | G",
                    "Combined DHI posterior and POS", "Empirical benchmarks and censoring",
                    "Validation, assumptions and limitations", "References")

    def test_the_moved_arguments_are_reachable_and_intact(self):
        at = _run()
        _no_exception(at, "tab 8")
        blob = "\n".join(str(m.value) for m in at.get("markdown"))
        assert "8.1 Theory and methods" in blob
        for k, title in enumerate(self.THEORY_ORDER, start=1):
            assert f"8.1.{k} · {title}" in blob, f"{title} is not sub-section 8.1.{k}"
        for label, (_, phrase) in self.DOCS.items():
            assert phrase in blob, f"{label} did not render its own text"
        assert "not found in this checkout" not in blob
        assert not [r for r in at.get("radio") if "Prior or likelihood?" in list(r.options)], (
            "the theory picker is back")

    def test_the_walkthrough_and_the_worked_example_sit_under_their_sections(self):
        """Two live pieces of the tool render inside the theory: the DHI walkthrough under
        8.1.8 and the base-rate worked example under 8.1.9. Order on the page is the check."""
        at = _run(dhi_toggle=True)
        blob = "\n".join(str(m.value) for m in at.get("markdown"))
        i5, i6 = blob.index("8.1.8 · Combined DHI posterior"), blob.index("8.1.9 · Empirical")
        assert i5 < blob.index("Step 1", i5) < i6, "the walkthrough is not under 8.1.8"
        i7, i8 = blob.index("8.1.9 · Empirical"), blob.index("8.1.10 · Validation")
        assert i7 < blob.index("counts the same belief twice", i7) < i8, (
            "the worked example is not under 8.1.9")

    def test_the_superseded_notes_are_kept_off_screen(self):
        """*Files are moved, not deleted.* The five notes 8.1 replaced stay readable in
        archive/superseded_notes/, indexed by a README, and none is registered on tab 8 any more."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        notes = ["COMPETING_LIMITS.md", "LIKELIHOOD_OR_PRIOR.md", "WEIGHT_NOT_BAYES.md",
                 "BASE_RATE_NEGLECT.md", "BENCHMARK_SOURCES.md"]
        missing = [n for n in notes if not (root / "archive" / "superseded_notes" / n).exists()]
        assert not missing, f"a superseded note was deleted rather than moved: {missing}"
        readme = (root / "archive" / "superseded_notes" / "README.md").read_text(encoding="utf-8")
        assert all(n in readme for n in notes), "archive/superseded_notes/README.md does not list every note"
        source = "\n".join((root / f).read_text(encoding="utf-8")
                           for f in ("app.py", "hcwc/ui/theory.py", "hcwc/ui/concept.py"))
        assert not [n for n in notes if n in source], "a superseded note is back on screen"

    def test_the_references_render_under_8_1_11(self):
        """The bibliography is 8.1.11 since 21 Sep 2026: one unnumbered subsection per `## `
        heading of docs/REFERENCES.md, with Beha in Method and the companion tools naming
        ArianeLogiX. There is no tab 8.3."""
        at = _run()
        blob = "\n".join(str(m.value) for m in at.get("markdown"))
        assert "8.1.11 · References" in blob
        for group in ("Method", "DHI evidence", "Companion tools"):
            assert f">{group}" in blob and "</h5>" in blob, (
                f"the bibliography's {group} section is missing")
        method = blob[blob.index(">Method"):]
        assert "Beha, A., Christensen, J. E. & Young, R. (2012)" in method
        assert "ariane-logix.com" in blob
        assert "8.3 ·" not in blob and "3 · References" not in blob

    def test_the_paper_has_its_own_section_rather_than_a_picker_entry(self):
        """Lars's restructure, 7 Sep 2026. The article is the thing you hand to someone who does
        not use the tool; burying it as one radio option among a dozen made it a footnote."""
        at = _run()
        blob = "\n".join(str(m.value) for m in at.get("markdown"))
        assert "competing geological limits and DHI evidence" in blob, (
            "the paper no longer renders on arrival")
        assert "8.2 The paper" in blob

    def test_the_paper_reviews_are_kept_but_not_shown(self):
        """*Don't delete them, keep them internally* \u2014 Lars, 7 Sep 2026. A user browsing the
        theory tab does not want five documents auditing other people's papers; whoever works on
        this repo next very much does.
        """
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        reviews = ["BEHA_2012_REVIEW.md", "HOOD_2019_REVIEW.md", "MONIGLE_2025_REVIEW.md",
                   "LOWRY_2005_REVIEW.md", "SEAL_CAPACITY_REVIEW.md"]
        missing = [n for n in reviews if not (root / "docs" / "reviews" / n).exists()]
        assert not missing, f"a review was deleted rather than kept: {missing}"

        source = "\n".join((root / f).read_text(encoding="utf-8")
                           for f in ("app.py", "hcwc/ui/theory.py", "hcwc/ui/concept.py"))
        surfaced = [n for n in reviews if f'"{n}"' in source]
        assert not surfaced, f"a review is back on screen: {surfaced}"

        index = (root / "docs" / "NEXT_PLAN.md").read_text(encoding="utf-8")
        unindexed = [n for n in reviews if n not in index]
        assert not unindexed, (
            "kept but unfindable \u2014 index them in docs/NEXT_PLAN.md: " + str(unindexed))

    def test_the_tabs_still_state_the_conclusion_and_say_where_to_read_it(self):
        """A pointer with no conclusion is worse than the essay: the reader at the slider has to
        leave the page to find out whether it matters to them. Since 15 Sep 2026 the pointer is a
        section number, "Method: see 8.1.x", not an essay title."""
        at = _run()
        blob = "\n".join(str(e.value) for kind in ("markdown", "caption", "info", "warning")
                          for e in at.get(kind))
        for conclusion in (
            "would count the geometry twice",
            "returning the same answer when its two inputs are swapped",
            "whether it carries something the model has not already used",
        ):
            assert conclusion in blob, f"the conclusion went with the essay: {conclusion!r}"
        assert "Method: see 8.1.9" in blob, "nothing points at 8.1.9"
        for stale in ("*Weight, not Bayes*", "*Base rates*", "*Prior or likelihood?*",
                      "tab 8.0", "Tab 8.0"):
            assert stale not in blob, f"a pointer still names the old essay or tab: {stale!r}"

    def test_no_moved_essay_is_still_duplicated_in_a_tab(self):
        """The split has to be a move, not a copy — two versions of one argument drift."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        sources = "\n".join(p.read_text(encoding="utf-8") for p in
                             [root / "app.py"] + sorted((root / "hcwc" / "ui").glob("*.py")))
        for phrase in ("Anyone who has fitted a hierarchical model",
                       "reproduces to 0.3913 under this expression",
                       "the benchmark reached by a longer road"):
            assert phrase not in sources, f"still in the tabs as well as in docs/: {phrase!r}"


class TestTheKnownGapIsNamedWhereItWouldBeLookedFor:
    """The Hood (2019) review, 7 Sep 2026, found one real gap: no seal-capacity route to a
    gas-oil contact. Lars's call was to note it in the app and plan it rather than build it.

    A planned gap is only honest while the note and the plan agree. These tests are what makes
    deleting one and forgetting the other a failure rather than a silent lie on screen.
    """

    def test_the_seal_calculator_says_it_holds_one_fluid(self):
        """The assessor on a two-phase prospect goes to the seal calculator, not to docs/."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        source = (root / "hcwc" / "ui" / "sources.py").read_text(encoding="utf-8")
        assert "Two phases in one closure" in source, (
            "the seal calculator no longer says it holds one fluid at a time")
        assert "PLAN_DUAL_PHASE_SEAL.md" in source, (
            "the note names no plan, so the gap reads as an omission rather than a decision")

    def test_the_plan_it_points_at_exists(self):
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        plan = root / "docs" / "PLAN_DUAL_PHASE_SEAL.md"
        assert plan.exists(), "the app points at a plan that is not in the checkout"
        text = plan.read_text(encoding="utf-8")
        assert "**Not started.**" in text, (
            "the plan no longer says it is unstarted -- if the work began, the app note is stale")

    def test_the_note_does_not_claim_the_feature_exists(self):
        """The failure mode this guards is a note that describes the physics so well the reader
        goes looking for the control. It has to say *not implemented* in those words."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        source = (root / "hcwc" / "ui" / "sources.py").read_text(encoding="utf-8")
        start = source.index("Two phases in one closure")
        block = source[start:start + 2500]
        assert "not implemented" in block, "the note describes a feature without saying it is absent"


class TestThePaperAgreesWithTheAppItDescribes:
    """`docs/ARTICLE.md` became a paper on 7 Sep 2026, with five figures generated from the
    engine and a worked prospect read at a 120 m assessment minimum.

    A paper whose numbers have drifted from the tool is worse than no paper, and the drift is
    silent -- nothing in a Markdown file fails when the code underneath it changes. These tests
    are the alarm.
    """

    ARTICLE = "paper/ARTICLE.md"
    #: Since 21 Sep 2026 the article's figures are drawn for the page by
    #: hcwc/plotting/paper/figures.py (scripts/paper_figures.py) from the scenario in
    #: scripts/paper_facts.py; the app exports (scripts/post_images.py) remain for the long
    #: manuscript, paper/ARTICLE_LONG_2026-09.md, and the workflow figure for tab 1.
    FIGURES = ("paper_fig1_competing_limits.png", "paper_fig2_controlling_mechanism.png",
               "paper_fig3_dhi_update.png", "paper_fig4_chance_against_depth.png",
               "paper_fig5_empirical_check.png")
    LONG_FIGURES = ("fig1_competing_limits.png", "fig2_controlling_mechanism.png",
                    "fig3_chance_against_depth.png", "fig4_dhi_update.png",
                    "fig5_truncate_vs_terminate.png", "fig6_chance_before_after.png")

    @staticmethod
    def _root():
        import pathlib
        return pathlib.Path(__file__).resolve().parent.parent

    def _text(self):
        return (self._root() / self.ARTICLE).read_text(encoding="utf-8")

    def test_every_figure_it_references_exists(self):
        """The app renders images through `st.image`, which shows a caption rather than raising
        when a file is missing -- so a deleted figure would degrade quietly."""
        text = self._text()
        for name in self.FIGURES:
            assert f"figures/{name}" in text, f"the paper no longer references {name}"
            assert (self._root() / "paper" / "figures" / name).exists(), \
                f"paper/figures/{name} is missing -- run scripts/post_images.py"
        long_text = (self._root() / "paper" / "ARTICLE_LONG_2026-09.md").read_text(encoding="utf-8")
        for name in self.LONG_FIGURES:
            assert f"figures/{name}" in long_text, f"the manuscript no longer references {name}"
            assert (self._root() / "paper" / "figures" / name).exists(), \
                f"paper/figures/{name} is missing -- run scripts/post_images.py"

    @pytest.mark.render
    def test_the_article_and_the_post_quote_paper_facts(self):
        """Audit P1-10 to P1-12, 21 Sep 2026: `scripts/paper_facts.py` is the one numerical
        source. The headline numbers the article and the post quote must be its output at the
        stated scenario, so a change in a default is caught here and not by a reader."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "paper_facts", self._root() / "scripts" / "paper_facts.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        f = module.facts()
        article = self._text()
        post = (self._root() / "paper" / "LINKEDIN_POST.md").read_text(encoding="utf-8")

        def pct(x):
            return f"{100 * x:.0f} %"

        for text in (article, post):
            assert pct(f["POS geological"]) in text and pct(f["POS given the DHI"]) in text
            assert f"{f['prior P90-P10 spread (m)']:.0f} m" in text
            assert f"{f['posterior P90-P10 spread (m)']:.0f} m" in text
            ess = f"{f['effective sample size']:,.0f}".replace(",", " ")
            assert ess in text, f"the effective sample size {ess} is not quoted"
            assert "effective sample size" in text
        p90, p50, p10 = f["prior HCWC P90/P50/P10 (m)"]
        assert f"{p90:,.0f} / {p50:,.0f} / {p10:,.0f}".replace(",", " ") in article
        shares = f["controlling shares (h >= h_min)"]
        for name, share in shares.items():
            if share > 0.03:
                assert pct(share) in article, f"{name} at {pct(share)} is not in the article"
        assert pct(f["P(well) given the DHI"]) in article

    def test_the_worked_prospect_is_reproducible(self):
        """The prospect definition ships beside the figures, so the numbers can be re-derived."""
        import json
        path = self._root() / "paper" / "figures" / "prospect.json"
        assert path.exists(), "the prospect the figures were drawn from was not written out"
        spec = json.loads(path.read_text(encoding="utf-8"))
        assert spec["min_column_m"] == 120.0, (
            "the figures were generated at a different assessment minimum than the paper states")
        assert spec["limits"], "the saved prospect has no limits"

    def test_pos_is_never_stated_without_the_element_term(self):
        """The error this paper was rewritten to remove: POS = F(h_min), dropping P(G).

        On the shipped prospect P(G) = 0.408 and F(120 m) = 0.61, so quoting the conditional term
        alone overstates the prospect by a factor of 2.5. The identity has to appear, and the
        bare form must not.
        """
        text = self._text()
        assert "P(G) \\times F(h_\\min)" in text or "P(G) \\times F(h_" in text, (
            "the paper no longer states POS = P(G) x F(h_min)")
        for wrong in ("POS = F(h_", "POS=F(h_"):
            assert wrong not in text, f"the conditional term is being quoted as the POS: {wrong!r}"

    def test_the_figures_script_still_runs_against_the_current_engine(self):
        """Import-level check only -- running the app is too slow for the suite, but a renamed
        core function would break the script silently until someone regenerated."""
        import importlib.util
        import pathlib
        path = pathlib.Path(self._root()) / "scripts" / "paper_figures.py"
        spec = importlib.util.spec_from_file_location("paper_figures", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in ("figure_5_truncate_vs_terminate", "from_the_app", "HMIN"):
            assert hasattr(module, name), f"scripts/paper_figures.py lost {name}"
        assert module.HMIN == 120.0

    def test_no_maths_crosses_a_line_break(self):
        """The formatting bug Lars caught on 7 Sep 2026, made into a failing test.

        A `$...$` or `$$...$$` that opens on one line and closes on the next is unterminated to
        a Markdown renderer, which then swallows everything after it until the next `$`. One
        wrapped equation in section 2 turned the rest of that section and all of section 3 into
        red LaTeX source on tab 8.0. Nothing raised; the page just quietly stopped being a paper.

        Every other document in `docs/` is checked too -- the reviews carry maths as well, and
        the failure looks identical there.
        """
        import pathlib

        DOLLAR = chr(36)

        root = pathlib.Path(self._root())
        problems = []
        for path in sorted([*(root / "docs").glob("*.md"), *(root / "paper").glob("*.md")]):
            lines = path.read_text(encoding="utf-8").split("\n")
            open_display = None
            for number, line in enumerate(lines, 1):
                display = line.count(DOLLAR + DOLLAR)
                if open_display is None:
                    if display == 1:
                        open_display = number
                elif display >= 1:
                    problems.append(f"{path.name}: display maths spans lines "
                                    f"{open_display}-{number}")
                    open_display = None
                if open_display is None and line.replace(DOLLAR + DOLLAR, "").count(DOLLAR) % 2:
                    problems.append(f"{path.name}:{number} inline maths does not close on "
                                    f"its own line")
            if open_display is not None:
                problems.append(f"{path.name}:{open_display} display maths never closes")
        assert not problems, (
            "maths crossing a line break renders as red source and eats what follows:\n  "
            + "\n  ".join(problems))

    def test_the_article_tab_renders_the_figures_rather_than_the_markdown(self):
        """`st.markdown` cannot resolve a relative image path, so the images would render broken
        rather than raise. The app splits them out; this is the check that it still does."""
        import pathlib
        root = pathlib.Path(self._root())
        theory = (root / "hcwc" / "ui" / "theory.py").read_text(encoding="utf-8")
        renderer = (root / "hcwc" / "ui" / "markdown.py").read_text(encoding="utf-8")
        assert "render_with_figures(_paper_text" in theory, (
            "the article is being passed straight to st.markdown, which cannot load its figures")
        assert "st.image(str(target)" in renderer


class TestTheIndependenceAssumptionsAreStatedWhereTheyBite:
    """Audit findings P1-1, P1-2 and P1-3, 14 Sep 2026.

    Three independence assumptions were stated once, on tab 1 or in a docstring, and nowhere a
    reader setting the affected control would see them: presence draws are outside the copula,
    calculator inputs are independent uniforms the correlation editor cannot reach, and the
    seal and charge calculators share a phase and not a fluid. Each is now beside its control.
    """

    @staticmethod
    def _blob(at):
        return "\n".join(str(e.value) for kind in ("markdown", "caption", "info", "warning",
                                                     "error")
                         for e in at.get(kind))

    #: The seal and fracture blocks open typed, so their calculators, and the notes inside
    #: them, render only when chosen.
    CALCULATORS = {"lim_Top seal (capillary)_src": "seal", "lim_Top seal (fracture)_src": "fracture"}

    def test_each_assumption_is_beside_its_control(self):
        blob = self._blob(_run(**self.CALCULATORS))
        for phrase in (
            "drawn independently of everything, including the presence of every other",  # P1-1
            "cannot reach inside a calculator",                                          # P1-2 seal
            "Stress and pore pressure are sampled as independent uniforms",              # P1-2 mech
            "share a phase and not a fluid",                                             # P1-3
        ):
            assert phrase in blob, f"not stated where it bites: {phrase!r}"

    def test_the_seal_note_is_labelled_a_modelling_choice(self):
        """CLAUDE.md, 15 Sep 2026: every assumption in the open is labelled elicited, heuristic
        or modelling choice."""
        # The same sentence opens a paragraph of 8.1.7, so the search is over the captions, where
        # the note on tab 3.0 is, rather than over everything on screen.
        captions = "\n".join(str(c.value) for c in _run(**self.CALCULATORS).caption)
        start = captions.index("cannot reach inside a calculator")
        assert "Modelling choice" in captions[start - 600:start + 200]


class TestTabsFourAndFiveOfferTheSameControls:
    """Lars, 15 Sep 2026: the scale-bars toggle was on 5.3.2 and not on 4.1.2, and the ask was
    that everything on the two result tabs is on both except what is about the DHI. The two are
    one renderer, so the check is on what it draws: every widget keyed by tab on 4 has its twin
    on 5, and the only widget 5 has that 4 does not is the DHI's own basis switch.
    """

    #: `competition_posterior`: the window on 5.2.1a can walk the posterior (21 Sep 2026);
    #: tab 4.1 has no posterior to walk.
    DHI_ONLY = {"controlling_view_N", "map_quantity_N", "map_depth_N",
                "competition_posterior_N"}

    def test_the_tab_keyed_widgets_match(self):
        import re
        at = _run(dhi_toggle=True)
        keys = set()
        for kind in ("radio", "checkbox", "toggle", "slider", "selectbox", "number_input",
                     "multiselect"):
            for w in at.get(kind):
                k = getattr(w, "key", None)
                if k:
                    keys.add(k)
        strip = lambda k: re.sub(r"_[45](_|$)", r"_N\1", k)  # noqa: E731
        on4 = {strip(k) for k in keys if re.search(r"_4(_|$)", k)}
        on5 = {strip(k) for k in keys if re.search(r"_5(_|$)", k)}
        # Tab 5.2's own controls carry a 5 as well; only the ones tab 4 also owns are compared.
        on5 = {k for k in on5 if not k.startswith(("combo_all", "hcwc_hist"))}
        assert on4 - on5 == set(), f"on tab 4 only: {sorted(on4 - on5)}"
        assert on5 - on4 == self.DHI_ONLY, f"on tab 5 only: {sorted(on5 - on4)}"

    def test_the_scale_toggle_is_on_both_tabs(self):
        at = _run(dhi_toggle=True)
        keys = {c.key for c in at.checkbox}
        assert {"controlling_scaled_4", "controlling_scaled_5"} <= keys

    def test_the_exhibit_counts_match(self):
        import re
        at = _run(dhi_toggle=True)
        seen = {}
        for c in at.caption:
            m = re.match(r"\*\*(Figure|Table) (\d\.\d)\.(\d+[a-z]+(?:\.\d+)?)\*\*", str(c.value))
            if m:
                seen.setdefault(m.group(2), []).append(m.group(1))
        # 5.2 carries seven exhibits 4.1 cannot: the strength-and-c sensitivity of 2e, which
        # exists only where there is evidence to vary (Lars, 17 Sep 2026). Everything else is
        # the same exhibit on the two bases, in the same order.
        assert len(seen["5.2"]) == len(seen["4.1"]) + 7, (seen["4.1"], seen["5.2"])
        assert seen["4.2"] == seen["5.3"], (seen["4.2"], seen["5.3"])


class TestTheCompetitionIsDrawnRealisationByRealisation:
    """Lars, 17 Sep 2026: the paper's figure 1, live, in place of the exceedance figure on 4.1
    and 5.2, whose curve it carries on its right-hand panel. Fifty realisations at a time, the shallowest active limit ringed in its controller's
    colour, a window slider through the whole run, and the whole distribution with its
    exceedance curve beside it."""

    def test_it_is_the_first_exhibit_on_both_result_tabs(self):
        at = _run(dhi_toggle=True)
        figures = at.session_state["_figures"]
        for label in ("Figure 4.1.1a", "Figure 5.2.1a"):
            fig, caption = figures[label]
            assert "The competition, realisation by realisation" in caption, label
            names = [str(t.name) for t in fig.data]
            assert any(n.startswith("shallowest active limit") for n in names), label
            assert any(n.startswith("P(z_HCWC ≥ z | G)") for n in names), label
        # Given the DHI the geological curve is drawn dashed beside the updated one, so what
        # the evidence moved is read in one panel (Lars, 17 Sep 2026); tab 4.1 carries one.
        names_5 = [str(t.name) for t in figures["Figure 5.2.1a"][0].data]
        assert "P(z_HCWC ≥ z | G), geological" in names_5
        assert sum(n.startswith("P(z_HCWC ≥ z | G)") for n in names_5) == 2
        names_4 = [str(t.name) for t in figures["Figure 4.1.1a"][0].data]
        assert sum(n.startswith("P(z_HCWC ≥ z | G)") for n in names_4) == 1

    def test_the_window_walks_the_run_in_steps_of_fifty(self):
        at = _run()
        slider = next(s for s in at.slider if s.key == "competition_window_4")
        assert slider.value == 0 and slider.max == 9_950 and slider.step == 50
        at.session_state["competition_window_4"] = 5_000
        at.run()
        fig, _ = at.session_state["_figures"]["Figure 4.1.1a"]
        assert fig.layout.xaxis.title.text == "realisation (5,000 to 5,049)"
        rings = next(t for t in fig.data if str(t.name).startswith("shallowest active limit"))
        assert len(rings.y) == 50

    def test_tab_5_walks_the_posterior_and_can_walk_the_run(self):
        """Lars, 21 Sep 2026: given the DHI the window shows the geological realisations drawn
        by their posterior weight, so what is on the left is the posterior; the toggle returns
        to the run's own order. The hover names the run realisation behind each one."""
        import numpy as np

        from hcwc.core import dhi

        at = _run()
        fig, caption = at.session_state["_figures"]["Figure 5.2.1a"]
        assert fig.layout.xaxis.title.text == "posterior realisation (0 to 49)"
        rings = next(t for t in fig.data if str(t.name).startswith("shallowest active limit"))
        post = at.session_state["dhi_posterior"]
        expect = dhi.posterior_indices(post)[:50]
        assert [row[1] for row in rings.customdata] == [str(i) for i in expect]
        np.testing.assert_allclose(np.asarray(rings.y, float), post.result.contact_m[expect])
        assert "drawn from the run by that weight" in caption
        # the posterior's fifty sit nearer the pick than the run's first fifty
        assert (np.std(post.result.contact_m[expect])
                < np.std(post.result.contact_m[:50]))

        at.session_state["competition_posterior_5"] = False
        at.run()
        fig, caption = at.session_state["_figures"]["Figure 5.2.1a"]
        assert fig.layout.xaxis.title.text == "realisation (0 to 49)"
        rings = next(t for t in fig.data if str(t.name).startswith("shallowest active limit"))
        assert [row[1] for row in rings.customdata] == [str(i) for i in range(50)]
        assert "the run's own, in the order drawn" in caption
        # tab 4.1 has no toggle
        assert not any(t.key == "competition_posterior_4" for t in at.toggle)

    def test_the_monigle_route_is_a_comparison_only(self):
        """Comparison-only by decision, 22 Sep 2026: the radio offers the stated value and the
        graded attributes; a prospect saved on the score route opens on the stated value with a
        notice, and the score's reading stays on screen beside the c in use."""
        at = _run(dhi_in_c_source="DHI score, Monigle et al. (2025)")
        radio = next(r for r in at.radio if r.key == "dhi_in_c_source")
        assert radio.options == ["Stated", "Graded attributes"]
        assert radio.value == "Stated"
        assert any("comparison now" in str(i.value) for i in at.info)
        assert any("Comparison only. Monigle" in str(c.value) for c in at.caption)
        assert at.session_state["dhi_posterior"].observation.p_valid == pytest.approx(0.36)

    def test_the_outcomes_are_on_tab_5_1_4_and_the_well_names_its_interval(self):
        """Lars, 21 Sep 2026: what the DHI can turn out to have been, as a bar, a table and the
        shaded intervals on 5.1.4a; 5.2.4 says which interval the well enters."""
        from hcwc.core import dhi

        at = _run()
        figures = at.session_state["_figures"]
        tables = at.session_state["_tables"]
        bar, cap = figures["Figure 5.1.4b"]
        assert [t.name for t in bar.data] == list(dhi.OUTCOMES)
        shares = [float(t.x[0]) for t in bar.data]
        assert sum(shares) == pytest.approx(1.0, abs=1e-9)
        overlay = at.session_state["dhi_overlay"]
        assert shares[0] == pytest.approx(1.0 - overlay["p_g_given_amplitude"], abs=1e-9)
        assert "Method: see 8.1.8" in cap
        table, tcap, *_ = tables["Table 5.1.4c"]
        assert list(table["DHI / contact relation"]) == list(dhi.OUTCOMES)
        assert "A well entering there finds" not in table.columns
        assert "posterior attribution" in tcap
        hist, hcap = figures["Figure 5.1.4a"]
        assert len(hist.layout.shapes) >= 3 and "indicated contact band" in hcap
        top, base = overlay["indicated_band_m"]
        assert top < overlay["picked_contact_m"] < base
        assert any("The well enters" in str(c.value) and "indicated contact band" in str(c.value)
                   for c in at.caption)

    def test_the_rings_take_their_controllers_colours(self):
        """An open marker's stroke is `marker.color`; per-point colours there are the point."""
        fig, _ = _run().session_state["_figures"]["Figure 4.1.1a"]
        rings = next(t for t in fig.data if str(t.name).startswith("shallowest active limit"))
        assert rings.marker.symbol == "circle-open"
        assert len(set(rings.marker.color)) > 1, "every ring has the same colour"
