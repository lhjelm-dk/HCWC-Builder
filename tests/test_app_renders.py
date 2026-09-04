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

    p90, p50, _ = _contact_quantiles()
    bracket = _well(well_in_hc_on=True, well_in_hc=p90)
    _no_exception(bracket, "a bracketing penetration")
    assert spread(bracket) < spread(_well())
    assert spread(bracket) < spread(_run())


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
    at = _run(**{f"{key}_src": "seal_as_top", f"{key}_pa": 1.0, f"{key}_thickness": thickness})
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
    at = _run(**{f"{key}_src": "seal_as_top", f"{key}_pa": 1.0})
    got = [w.value for w in at.number_input if w.key == f"{key}_thickness"]
    assert got == [50.0]


@pytest.mark.parametrize("source", ["seal", "seal_as_top"])
def test_both_routes_to_the_base_seal_put_it_in_the_same_place(source):
    """*Same as the top seal* and *From seal capacity* are two entry points to one limit. If only
    one carried the reservoir-thickness offset they would disagree about where that limit sits."""
    import numpy as np

    from hcwc.ui import run as engine_run

    key = "lim_Base seal (capillary)"
    at = _run(**{f"{key}_src": source, f"{key}_pa": 1.0, f"{key}_thickness": 50.0})
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
        at = _run()
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
        at = _run(**{f"{self.KEY}_fluid": fluid, f"{self.KEY}_rh": rho})
        _no_exception(at, f"{fluid} at {rho}")
        fired = any("density against" in w.value for w in at.warning)
        assert fired is should_warn

    def test_the_shipped_capacity_matches_the_elicited_ranges(self):
        """Pins the defaults to the numbers Lars actually wants: 79 / 148 / 433 m."""
        at = _run()
        got = [m.value for m in at.metric if m.label.endswith("capacity")]
        assert got == ["79 m", "148 m", "433 m"], got


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

    def test_the_empirical_prior_is_drawn_by_default_and_nothing_else_is(self):
        names = set(self._violins(_run()))
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
        import numpy as np

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
        assert "The DHI, on its own" in centres, "the amplitude has no lane of its own"

        evidence = centres["The DHI, on its own"]
        limits = [x for name, x in centres.items()
                  if not name.startswith("Resulting HC depth") and name != "The DHI, on its own"]
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
        from hcwc.ui import limit_stack
        assert {limit_stack.LIMITS_GROUP, limit_stack.EVIDENCE_GROUP,
                limit_stack.RESULT_GROUP} <= headings, f"headings found: {headings}"

    def test_the_geological_tab_has_no_amplitude_group(self):
        """Nothing to show there, and a group heading over an empty gap would be worse than none."""
        centres, layout = None, None
        at = _run(**{"stack_mode_4": "Violin"})
        import base64
        import json

        import numpy as np
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            names = [str(t.get("name")) for t in spec.get("data", [])]
            if "Resulting HC depth" in names and not any("given the DHI" in n for n in names):
                assert "The DHI, on its own" not in names
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
                if str(trace.get("name")) != "The DHI, on its own":
                    continue
                assert trace.get("line", {}).get("dash") == "dot", \
                    "the amplitude lane is drawn like a sample"
                x = np.frombuffer(base64.b64decode(trace["x"]["bdata"]),
                                  dtype=np.dtype(trace["x"].get("dtype", "f8")))
                # Peak-normalised into a lane of width LANE_FILL, so it spans at most that.
                from hcwc.ui import limit_stack
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
                if str(trace.get("name")) != "The DHI, on its own":
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
        import numpy as np

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
        found = [t for t, _, _ in self._traces(at, "The DHI, on its own")]
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
                                        "The DHI, on its own"):
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
