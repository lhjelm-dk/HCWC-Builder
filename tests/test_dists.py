"""Parity tests for the elicited distributions.

The targets are the *parameterisations*, not any particular run's summary statistics.
That is deliberate: simulation statistics from a Latin-Hypercube run with an unfixed
seed are not reproducible, so asserting on them would be asserting on noise. What *is*
reproducible is that `RiskNormalAlt(0.01%, 2049, 99.99%, 2051)` is the normal whose
0.01% point is 2049 -- so that is what these check.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import norm

from hcwc.core import dists


def rng() -> np.random.Generator:
    return np.random.default_rng(20260825)


class TestNormalAlt:
    def test_hits_both_stated_percentiles(self):
        # the apex depth.
        mu, sigma = dists.normal_alt_params(0.0001, 2049.0, 0.9999, 2051.0)
        assert norm.cdf(2049.0, mu, sigma) == pytest.approx(0.0001, abs=1e-12)
        assert norm.cdf(2051.0, mu, sigma) == pytest.approx(0.9999, abs=1e-12)

    def test_symmetric_input_gives_midpoint_mean(self):
        mu, _ = dists.normal_alt_params(0.0001, 2049.0, 0.9999, 2051.0)
        assert mu == pytest.approx(2050.0)

    def test_closure_height_case(self):
        # RiskNormalAlt(1%, 340, 99%, 360), mean 350.
        mu, sigma = dists.normal_alt_params(0.01, 340.0, 0.99, 360.0)
        assert mu == pytest.approx(350.0)
        assert sigma == pytest.approx(10.0 / norm.ppf(0.99))

    def test_samples_match_the_parameters(self):
        n = 200_000
        x = dists.normal_alt(rng(), 0.01, 340.0, 0.99, 360.0, n)
        assert x.mean() == pytest.approx(350.0, abs=0.05)

    def test_equal_percentiles_rejected(self):
        with pytest.raises(ValueError, match="must differ"):
            dists.normal_alt_params(0.5, 1.0, 0.5, 2.0)

    def test_inverted_percentiles_rejected(self):
        # p2 > p1 but x2 < x1 -- an assessor who typed the depths the wrong way round.
        with pytest.raises(ValueError, match="non-positive sigma"):
            dists.normal_alt_params(0.01, 360.0, 0.99, 340.0)


class TestBetaSubj:
    # top seal capillary: min 20, mode 200, mean 250, max 618.
    CASE = (20.0, 200.0, 250.0, 618.0)

    def test_recovers_the_elicited_mean(self):
        a1, a2 = dists.beta_subj_params(*self.CASE)
        lo, mode, mean, hi = self.CASE
        assert lo + (hi - lo) * a1 / (a1 + a2) == pytest.approx(mean)

    def test_recovers_the_elicited_mode(self):
        a1, a2 = dists.beta_subj_params(*self.CASE)
        lo, mode, _, hi = self.CASE
        assert a1 > 1 and a2 > 1, "an interior mode needs both shapes above 1"
        assert lo + (hi - lo) * (a1 - 1) / (a1 + a2 - 2) == pytest.approx(mode)

    def test_samples_stay_on_the_support(self):
        x = dists.beta_subj(rng(), *self.CASE, 50_000)
        assert x.min() >= self.CASE[0]
        assert x.max() <= self.CASE[3]

    def test_sample_mean_matches(self):
        x = dists.beta_subj(rng(), *self.CASE, 200_000)
        assert x.mean() == pytest.approx(self.CASE[2], rel=0.01)

    def test_the_stats_compare_failure_is_reported_not_silent(self):
        # RiskBetaSubj(20, 800, 700, h) with h = 350.
        # Excel shows #VALUE!; we want a sentence saying why.
        with pytest.raises(ValueError, match="must lie within"):
            dists.beta_subj_params(20.0, 800.0, 700.0, 350.0)

    def test_mode_equal_to_mean_rejected(self):
        # Mode off-centre, so this exercises the mode == mean path rather than the midpoint one.
        with pytest.raises(ValueError, match="must differ"):
            dists.beta_subj_params(0.0, 3.0, 3.0, 10.0)


class TestBetaGeneral:
    def test_graham_underfilled_branch_is_negatively_skewed(self):
        # RiskBetaGeneral(5, 1, 20, h): mass piled at the spill.
        x = dists.beta_general(rng(), 5.0, 1.0, 20.0, 350.0, 100_000)
        assert x.mean() > (20.0 + 350.0) / 2
        assert np.median(x) > x.mean(), "a1 > a2 on this support means left-skewed"

    def test_rejects_a_degenerate_support(self):
        with pytest.raises(ValueError, match="must exceed"):
            dists.beta_general(rng(), 2.0, 2.0, 350.0, 350.0, 10)


class TestBernoulli:
    def test_frequency_matches_p(self):
        x = dists.bernoulli(rng(), 0.6, 200_000)
        assert x.mean() == pytest.approx(0.6, abs=0.005)

    def test_returns_a_mask(self):
        assert dists.bernoulli(rng(), 0.5, 10).dtype == np.bool_

    def test_certain_and_impossible_are_allowed(self):
        # p = 0 and p = 1 are real inputs: a mechanism this prospect does not have, and one that
        # is always present.
        assert not dists.bernoulli(rng(), 0.0, 1000).any()
        assert dists.bernoulli(rng(), 1.0, 1000).all()

    def test_out_of_range_rejected(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            dists.bernoulli(rng(), 1.5, 10)


class TestPert:
    def test_mode_dominates(self):
        x = dists.pert(rng(), 200.0, 250.0, 400.0, 100_000)
        assert x.mean() == pytest.approx((200.0 + 4 * 250.0 + 400.0) / 6.0, rel=0.01)


class TestBetaSubjSymmetricCase:
    """A symmetric four-point elicitation asks for a BetaSubj that does not exist."""

    def test_a_symmetric_four_point_elicitation_is_undetermined(self):
        with pytest.raises(ValueError, match="midpoint"):
            dists.beta_subj_params(330.0, 350.0, 350.0, 370.0)

    def test_a_midpoint_mode_is_undetermined_even_with_a_different_mean(self):
        """The numerator vanishes on the mode alone; moving the mean does not rescue it."""
        with pytest.raises(ValueError, match="midpoint"):
            dists.beta_subj_params(330.0, 350.0, 355.0, 370.0)

    def test_the_message_names_the_distribution_to_use_instead(self):
        with pytest.raises(ValueError, match="PERT"):
            dists.beta_subj_params(330.0, 350.0, 355.0, 370.0)

    def test_pert_handles_the_same_three_points(self):
        x = dists.pert(rng(), 330.0, 350.0, 370.0, 50_000)
        assert x.mean() == pytest.approx(350.0, abs=0.5)
        assert x.min() >= 330.0 and x.max() <= 370.0

    def test_an_off_centre_mode_still_works(self):
        a1, a2 = dists.beta_subj_params(330.0, 345.0, 350.0, 370.0)
        assert a1 > 0 and a2 > 0
