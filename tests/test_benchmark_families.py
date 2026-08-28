"""The two generated benchmark families, and what actually separates them.

The headline finding: **the C&C series is not a dataset.** It and the ExxonMobil series are the
same banded fill-to-spill model, sharing the same Bernoulli weight to the digit. They differ in
exactly one thing — the distribution drawn when the closure does *not* fill to spill. There was no
table of reservoir statistics to extract; there was a shape.

The C&C shape is still gated behind `reference/private/`, so everything touching it skips when it is
absent. That is a normal state, not a failure — every clone except Lars's is in it.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.io import benchmarks


class TestTheSharedBandedModel:
    def test_the_spill_weight_matches_the_published_bernoulli(self):
        """`O8 = RiskBernoulli(0.6 + (h - 250) * 0.00073)` is the *survival* probability, so the
        fill-to-spill weight is its complement. The two published endpoints have to meet: 0.4 below
        250 m, and zero at 800 m.

        **The slope is not rounded here.** 0.00073 is the obvious rounding of the exact
        0.4/550 = 0.000727..., which is why the tolerance is 3e-4 rather than exact — and the
        rounding is what pushes the Bernoulli argument above 1 near the top of the band; see
        :meth:`test_a_rounded_slope_pushes_the_bernoulli_above_one`.
        """
        assert benchmarks.spill_weight(100.0) == pytest.approx(0.4)
        assert benchmarks.spill_weight(249.0) == pytest.approx(0.4)
        assert benchmarks.spill_weight(350.0) == pytest.approx(1.0 - (0.6 + 100 * 0.00073), abs=3e-4)
        assert benchmarks.spill_weight(800.0) == pytest.approx(0.0, abs=1e-9)
        assert benchmarks.spill_weight(1200.0) == 0.0

    def test_a_rounded_slope_pushes_the_bernoulli_above_one(self):
        """Low severity, but real, and the reason the exact slope is used.

        With the rounded slope the survival probability passes 1.0 at h = 797.9 m, so for the top
        2 m of the band a Bernoulli is being asked for a probability above 1. Nothing visible
        happens — the draw is a survival either way — which is exactly why it would go unnoticed.
        The exact slope reaches zero at 800 m by construction and cannot overshoot.
        """
        assert 0.6 + (798.0 - 250.0) * 0.00073 > 1.0
        assert all(0.0 <= benchmarks.spill_weight(h) <= 1.0
                   for h in (250.0, 500.0, 797.0, 798.0, 800.0, 900.0))

    def test_it_decays_monotonically_across_the_band(self):
        weights = [benchmarks.spill_weight(h) for h in (250.0, 400.0, 600.0, 800.0)]
        assert weights == sorted(weights, reverse=True)

    def test_a_non_positive_relief_is_refused(self):
        with pytest.raises(ValueError, match="positive"):
            benchmarks.spill_weight(0.0)

    def test_graham_is_the_exxonmobil_branch(self):
        """`graham_column_height` was written from the published abstract, and the banded model
        was written independently. They agree exactly, which is the cross-check that the linear
        reading of Graham's decay is not just our reading."""
        rng = np.random.default_rng(3)
        drawn = benchmarks.graham_column_height(rng, 350.0, 200_000)
        assert np.mean(drawn >= 350.0) == pytest.approx(benchmarks.spill_weight(350.0), abs=0.005)
        free = drawn[drawn < 350.0]
        assert free.min() >= 20.0
        # Uniform on [20, h]: the mean sits at the midpoint.
        assert free.mean() == pytest.approx((20.0 + 350.0) / 2, rel=0.02)


class TestTheCCBranch:
    """Skipped wholesale when the private shape is absent, which is the normal state off Lars's
    machine and must not read as a failure."""

    @pytest.fixture(autouse=True)
    def _needs_shape(self):
        if benchmarks.load_cc_shape() is None:
            pytest.skip("reference/private/cc_shape.json is not on this machine")

    def test_it_shares_the_spill_weight_exactly(self):
        """The whole point. If these two ever diverge, the claim that one shape separates the
        families is wrong and the UI copy saying so has to change."""
        rng = np.random.default_rng(5)
        for relief in (100.0, 350.0, 600.0):
            cc = benchmarks.cc_column_height(rng, relief, 200_000)
            ex = benchmarks.graham_column_height(rng, relief, 200_000)
            assert np.mean(cc >= relief) == pytest.approx(np.mean(ex >= relief), abs=0.006)

    def test_it_fills_closures_much_harder_than_the_uniform_branch(self):
        """The consequence of the shape, and the reason the choice is worth seeing: on an 800 m
        closure the top-weighted shape puts the P50 column near 700 m where uniform puts it near
        410 m. One modelling decision, a 70 % difference in the prior."""
        rng = np.random.default_rng(7)
        cc = benchmarks.cc_column_height(rng, 800.0, 200_000)
        ex = benchmarks.graham_column_height(rng, 800.0, 200_000)
        assert np.median(cc) > np.median(ex) * 1.5
        assert np.median(cc) / 800.0 > 0.8
        assert np.median(ex) / 800.0 < 0.6

    def test_it_respects_the_same_floor_and_ceiling(self):
        rng = np.random.default_rng(9)
        drawn = benchmarks.cc_column_height(rng, 400.0, 50_000)
        assert drawn.min() >= 20.0
        assert drawn.max() <= 400.0

    def test_the_shape_is_never_committed(self):
        """The instruction was "keep for now, hidden". This asserts the mechanism that honours it:
        the parameters live under the git-ignored private directory and nowhere else."""
        import subprocess
        path = benchmarks.PRIVATE / "cc_shape.json"
        out = subprocess.run(["git", "check-ignore", str(path)],
                             cwd=path.parents[2], capture_output=True, text=True)
        assert out.returncode == 0, "cc_shape.json is NOT git-ignored"


def test_a_missing_shape_omits_the_series_rather_than_raising(monkeypatch):
    """A clone without the private directory must still run the tab, with the series simply gone."""
    monkeypatch.setattr(benchmarks, "load_cc_shape", lambda: None)
    assert benchmarks.cc_column_height(np.random.default_rng(1), 300.0, 10) is None
