"""Placing the built distribution inside a benchmark's.

The one assumption everything rests on is the direction: **below P50 is optimistic**. A taller
predicted column scores *lower*, because fewer of the benchmark's closures reach it. Inverting that
would flip every verdict on tab ⑧ and raise nothing anywhere, so it is the first thing tested.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.core import calibration


class TestExceedancePercentile:
    def test_the_median_of_a_sample_lands_at_fifty(self):
        samples = np.random.default_rng(0).normal(200.0, 40.0, 60_000)
        assert calibration.exceedance_percentile(float(np.median(samples)), samples) \
            == pytest.approx(50.0, abs=0.5)

    def test_a_taller_column_scores_lower(self):
        """The direction, stated as a test. Fewer of the benchmark's closures reach a taller
        column, so a taller column is a *lower* exceedance percentile — and that is what makes
        'below 50' mean optimistic rather than the reverse."""
        samples = np.random.default_rng(1).normal(200.0, 40.0, 60_000)
        assert (calibration.exceedance_percentile(260.0, samples)
                < calibration.exceedance_percentile(200.0, samples)
                < calibration.exceedance_percentile(140.0, samples))

    def test_an_empty_benchmark_is_nan_not_zero(self):
        """Zero would read as 'wildly optimistic' rather than 'no comparison', which is the worst
        available way to report a missing benchmark."""
        assert np.isnan(calibration.exceedance_percentile(200.0, np.array([])))


class TestComparison:
    @staticmethod
    def _pair(built_mean: float, bench_mean: float = 200.0, sd: float = 40.0):
        rng = np.random.default_rng(7)
        return (rng.normal(built_mean, sd, 40_000), rng.normal(bench_mean, sd, 40_000))

    def test_an_identical_distribution_is_in_line(self):
        rng = np.random.default_rng(3)
        same = rng.normal(200.0, 40.0, 40_000)
        c = calibration.compare(same, same, "itself")
        assert c.p50_lands_at == pytest.approx(50.0, abs=1.0)
        assert c.verdict == "in line"
        assert c.ratio == pytest.approx(1.0, abs=0.01)

    def test_a_taller_prediction_reads_optimistic(self):
        built, bench = self._pair(260.0)
        c = calibration.compare(built, bench, "benchmark")
        assert c.p50_lands_at < 40.0
        assert c.verdict == "optimistic"
        assert c.ratio > 1.0

    def test_a_shorter_prediction_reads_conservative(self):
        built, bench = self._pair(140.0)
        c = calibration.compare(built, bench, "benchmark")
        assert c.p50_lands_at > 60.0
        assert c.verdict == "conservative"
        assert c.ratio < 1.0

    def test_a_small_difference_is_not_dressed_up_as_a_finding(self):
        """A few thousand realisations move a percentile on their own. Inside the neutral band the
        honest report is 'in line', not a spurious direction."""
        built, bench = self._pair(205.0)
        assert calibration.compare(built, bench, "benchmark").verdict == "in line"

    def test_the_sentence_carries_the_number_and_the_direction(self):
        built, bench = self._pair(260.0)
        sentence = calibration.compare(built, bench, "Graham et al.").sentence
        assert "Graham et al." in sentence and "optimistic" in sentence and "P" in sentence

    def test_the_percentiles_use_the_exceedance_convention(self):
        """P90 is the shallow end here as everywhere else in the tool."""
        built, bench = self._pair(200.0)
        c = calibration.compare(built, bench, "benchmark")
        assert c.built_p90 < c.built_p50 < c.built_p10
        assert c.bench_p90 < c.bench_p50 < c.bench_p10


class TestQuantilePairs:
    def test_identical_distributions_lie_on_the_45_degree_line(self):
        rng = np.random.default_rng(5)
        same = rng.normal(200.0, 40.0, 40_000)
        a, b = calibration.quantile_pairs(same, same)
        assert np.allclose(a, b)

    def test_the_unstable_extremes_are_trimmed(self):
        """P0 and P100 of a Monte Carlo are its sample minimum and maximum, so a Q–Q plot that
        ended on them would swing on one realisation at each corner."""
        rng = np.random.default_rng(6)
        drawn = rng.normal(200.0, 40.0, 40_000)
        a, _ = calibration.quantile_pairs(drawn, drawn)
        assert a.min() > drawn.min() and a.max() < drawn.max()

    def test_a_uniform_offset_shows_as_a_parallel_shift(self):
        """The shape carries what the single number cannot: uniform optimism is a line parallel to
        the diagonal, which is a correctable bias, not a distortion."""
        rng = np.random.default_rng(8)
        bench = rng.normal(200.0, 40.0, 40_000)
        a, b = calibration.quantile_pairs(bench + 50.0, bench)
        assert np.allclose(a - b, 50.0, atol=2.0)
