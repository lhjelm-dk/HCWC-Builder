"""Placing the built distribution inside a benchmark's.

The one assumption everything rests on is the direction: **below P50 is optimistic**. A taller
predicted column scores *lower*, because fewer of the benchmark's closures reach it. Inverting that
would flip every verdict on tab 8.0 and raise nothing anywhere, so it is the first thing tested.
"""
from __future__ import annotations

import math

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


class TestAnEmptyBuiltDistribution:
    def test_it_explains_itself_rather_than_raising_out_of_numpy(self):
        """An assessment minimum above every achievable column leaves nothing to place inside a
        benchmark. `np.percentile` of an empty array is an `IndexError` from deep inside numpy,
        which is what a reader saw — for a question ("is this commercial at 350 m?") whose honest
        answer is simply *no*."""
        with pytest.raises(ValueError, match="no realisation reached the assessment minimum"):
            calibration.compare(np.array([]), np.array([10.0, 20.0, 30.0]), "a benchmark")

    def test_an_empty_benchmark_is_named_separately(self):
        with pytest.raises(ValueError, match="benchmark drew no samples"):
            calibration.compare(np.array([10.0, 20.0]), np.array([]), "a benchmark")


# --------------------------------------------------------------------------- the tab-6 statistics
#
# Both of these reach the screen: `corridor_share` as a legend string on the Q-Q plot -- "Fitted
# NCS - 42 % in band" -- and `quantile_ratios` as its own curve. Until 8 Sep 2026 neither had an
# assertion anywhere: the render tests proved the tab drew without raising, and nothing checked
# the numbers on it. A wrong corridor share reads as a confident, precise QC verdict, on the tab
# whose whole job is saying whether you are optimistic.


class TestCorridorShare:
    """The share of matched quantiles within `CORRIDOR` of the benchmark."""

    def test_a_distribution_against_itself_is_everything_in_band(self):
        rng = np.random.default_rng(11)
        same = rng.normal(200.0, 40.0, 40_000)
        assert calibration.corridor_share(same, same) == pytest.approx(1.0)

    def test_it_is_a_fraction_not_a_percentage(self):
        """The caller formats it with `:.0%`, so returning 42.0 instead of 0.42 would print
        '4200 % in band' -- or, worse, 0.42 would print as '0 %' if the convention flipped."""
        rng = np.random.default_rng(12)
        same = rng.normal(200.0, 40.0, 20_000)
        got = calibration.corridor_share(same, same)
        assert 0.0 <= got <= 1.0

    def test_a_uniform_ratio_just_inside_the_corridor_is_all_in_band(self):
        rng = np.random.default_rng(13)
        bench = rng.normal(200.0, 40.0, 40_000)
        inside = bench * (1.0 + calibration.CORRIDOR * 0.9)
        assert calibration.corridor_share(inside, bench) == pytest.approx(1.0)

    def test_a_uniform_ratio_just_outside_the_corridor_is_none_in_band(self):
        """The pair above and below pin the threshold itself, not merely the direction."""
        rng = np.random.default_rng(14)
        bench = rng.normal(200.0, 40.0, 40_000)
        outside = bench * (1.0 + calibration.CORRIDOR * 1.1)
        assert calibration.corridor_share(outside, bench) == pytest.approx(0.0)

    def test_the_tolerance_is_relative_not_absolute(self):
        """15 % of 40 m is 6 m and 15 % of 400 m is 60 m. An absolute corridor would call a
        shallow prospect badly calibrated and a deep one well calibrated for the same error."""
        rng = np.random.default_rng(15)
        small = rng.normal(40.0, 8.0, 20_000)
        large = small * 10.0
        assert calibration.corridor_share(small * 1.10, small) == pytest.approx(
            calibration.corridor_share(large * 1.10, large))

    def test_a_widening_bias_lowers_the_share(self):
        rng = np.random.default_rng(16)
        bench = rng.normal(200.0, 40.0, 40_000)
        shares = [calibration.corridor_share(bench * (1.0 + k), bench)
                  for k in (0.02, 0.10, 0.20, 0.50)]
        assert shares == sorted(shares, reverse=True)

    def test_an_explicit_tolerance_overrides_the_default(self):
        rng = np.random.default_rng(17)
        bench = rng.normal(200.0, 40.0, 20_000)
        drifted = bench * 1.25
        assert calibration.corridor_share(drifted, bench, tolerance=0.15) == pytest.approx(0.0)
        assert calibration.corridor_share(drifted, bench, tolerance=0.30) == pytest.approx(1.0)

    def test_a_benchmark_pinned_at_zero_is_nan_rather_than_a_division(self):
        """Every matched quantile of an all-zero benchmark is zero, so every ratio is undefined.
        Returning 0.0 would read as 'nothing agrees'; the honest answer is 'unanswerable'."""
        zeros = np.zeros(500)
        assert math.isnan(calibration.corridor_share(zeros, zeros))


