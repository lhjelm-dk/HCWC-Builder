"""The reusable limit block — the component tab ③ instantiates twelve times.

Only the pure parts are tested here: the stats convention, the parameter tables, and the defaults.
The Streamlit rendering itself is covered by the app-level smoke test in `test_ui_imports.py`.

The convention tests matter more than they look. `P90` meaning the *shallow* end is the single
assumption that, if it silently flipped, would invert every limit preview in the tool without
raising anything anywhere.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.core.limits import _KINDS, DepthDistribution
from hcwc.ui import limit_block as lb


class TestStatsRow:
    def test_the_percentiles_are_exceedance_not_ascending(self):
        """P90 is the value 90 % of realisations come out *deeper* than, so it is the shallow end.

        If this ever flips, every block's table and figure become wrong in the same direction and
        nothing raises — which is exactly why it is asserted rather than assumed.
        """
        samples = np.random.default_rng(0).normal(2300.0, 50.0, 60_000)
        row = lb.stats_row(samples)
        assert row["P100"] < row["P90"] < row["P50"] < row["P10"] < row["P0"]
        assert row["P90"] == pytest.approx(np.percentile(samples, 10))
        assert row["P10"] == pytest.approx(np.percentile(samples, 90))

    def test_it_matches_the_geox_export_convention(self):
        """The export writes P100 as the shallowest contact. A block that disagreed with the file
        it feeds would be a contradiction inside one tool."""
        from hcwc.io import geox
        samples = np.random.default_rng(3).normal(2300.0, 60.0, 20_000)
        row = lb.stats_row(samples)
        table = geox.percentile_table(samples, tail_mode="raw").table
        by_percentile = dict(zip(table["Percentile"], table["Value"]))
        assert row["P90"] == pytest.approx(by_percentile[90], rel=1e-6)
        assert row["P10"] == pytest.approx(by_percentile[10], rel=1e-6)

    def test_the_extremes_are_the_sample_bounds(self):
        samples = np.random.default_rng(1).uniform(100.0, 400.0, 10_000)
        row = lb.stats_row(samples)
        assert row["P100"] == pytest.approx(samples.min())
        assert row["P0"] == pytest.approx(samples.max())

    def test_the_mean_is_reported_because_it_is_not_p50(self):
        """On a skewed limit the two differ, and an assessor who elicited a mean needs to see what
        the shape did to it."""
        samples = np.random.default_rng(2).lognormal(5.0, 0.8, 40_000)
        row = lb.stats_row(samples)
        assert row["Mean"] > row["P50"]


class TestForms:
    def test_every_offered_form_is_a_distribution_the_core_knows(self):
        assert set(lb.FORMS) <= set(_KINDS)

    def test_every_form_asks_for_exactly_the_parameters_it_needs(self):
        """A form that asked for too few would raise on construction; one that asked for too many
        would raise on the `extra` check. Either way the block would be unusable, so the tables are
        matched here rather than discovered in the browser.

        `normal_alt` is the deliberate exception: its two percentiles are pinned at P10/P90 in the
        block, so only the two *values* are asked for.
        """
        for form, (_, specs) in lb.FORMS.items():
            asked = {key for key, _ in specs}
            needed = set(_KINDS[form][1])
            if form == "normal_alt":
                assert asked == {"x1", "x2"}
                assert needed - asked == {"p1", "p2"}
            else:
                assert asked == needed, form

    def test_the_defaults_build_a_valid_distribution_for_every_form(self):
        """Switching distribution must never leave the block in a state that throws. This walks
        every form with the shared defaults and constructs it."""
        base = lb._defaults(50.0, 300.0)
        for form, (_, specs) in lb.FORMS.items():
            params = {key: base[key] for key, _ in specs}
            if form == "normal_alt":
                params |= {"p1": 0.10, "p2": 0.90}
            distribution = DepthDistribution(form, params)
            drawn = distribution.ppf(np.linspace(0.001, 0.999, 128))
            assert np.isfinite(drawn).all(), form

    def test_selecting_beta_subj_does_not_error_before_anything_is_typed(self):
        """`BetaSubj` has no solution when the mode sits exactly at the midpoint of the support --
        the four points determine symmetry and nothing else.

        A midpoint default would mean choosing BetaSubj threw an error before the user had entered
        a single number, which is precisely the class of unhelpfulness this rebuild exists to
        remove. So the shared default is mildly right-skewed, and this pins it.
        """
        base = lb._defaults(50.0, 300.0)
        assert base["mode"] != 0.5 * (50.0 + 300.0)
        assert base["mean"] != base["mode"]
        drawn = DepthDistribution("beta_subj", {k: base[k] for k in
                                                ("minimum", "mode", "mean", "maximum")}
                                  ).ppf(np.linspace(0.001, 0.999, 64))
        assert np.isfinite(drawn).all()
        assert base["minimum"] <= drawn.min() and drawn.max() <= base["maximum"]

    def test_the_defaults_span_the_range_they_are_given(self):
        base = lb._defaults(100.0, 500.0)
        assert base["minimum"] == 100.0 and base["maximum"] == 500.0
        assert base["mode"] == pytest.approx(260.0)
        assert base["mean"] == pytest.approx(280.0)
        assert base["x1"] == pytest.approx(140.0) and base["x2"] == pytest.approx(460.0)
