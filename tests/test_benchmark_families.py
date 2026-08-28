"""The two generated benchmark families, and what actually separates them.

The banded fill-to-spill model: a Bernoulli on whether the closure fills, and a shape for the
column when it does not. The weight is Graham's and is published; the shape is a modelling choice.

A benchmark of your own goes through `hcwc.io.datasets` instead — raw discoveries, fitted here with
the censoring correction — and is tested in `tests/test_datasets.py`.
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