class TestQuantileRatios:
    """Built over benchmark at each matched quantile. Above 1 is a taller predicted column."""

    def test_a_distribution_against_itself_is_flat_at_one(self):
        rng = np.random.default_rng(21)
        same = rng.normal(200.0, 40.0, 40_000)
        assert calibration.quantile_ratios(same, same) == pytest.approx(1.0)

    def test_a_taller_prediction_is_above_one(self):
        """The direction, and it is the opposite of `exceedance_percentile`'s: a taller column
        raises this curve and lowers that score. Both are on tab 6.0 and a reader comparing them
        needs each to mean what it says."""
        rng = np.random.default_rng(22)
        bench = rng.normal(200.0, 40.0, 40_000)
        assert np.all(calibration.quantile_ratios(bench * 1.3, bench) > 1.0)
        assert np.all(calibration.quantile_ratios(bench * 0.7, bench) < 1.0)

    def test_a_uniform_scaling_is_a_flat_curve_at_that_scale(self):
        """Flat means correctable bias. The shape is the finding, so a flat input must not come
        back with structure in it."""
        rng = np.random.default_rng(23)
        bench = rng.normal(200.0, 40.0, 40_000)
        got = calibration.quantile_ratios(bench * 1.2, bench)
        assert got == pytest.approx(1.2, rel=1e-9)

    def test_tail_optimism_shows_as_a_rising_curve(self):
        """The distinction the docstring exists for: a flat 1.2 is a correctable bias, a ratio
        rising toward the upside is optimism concentrated in the tail the volume comes from."""
        rng = np.random.default_rng(24)
        bench = np.sort(rng.normal(200.0, 40.0, 40_000))
        stretched = bench + np.linspace(0.0, 120.0, bench.size)
        got = calibration.quantile_ratios(stretched, bench)
        assert got[-1] > got[0]
        assert np.corrcoef(np.arange(got.size), got)[0, 1] > 0.9

    def test_it_returns_one_value_per_matched_quantile(self):
        rng = np.random.default_rng(25)
        bench = rng.normal(200.0, 40.0, 10_000)
        mine, _ = calibration.quantile_pairs(bench, bench)
        assert calibration.quantile_ratios(bench, bench).shape == mine.shape

    def test_a_zero_in_the_benchmark_is_nan_rather_than_infinity(self):
        """`inf` on a plotted curve rescales the axis and hides every real value on it."""
        got = calibration.quantile_ratios(np.linspace(1.0, 100.0, 500), np.zeros(500))
        assert np.isnan(got).all()

    def test_the_ratios_agree_with_the_pairs_they_come_from(self):
        """Two functions read off one Q-Q construction; they must not drift apart."""
        rng = np.random.default_rng(26)
        bench = rng.normal(200.0, 40.0, 20_000)
        built = rng.normal(230.0, 50.0, 20_000)
        mine, theirs = calibration.quantile_pairs(built, bench)
        assert calibration.quantile_ratios(built, bench) == pytest.approx(mine / theirs)


class TestTheTwoStatisticsAgreeWithEachOther:
    def test_the_share_counts_exactly_the_ratios_inside_the_corridor(self):
        """`corridor_share` is the fraction of `quantile_ratios` within tolerance of 1. Stated as
        a test because they are computed separately and shown side by side."""
        rng = np.random.default_rng(31)
        bench = np.sort(rng.normal(200.0, 40.0, 30_000))
        built = bench + np.linspace(-40.0, 90.0, bench.size)
        ratios = calibration.quantile_ratios(built, bench)
        by_hand = float(np.mean(np.abs(ratios - 1.0) <= calibration.CORRIDOR))
        assert calibration.corridor_share(built, bench) == pytest.approx(by_hand)
