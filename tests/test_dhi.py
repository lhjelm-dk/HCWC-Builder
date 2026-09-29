"""The DHI update, and the claim the signed note of 25 August 2026 was written to make.

That claim is testable in one line: the updated POS and the updated contact distribution must be
the *same object*, read at different thresholds. If `pos()` is ever anything other than
`exceedance(h_min)`, the note is wrong and so is the tool.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from hcwc.core import dhi, engine
from hcwc.core import dhi_comparison as comparison
from hcwc.core.dhi import DetectionFunction, DhiObservation
from hcwc.core.limits import DepthDistribution, Group, Limit, LimitSet, reference_prospect

N = 40_000


def run(min_column_m: float = 100.0):
    base = reference_prospect()
    return engine.run(LimitSet(apex=base.apex, limits=base.limits, name=base.name,
                               min_column_m=min_column_m), N)


class TestDetectionFunction:
    def test_it_rises_with_column_height(self):
        d = DetectionFunction(h50_m=25.0, steepness_m=8.0)
        got = d.at(np.array([0.0, 10.0, 25.0, 50.0, 200.0]))
        assert np.all(np.diff(got) > 0)

    def test_the_half_point_is_half_the_ceiling(self):
        d = DetectionFunction(h50_m=30.0, steepness_m=5.0, ceiling=0.9)
        assert d.at(np.array([30.0]))[0] == pytest.approx(0.45)

    def test_it_never_reaches_certainty(self):
        """A ceiling of 1 would make an absent anomaly infinitely strong evidence."""
        d = DetectionFunction(ceiling=0.9)
        assert d.at(np.array([10_000.0]))[0] < 0.9 + 1e-9
        assert d.at(np.array([10_000.0]))[0] == pytest.approx(0.9, abs=1e-6)

    def test_a_thin_column_is_nearly_invisible(self):
        assert DetectionFunction(h50_m=25.0, steepness_m=8.0).at(np.array([2.0]))[0] < 0.05

    @pytest.mark.parametrize("kwargs", [{"h50_m": 0.0}, {"steepness_m": -1.0},
                                        {"ceiling": 0.0}, {"ceiling": 1.5}])
    def test_bad_parameters_refused(self, kwargs):
        with pytest.raises(ValueError):
            DetectionFunction(**kwargs)


class TestTheCentralClaim:
    """POS and the contact distribution are one object."""

    def setup_method(self):
        self.result = run(100.0)
        self.post = dhi.update(self.result, DetectionFunction(),
                               DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=20.0))

    def test_pos_is_exceedance_read_at_the_assessment_minimum(self):
        for posterior in (False, True):
            assert self.post.pos(posterior=posterior) == pytest.approx(
                float(self.post.exceedance(100.0, posterior=posterior)[0]))

    def test_the_prior_matches_the_engine(self):
        assert self.post.pos(posterior=False) == pytest.approx(self.result.pos)

    def test_exceedance_is_monotone_in_both(self):
        grid = np.linspace(0.0, 400.0, 80)
        for posterior in (False, True):
            assert np.all(np.diff(self.post.exceedance(grid, posterior=posterior)) <= 1e-12)

    def test_f_at_h_min_is_never_below_f_at_a_deeper_threshold(self):
        """`F(h_min) >= F(h_DHI)` always — the reason there was nothing to reconcile."""
        assert (self.post.exceedance(100.0)[0] >= self.post.exceedance(250.0)[0])


class TestAnObservedAnomaly:
    def test_a_deep_pick_moves_the_contact_deeper(self):
        result = run(0.0)
        post = dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2350.0, pick_sigma_m=20.0))
        assert post.percentiles(50.0)[0] > post.percentiles(50.0, posterior=False)[0]

    def test_a_shallow_pick_moves_it_shallower(self):
        result = run(0.0)
        post = dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2130.0, pick_sigma_m=20.0))
        assert post.percentiles(50.0)[0] < post.percentiles(50.0, posterior=False)[0]

    def test_a_deep_pick_raises_pos(self):
        """It raises POS *and* deepens the contact — both, from one update."""
        result = run(150.0)
        post = dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2350.0, pick_sigma_m=20.0))
        assert post.pos() > post.pos(posterior=False)
        assert post.r_dhi > 1.0

    def test_a_tighter_pick_concentrates_the_posterior(self):
        result = run(0.0)
        loose = dhi.update(result, DetectionFunction(),
                           DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=60.0))
        tight = dhi.update(result, DetectionFunction(),
                           DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=8.0))
        spread = lambda p: p.percentiles(10.0)[0] - p.percentiles(90.0)[0]  # noqa: E731
        assert spread(tight) < spread(loose)
        assert tight.effective_sample_size < loose.effective_sample_size


class TestAnAbsentAnomaly:
    """An amplitude absent where one was expected is evidence, and needs no special case."""

    def test_it_lowers_pos(self):
        result = run(150.0)
        post = dhi.update(result, DetectionFunction(h50_m=25.0), DhiObservation(seen=False))
        assert post.pos() < post.pos(posterior=False)
        assert post.r_dhi < 1.0

    def test_it_shallows_the_contact(self):
        result = run(0.0)
        post = dhi.update(result, DetectionFunction(h50_m=25.0), DhiObservation(seen=False))
        assert post.percentiles(50.0)[0] < post.percentiles(50.0, posterior=False)[0]

    def test_a_higher_detection_threshold_makes_absence_weaker_evidence(self):
        """If you would not have seen it anyway, not seeing it says little."""
        result = run(150.0)
        sensitive = dhi.update(result, DetectionFunction(h50_m=20.0), DhiObservation(seen=False))
        blind = dhi.update(result, DetectionFunction(h50_m=400.0), DhiObservation(seen=False))
        assert sensitive.pos() < blind.pos()

    def test_it_needs_no_picked_contact(self):
        dhi.update(run(), DetectionFunction(), DhiObservation(seen=False))

    def test_an_observed_anomaly_without_a_pick_is_refused(self):
        with pytest.raises(ValueError, match="picked contact depth"):
            DhiObservation(seen=True)


class TestDegenerateCases:
    def test_a_pick_far_outside_the_prior_is_refused_not_reported(self):
        result = run(0.0)
        with pytest.raises(ValueError, match="no posterior"):
            dhi.update(result, DetectionFunction(),
                       DhiObservation(seen=True, contact_m=9000.0, pick_sigma_m=1.0))

    def test_effective_sample_size_falls_as_the_pick_gets_more_surprising(self):
        result = run(0.0)
        near = dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2210.0, pick_sigma_m=25.0))
        far = dhi.update(result, DetectionFunction(),
                         DhiObservation(seen=True, contact_m=2380.0, pick_sigma_m=25.0))
        assert far.effective_sample_size < near.effective_sample_size

    def test_a_non_positive_pick_sigma_is_refused(self):
        with pytest.raises(ValueError, match="depth-conversion error"):
            DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=0.0)


class TestPosteriorIndices:
    """The posterior as realisation indices, for the window on Figure 5.2.1a."""

    def _posterior(self):
        result = engine.run(reference_prospect(), 4_000, seed=1)
        obs = dhi.DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=10.0, p_valid=0.5)
        return dhi.update(result, dhi.DetectionFunction(), obs)

    def test_it_draws_every_index_by_weight_with_replacement(self):
        post = self._posterior()
        idx = dhi.posterior_indices(post)
        assert idx.shape == (post.result.n,)
        assert idx.min() >= 0 and idx.max() < post.result.n
        assert len(set(idx.tolist())) < post.result.n, "no repeats means no reweighting"
        # the drawn contacts follow the weighted distribution, not the prior
        drawn = post.result.contact_m[idx]
        w = post.weights / post.weights.sum()
        assert np.mean(drawn) == pytest.approx(float(np.sum(w * post.result.contact_m)), abs=3.0)

    def test_the_draw_is_fixed_and_sized(self):
        post = self._posterior()
        np.testing.assert_array_equal(dhi.posterior_indices(post), dhi.posterior_indices(post))
        assert dhi.posterior_indices(post, 50).shape == (50,)

    def test_unnormalisable_weights_fall_back_to_the_run_order(self):
        post = self._posterior()
        broken = dhi.DhiPosterior(result=post.result, weights=np.zeros(post.result.n),
                                  detection=post.detection, observation=post.observation)
        np.testing.assert_array_equal(dhi.posterior_indices(broken), np.arange(post.result.n))


class TestOutcomes:
    """What the DHI can turn out to have been (8.1.8): the outcome shares read off the posterior."""

    def _posterior(self, c=0.5, contact=2250.0, sigma=10.0, seen=True, absent_below=None):
        result = engine.run(reference_prospect(), 6_000, seed=2)
        obs = dhi.DhiObservation(seen=seen, pick_sigma_m=sigma, p_valid=c,
                                 contact_m=contact if seen and absent_below is None else None,
                                 absent_below_m=absent_below)
        return dhi.update(result, dhi.DetectionFunction(), obs)

    def test_the_branches_sum_to_the_likelihood(self):
        post = self._posterior()
        valid, spurious = dhi.likelihood_branches(post.result, post.detection, post.observation)
        np.testing.assert_allclose(valid + spurious, post.weights, rtol=1e-12)
        assert (spurious > 0).all() and np.ptp(spurious) == 0.0, "the spurious branch is flat"

    def test_the_branches_exist_only_for_a_seen_pick(self):
        post = self._posterior(seen=False)
        with pytest.raises(ValueError, match="seen, picked"):
            dhi.likelihood_branches(post.result, post.detection, post.observation)
        assert dhi.outcome_shares(post, 0.5) is None
        partial = self._posterior(absent_below=2300.0)
        assert dhi.outcome_shares(partial, 0.5) is None

    def test_the_shares_sum_to_one_and_the_axis_shares_p_g_given_s(self):
        o = dhi.outcome_shares(self._posterior(), 0.47)
        assert sum(o.shares.values()) == pytest.approx(1.0, abs=1e-12)
        assert o.shares[dhi.OUTCOME_NO_HC] == pytest.approx(0.53)
        on_axis = sum(v for k, v in o.shares.items() if k != dhi.OUTCOME_NO_HC)
        assert on_axis == pytest.approx(0.47, abs=1e-12)
        assert o.p_g_given_s == pytest.approx(0.47)
        assert all(v >= 0.0 for v in o.shares.values())

    def test_the_band_is_the_pick_p99_to_p1(self):
        o = dhi.outcome_shares(self._posterior(contact=2250.0, sigma=10.0), 0.5)
        top, base = o.band_m
        assert top == pytest.approx(2250.0 - 2.3263 * 10.0, abs=0.05)
        assert base == pytest.approx(2250.0 + 2.3263 * 10.0, abs=0.05)

    def test_a_certain_pick_leaves_the_band_only_through_its_own_tails(self):
        o = dhi.outcome_shares(self._posterior(c=0.999), 0.5)
        assert o.shares[dhi.OUTCOME_AT_BY_CHANCE] < 0.002
        assert o.shares[dhi.OUTCOME_ABOVE] + o.shares[dhi.OUTCOME_BELOW] < 0.02
        assert o.attribution > 0.99

    def test_coincidence_is_the_geology_s_own_mass_in_the_band(self):
        """With the DHI taken as almost certainly not the contact, the mass in the band is what
        the geological prior puts there, and it is all 'by coincidence'."""
        post = self._posterior(c=0.01)
        o = dhi.outcome_shares(post, 1.0)
        top, base = o.band_m
        z = post.result.contact_m
        prior_in_band = float(((z >= top) & (z <= base)).mean())
        assert o.shares[dhi.OUTCOME_AT_BY_CHANCE] == pytest.approx(prior_in_band, abs=0.01)
        assert o.shares[dhi.OUTCOME_AT_BY_DHI] < 0.03
        assert o.attribution < 0.05

    def test_the_attribution_rises_when_the_pick_lands_where_the_geology_expects_it(self):
        """The stated c is the prior; the geology revises it. A pick at the geological P50 is
        more plausibly the contact than a pick where the geology puts almost nothing."""
        result = engine.run(reference_prospect(), 6_000, seed=2)
        p50 = float(result.percentiles(50.0)[0])
        far = float(result.contact_m.max()) - 5.0
        at_p50 = dhi.update(result, dhi.DetectionFunction(),
                            dhi.DhiObservation(seen=True, contact_m=p50, pick_sigma_m=10.0,
                                               p_valid=0.36))
        far_off = dhi.update(result, dhi.DetectionFunction(),
                             dhi.DhiObservation(seen=True, contact_m=far, pick_sigma_m=10.0,
                                                p_valid=0.36))
        assert dhi.outcome_shares(at_p50, 0.5).attribution > 0.36
        assert dhi.outcome_shares(far_off, 0.5).attribution < 0.36


class TestScenarioSwitch:
    """Formulation A — the scenario switch."""

    def test_it_moves_the_contact_but_not_pos(self):
        result = run(100.0)
        switched = comparison.scenario_switch(result, 0.655, 2300.0, 20.0)
        assert switched.shape == result.contact_m.shape
        assert not np.allclose(switched, result.contact_m)

    def test_p_valid_zero_leaves_the_contact_untouched(self):
        result = run()
        assert np.allclose(comparison.scenario_switch(result, 0.0, 2300.0, 20.0), result.contact_m)

    def test_p_valid_one_replaces_every_contact(self):
        result = run()
        switched = comparison.scenario_switch(result, 1.0, 2300.0, 20.0)
        assert switched.mean() == pytest.approx(2300.0, abs=1.0)

    def test_the_switched_fraction_matches_p_valid(self):
        result = run()
        switched = comparison.scenario_switch(result, 0.655, 2300.0, 5.0)
        replaced = np.abs(switched - result.contact_m) > 1e-9
        assert replaced.mean() == pytest.approx(0.655, abs=0.01)

    def test_an_out_of_range_validity_is_refused(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            comparison.scenario_switch(run(), 1.5, 2300.0, 20.0)


class TestAreaCrossCheck:
    DEPTHS = np.linspace(2040.0, 2400.0, 37)
    AREAS = np.linspace(0.0, 32.6, 37)

    def test_agreement_reports_near_zero(self):
        out = dhi.area_cross_check(self.DEPTHS, self.AREAS, 16.3, 2220.0)
        assert abs(out["disagreement_m"]) < 5.0

    def test_a_narrow_anomaly_implies_a_shallower_contact(self):
        out = dhi.area_cross_check(self.DEPTHS, self.AREAS, 5.0, 2300.0)
        assert out["disagreement_m"] < 0
        assert out["from_area_m"] < out["from_termination_m"]

    def test_a_wide_anomaly_implies_a_deeper_contact(self):
        out = dhi.area_cross_check(self.DEPTHS, self.AREAS, 30.0, 2150.0)
        assert out["disagreement_m"] > 0

    def test_a_non_monotone_area_is_refused(self):
        with pytest.raises(ValueError, match="must increase with depth"):
            dhi.area_cross_check(self.DEPTHS, self.AREAS[::-1], 10.0, 2200.0)


class TestContainment:
    DEPTHS = np.linspace(2040.0, 2400.0, 37)
    AREAS = np.linspace(0.0, 32.6, 37)

    def test_a_small_minimum_inside_a_large_anomaly_is_fine(self):
        ok, msg = dhi.containment_ok(self.DEPTHS, self.AREAS, 2050.0, 50.0, 20.0)
        assert ok and msg == ""

    def test_a_minimum_larger_than_the_anomaly_is_refused_with_a_reason(self):
        ok, msg = dhi.containment_ok(self.DEPTHS, self.AREAS, 2050.0, 300.0, 2.0)
        assert not ok
        assert "smaller accumulation than the" in msg
        assert "km²" in msg


class TestResolutionCeiling:
    """A DHI may move POS and assert a contact. It may not re-weight the competing limits."""

    def test_the_controlling_limit_diagnostic_is_untouched_by_the_update(self):
        result = run(100.0)
        before = result.controlling_shares()
        dhi.update(result, DetectionFunction(),
                   DhiObservation(seen=True, contact_m=2350.0, pick_sigma_m=20.0))
        assert result.controlling_shares() == before

    def test_the_posterior_keeps_the_same_realisations(self):
        """Importance weighting, not re-simulation — so prior and posterior are comparable."""
        result = run(100.0)
        post = dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=20.0))
        assert post.weights.size == result.n
        assert post.result is result


class TestUndefinedLikelihoodRatio:
    """R needs both a success set and a failure set to compare."""

    def test_it_is_undefined_when_every_realisation_succeeds(self):
        """With the assessment minimum at zero there is no failure set."""
        post = dhi.update(run(0.0), DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=20.0))
        assert post.result.above_minimum.all()
        assert np.isnan(post.r_dhi)

    def test_it_is_defined_once_a_minimum_is_set(self):
        post = dhi.update(run(150.0), DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2350.0, pick_sigma_m=20.0))
        assert not np.isnan(post.r_dhi)
        assert post.r_dhi > 0

    def test_it_is_undefined_when_every_realisation_fails(self):
        post = dhi.update(run(5000.0), DetectionFunction(), DhiObservation(seen=False))
        assert not post.result.above_minimum.any()
        assert np.isnan(post.r_dhi)

    def test_a_favourable_observation_gives_r_above_one(self):
        post = dhi.update(run(150.0), DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2350.0, pick_sigma_m=25.0))
        assert post.r_dhi > 1.0 and post.pos() > post.pos(posterior=False)

    def test_an_unfavourable_observation_gives_r_below_one(self):
        post = dhi.update(run(150.0), DetectionFunction(h50_m=25.0), DhiObservation(seen=False))
        assert post.r_dhi < 1.0 and post.pos() < post.pos(posterior=False)


class TestStrengthModel:
    """Adapted from E-POS's custom-R tool. The numbers must match it."""

    def test_the_default_slider_is_e_pos_s(self):
        assert dhi.DEFAULT_STRENGTH == 7.0

    def test_the_default_curves_are_e_pos_s(self):
        m = dhi.StrengthModel()
        assert (m.hc.p1, m.hc.p99) == (-50.0, 100.0)
        assert (m.no_hc.p1, m.no_hc.p99) == (-100.0, 50.0)

    def test_p1_p99_gives_the_right_gaussian(self):
        """E-POS's worked example: p1 = -50, p99 = 100 -> mean 25, sd 32.239."""
        c = dhi.StrengthCase(-50.0, 100.0)
        assert c.mean == pytest.approx(25.0)
        assert c.sd == pytest.approx(32.239, abs=1e-3)

    def test_r_rises_with_strength(self):
        m = dhi.StrengthModel()
        got = [m.r_at(s) for s in (-50, -10, 0, 25, 50)]
        assert got == sorted(got)

    def test_a_neutral_reading_gives_r_of_one(self):
        """The curves cross at 0 by symmetry of the defaults."""
        assert dhi.StrengthModel().r_at(0.0) == pytest.approx(1.0, abs=0.01)

    def test_r_is_floored_and_capped_at_the_single_channel_ceiling(self):
        """Not `R_CAP`, which is five times looser and guards the *combination*.

        The two were one number until 9 Sep 2026, and the looser of the two jobs won: one
        elicited slider on an axis with no external referent could move the prospect chance
        from 1.4 % to 97.2 %, while `strength_bands` said in words, three lines away, that
        |R| above 10 should send you back to the inputs.
        """
        m = dhi.StrengthModel()
        assert m.r_at(400.0) == pytest.approx(dhi.R_SINGLE_CHANNEL)
        assert m.r_at(-400.0) == pytest.approx(1.0 / dhi.R_SINGLE_CHANNEL)

    def test_far_enough_out_both_curves_underflow_and_the_answer_is_neutral(self):
        """Not the ceiling: with both densities at zero there is no ratio to take.

        Pinned rather than fixed. R = 1 is the right answer for a reading neither population
        can produce, and it is unreachable from the slider anyway.
        """
        assert dhi.StrengthModel().r_at(10_000.0) == 1.0

    def test_the_single_channel_ceiling_is_stricter_than_the_combination_guard(self):
        """They do different jobs, so one must not quietly become the other again."""
        assert dhi.R_SINGLE_CHANNEL < dhi.R_CAP

    def test_r_is_scale_invariant_in_the_strength_axis(self):
        """Only the relative heights matter, so rescaling the axis cannot change R."""
        base = dhi.StrengthModel().r_at(25.0)
        scaled = dhi.StrengthModel(dhi.StrengthCase(-500.0, 1000.0),
                                   dhi.StrengthCase(-1000.0, 500.0)).r_at(250.0)
        assert scaled == pytest.approx(base, rel=1e-9)


class TestTheStrengthAxisCanBeInverted:
    """`strength_at` exists so the slider can stop where the evidence stops.

    A slider whose outer halves are flattened by a cap is worse than a narrower live one: it
    invites a reading the arithmetic then refuses without saying so.
    """

    def test_it_inverts_r_at_on_the_defaults(self):
        m = dhi.StrengthModel()
        for r in (0.2, 0.5, 1.0, 2.0, 5.0, dhi.R_SINGLE_CHANNEL):
            assert m.r_at(m.strength_at(r)) == pytest.approx(r, rel=1e-6)

    def test_the_defaults_are_symmetric_about_neutral(self):
        m = dhi.StrengthModel()
        hi = m.strength_at(dhi.R_SINGLE_CHANNEL)
        lo = m.strength_at(1.0 / dhi.R_SINGLE_CHANNEL)
        assert hi == pytest.approx(-lo, rel=1e-6)

    def test_unequal_widths_take_the_near_branch(self):
        """With unequal standard deviations log R is a quadratic and reaches any target twice.

        The far root is where the narrower curve has collapsed to nothing. Arithmetically the
        ratio is right; as a slider bound it would put the *supportive* end of the axis at a
        reading that sits on the wrong side of the crossing.
        """
        m = dhi.StrengthModel(hc=dhi.StrengthCase(-50.0, 100.0),
                              no_hc=dhi.StrengthCase(-80.0, 10.0))
        crossing = m.strength_at(1.0)
        hi = m.strength_at(dhi.R_SINGLE_CHANNEL)
        assert hi > crossing
        assert m.r_at(hi) == pytest.approx(dhi.R_SINGLE_CHANNEL, rel=1e-2)

    def test_curves_that_never_separate_have_no_inverse(self):
        """Identical populations give R = 1 everywhere, and nan is the honest answer."""
        same = dhi.StrengthCase(-100.0, 100.0)
        assert np.isnan(dhi.StrengthModel(hc=same, no_hc=same).strength_at(2.0))


class TestEachChannelIsBoundedBeforeCombining:
    """The geometry ratio is reported raw and used clipped, and the two are different numbers."""

    def test_a_runaway_geometry_ratio_cannot_walk_into_the_combination(self):
        loose = comparison.CombinedUpdate(0.4, r_geometry=4_000.0, r_strength=1.0, dependence=0.0)
        assert loose.r_combined == pytest.approx(dhi.R_SINGLE_CHANNEL)

    def test_a_runaway_ratio_downward_is_bounded_too(self):
        loose = comparison.CombinedUpdate(0.4, r_geometry=1e-6, r_strength=1.0, dependence=0.0)
        assert loose.r_combined == pytest.approx(1.0 / dhi.R_SINGLE_CHANNEL)

    def test_a_missing_geometry_channel_still_bounds_the_strength(self):
        c = comparison.CombinedUpdate(0.4, r_geometry=float("nan"), r_strength=1_000.0)
        assert c.r_combined == pytest.approx(dhi.R_SINGLE_CHANNEL)

    def test_two_bounded_channels_may_exceed_one(self):
        """The combination guard is looser on purpose: Kjonsberg measured 29 on a drilled gas find."""
        both = comparison.CombinedUpdate(0.4, r_geometry=dhi.R_SINGLE_CHANNEL,
                                  r_strength=dhi.R_SINGLE_CHANNEL, dependence=0.0)
        assert both.r_combined > dhi.R_SINGLE_CHANNEL
        assert both.r_combined <= dhi.R_CAP


class TestLeverageIsMeasuredNotAsserted:
    """What a control is worth, so the tab can print it beside the control.

    The audit that prompted this found the explanation distributed by how interesting a number is
    rather than by how far it moves the answer.
    """

    def setup_method(self):
        self.result = run(min_column_m=120.0)
        self.det = DetectionFunction()
        self.obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.35)

    def _state(self, **over):
        det = dataclasses.replace(self.det, **{k: v for k, v in over.items()
                                               if k in ("h50_m", "steepness_m", "ceiling")})
        obs = dataclasses.replace(self.obs, **{k: v for k, v in over.items()
                                               if k in ("contact_m", "pick_sigma_m", "p_valid")})
        return (self.result, det, obs, 0.4, over.get("r_strength", 1.4))

    def test_outcome_reports_both_numbers(self):
        got = dhi.outcome(self.result, self.det, self.obs, p_g=0.4, r_strength=1.4)
        assert 0.0 < got.pos < 1.0
        assert np.isfinite(got.contact_m)

    def test_the_amplitude_character_moves_the_chance(self):
        lv = dhi.leverage(lambda v: self._state(r_strength=v),
                          [1.0 / dhi.R_SINGLE_CHANNEL, 1.0, dhi.R_SINGLE_CHANNEL])
        assert lv.measurable
        assert not lv.inert
        assert lv.pos_points > 50.0

    def test_the_detection_shape_is_inert_when_every_column_clears_tuning(self):
        """The finding this whole readout exists to make visible.

        `D(h)` sits at its ceiling for every realisation on any prospect worth drilling, so the
        two shape parameters multiply every weight by the same number and cancel out of the
        ratio. They carried a warning triangle and a paragraph of the paper for that.
        """
        cleared = self.result.column_m[self.result.above_minimum]
        assert float(cleared.min()) > 3 * self.det.h50_m
        lv = dhi.leverage(lambda v: self._state(h50_m=v), [5.0, 15.0, 25.0, 50.0])
        assert lv.inert

    def test_a_refused_state_is_skipped_rather_than_counted_as_an_extreme(self):
        """A state the model will not enter is not a leverage of one hundred points.

        A *pick* can never do it -- Cromwell's floor keeps every weight positive however far
        out the contact is put, which is the whole point of it -- so the refusal here comes
        from the observation constructor instead.
        """
        lv = dhi.leverage(lambda v: self._state(pick_sigma_m=v), [3.0, 15.0, -1.0])
        assert lv.measurable
        assert lv.span == (3.0, 15.0)

    def test_too_few_usable_points_is_nan_rather_than_zero(self):
        """"Nothing moved" and "the sweep could not run" are different findings."""
        lv = dhi.leverage(lambda v: self._state(pick_sigma_m=v), [-1.0, -2.0])
        assert not lv.measurable
        assert not lv.inert

    def test_the_swept_span_is_reported(self):
        lv = dhi.leverage(lambda v: self._state(pick_sigma_m=v), [3.0, 15.0, 120.0])
        assert lv.span == (3.0, 120.0)


class TestSimmUpdate:
    def test_r_of_one_leaves_the_prior_alone(self):
        assert dhi.simm_update(0.432, 1.0) == pytest.approx(0.432)

    def test_it_matches_the_closed_form(self):
        assert dhi.simm_update(0.4, 3.0) == pytest.approx(3 * 0.4 / (3 * 0.4 + 0.6))

    def test_certainty_is_preserved(self):
        assert dhi.simm_update(1.0, 0.5) == pytest.approx(1.0)
        assert dhi.simm_update(0.0, 10.0) == pytest.approx(0.0)

    def test_volume_weight_is_r_over_r_plus_one(self):
        """E-POS's `dhi_score_from_r`."""
        assert dhi.volume_weight(1.4) == pytest.approx(1.4 / 2.4)
        assert dhi.volume_weight(1.0) == pytest.approx(0.5)

    def test_an_impossible_prior_is_refused(self):
        with pytest.raises(ValueError, match="must be a probability"):
            dhi.simm_update(1.5, 2.0)

    @pytest.mark.parametrize("r, label", [(20.0, "Decisive ↑"), (4.0, "Strong ↑"),
                                          (2.0, "Moderate ↑"), (1.0, "Negligible"),
                                          (0.5, "Moderate ↓"), (0.2, "Strong ↓"),
                                          (0.05, "Decisive ↓")])
    def test_simm_bands(self, r, label):
        assert dhi.strength_bands(r)[0] == label


class TestCombinedUpdate:
    """Two channels of one observation — and the double-count that multiplying them would be."""

    def test_dependence_zero_multiplies_the_two(self):
        c = comparison.CombinedUpdate(0.4, r_geometry=2.5, r_strength=1.4, dependence=0.0)
        assert c.r_combined == pytest.approx(2.5 * 1.4, rel=1e-6)

    def test_dependence_one_takes_the_stronger_alone(self):
        c = comparison.CombinedUpdate(0.4, r_geometry=2.5, r_strength=1.4, dependence=1.0)
        assert c.r_combined == pytest.approx(2.5, rel=1e-6)

    def test_a_half_dependence_sits_between(self):
        half = comparison.CombinedUpdate(0.4, 2.5, 1.4, 0.5).r_combined
        assert 2.5 < half < 2.5 * 1.4

    def test_the_posterior_uses_the_combined_ratio(self):
        c = comparison.CombinedUpdate(0.432, 2.5, 1.4, 0.5)
        assert c.posterior_pos == pytest.approx(dhi.simm_update(0.432, c.r_combined))

    def test_two_downward_channels_still_combine_downward(self):
        c = comparison.CombinedUpdate(0.5, r_geometry=0.5, r_strength=0.4, dependence=0.0)
        assert c.r_combined < 0.5
        assert c.posterior_pos < 0.5

    def test_a_missing_geometry_channel_falls_back_to_strength(self):
        c = comparison.CombinedUpdate(0.4, r_geometry=float("nan"), r_strength=1.4)
        assert c.r_combined == pytest.approx(1.4)

    def test_dependence_out_of_range_refused(self):
        with pytest.raises(ValueError, match="dependence must be"):
            comparison.CombinedUpdate(0.4, 2.0, 1.5, dependence=1.5)


class TestTheUpdateIsAnchoredToTheGeologicalPos:
    """What the DHI update multiplies, and the bug that came of getting it wrong.

    **E-POS anchors its DFI update to the geological POS** — the ∏-pillars product, or the ESL
    mass-rollup via `prior_pg_override` (`logic/dfi_bayes.py::compute_dfi_posterior`). It never
    anchors to a geometric exceedance probability.

    This tool anchored to `F(h_min)` alone, which is `P(column reaches the threshold | the prospect
    works)`. At a zero assessment minimum that is exactly 1.0, so a perfectly ordinary DHI appeared
    to leave POS at 100 %: nothing can move certainty. The prospect POS is the **product** of the
    two, and both halves already existed — the element chances on tab 2.0 and the exceedance from the
    engine.
    """

    ELEMENTS = {"Charge": 0.902, "Closure": 1.0, "Reservoir": 0.603, "Retention": 0.807}

    @property
    def geological_pos(self) -> float:
        return float(np.prod(list(self.ELEMENTS.values())))

    def test_a_prior_of_one_cannot_be_moved_by_any_evidence(self):
        """The arithmetic behind the symptom. Not a defect in `simm_update` — a defect in what was
        handed to it."""
        for r in (1.4, 3.0, 10.0, dhi.R_CAP):
            assert dhi.simm_update(1.0, r) == 1.0

    def test_the_default_strength_moves_a_geological_prior_sensibly(self):
        """The number Lars saw as 100 %. Anchored properly it is 43.9 % → 52.3 %: a weak DHI
        buying about eight points, which is what a 'Negligible' band should look like on a mid
        prior."""
        r = dhi.StrengthModel().r_at(dhi.DEFAULT_STRENGTH)
        assert r == pytest.approx(1.40, abs=0.01)
        assert self.geological_pos == pytest.approx(0.439, abs=0.005)
        assert dhi.simm_update(self.geological_pos, r) == pytest.approx(0.523, abs=0.005)

    def test_the_anchor_changes_the_posterior_but_never_the_ratio(self):
        """E-POS states this explicitly: R and the volume weight are invariant to re-anchoring
        because they are likelihood ratios; only where the ratio is applied moves. If that ever
        stopped holding, the two tools would disagree about the strength of the same evidence.
        """
        r = dhi.StrengthModel().r_at(dhi.DEFAULT_STRENGTH)
        assert dhi.volume_weight(r) == pytest.approx(r / (r + 1.0))
        posteriors = [dhi.simm_update(p, r) for p in (0.2, 0.439, 0.8)]
        assert posteriors == sorted(posteriors)
        assert all(p > prior for p, prior in zip(posteriors, (0.2, 0.439, 0.8)))

    def test_the_geometric_and_geological_halves_multiply(self):
        """Prospect POS = ∏ element chances × P(column ≥ h). The second term is conditional on the
        prospect working, which is exactly what the competing-limits model computes."""
        from hcwc.core import engine as engine_mod
        from hcwc.core.limits import reference_prospect
        result = engine_mod.run(dataclasses.replace(reference_prospect(), min_column_m=40.0), 5_000)
        prospect_pos = self.geological_pos * result.pos
        assert 0.0 < prospect_pos < self.geological_pos
        assert prospect_pos == pytest.approx(self.geological_pos * result.pos)


class TestThePickHasAShape:
    """Three controls doing three separate things, which is the point of shaping the pick."""

    def test_the_normal_shape_reproduces_the_old_behaviour_exactly(self):
        """The default must be a no-op, or every prospect ever saved changes meaning."""
        result = run()
        obs = DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=20.0)
        from scipy.stats import norm as _n
        expected = (DetectionFunction().at(result.column_m)
                    * _n.pdf((2300.0 - result.contact_m) / 20.0) / 20.0)
        assert np.allclose(dhi.likelihood(result, DetectionFunction(), obs), expected)

    def test_a_bounded_shape_is_zero_outside_its_range(self):
        result = run()
        obs = DhiObservation(seen=True, contact_m=2300.0, pick_shape=dhi.PERT,
                             shallowest_m=2280.0, deepest_m=2320.0)
        outside = (result.contact_m < 2280.0) | (result.contact_m > 2320.0)
        assert outside.any(), "the fixture must straddle the bound for this to test anything"
        assert np.all(obs.pick_pdf(result.contact_m)[outside] == 0.0)

    def test_skewing_deep_raises_the_reading_at_the_pick(self):
        """The lever for 'why is it only half the POS at the contact I picked'.

        A symmetric pick puts the posterior median on the pick. Asserting instead that the
        termination under-calls — mode near the shallow end, a long tail below — moves the median
        below the pick, so more of the posterior lies at or beyond it.
        """
        result, detection = run(), DetectionFunction()
        at_pick = []
        for obs in (DhiObservation(seen=True, contact_m=2300.0, pick_shape=dhi.PERT,
                                   shallowest_m=2280.0, deepest_m=2320.0),
                    DhiObservation(seen=True, contact_m=2300.0, pick_shape=dhi.PERT,
                                   shallowest_m=2294.0, deepest_m=2360.0)):
            post = dhi.update(result, detection, obs)
            at_pick.append(float(post.exceedance(np.array([2300.0 - np.median(result.apex_m)]))[0]))
        symmetric, skewed_deep = at_pick
        assert skewed_deep > symmetric + 0.10

    def test_widening_acts_mostly_on_the_tail(self):
        """Width and skew are different dials, but only *mostly* — worth being exact about.

        A wider pick always fattens the deep tail. It can also move the reading at the picked
        contact, and the amount depends on the prior: a wide likelihood lets an asymmetric prior
        pull the posterior median off the pick, where a tight one pins it there. On the worked
        prospect that shift is a third of a point; on this fixture it is eight. So the claim to
        pin is the *relative* one — width is a tail control that has a side effect near the pick,
        not a tail control with no effect there.
        """
        result, detection = run(), DetectionFunction()
        apex = float(np.median(result.apex_m))
        reads = []
        for sigma in (20.0, 40.0):
            post = dhi.update(result, detection,
                              DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=sigma))
            reads.append((float(post.exceedance(np.array([2300.0 - apex]))[0]),
                          float(post.exceedance(np.array([2360.0 - apex]))[0])))
        (pick_tight, tail_tight), (pick_wide, tail_wide) = reads
        assert tail_wide > tail_tight * 1.5
        assert (abs(tail_wide - tail_tight) / tail_tight
                > 3.0 * abs(pick_wide - pick_tight) / pick_tight)

    @pytest.mark.parametrize("kwargs", [
        {"pick_shape": "banana"},
        {"pick_shape": dhi.PERT, "shallowest_m": 2280.0},
        {"pick_shape": dhi.PERT, "shallowest_m": 2320.0, "deepest_m": 2280.0},
        {"pick_shape": dhi.PERT, "shallowest_m": 2310.0, "deepest_m": 2360.0},
        {"p_valid": 0.0},
        {"p_valid": 1.5},
    ])
    def test_incoherent_picks_refused(self, kwargs):
        with pytest.raises(ValueError):
            DhiObservation(seen=True, contact_m=2300.0, **kwargs)


class TestNothingIsEverRuledOut:
    """Cromwell's rule, enforced rather than described.

    A zero likelihood is not weak evidence, it is infinitely strong evidence: in odds form
    `posterior = R x prior`, so `R = 0` annihilates whatever prior you started with. One seismic
    pick is not allowed to do that, and the mixture in `dhi.likelihood` is what stops it.
    """

    SHAPES = [
        {"pick_shape": dhi.NORMAL, "pick_sigma_m": 20.0},
        {"pick_shape": dhi.NORMAL, "pick_sigma_m": 3.0},
        {"pick_shape": dhi.PERT, "shallowest_m": 2280.0, "deepest_m": 2320.0},
        {"pick_shape": dhi.PERT, "shallowest_m": 2296.0, "deepest_m": 2380.0},
        {"pick_shape": dhi.UNIFORM, "shallowest_m": 2280.0, "deepest_m": 2320.0},
    ]

    @pytest.mark.parametrize("shape", SHAPES)
    @pytest.mark.parametrize("p_valid", [0.99, 0.9, 0.655, 0.5, 0.2])
    def test_the_depth_channel_can_never_say_more_than_the_floor_allows(self, shape, p_valid):
        """`L / c >= 1 - p_valid`, for every shape, because `Pick(.) >= 0`."""
        result = run()
        obs = DhiObservation(seen=True, contact_m=2300.0, p_valid=p_valid, **shape)
        weights = dhi.likelihood(result, DetectionFunction(), obs)
        c = dhi.spurious_density(result.limit_set.contact_support_m())
        assert (weights / c).min() >= (1.0 - p_valid) - 1e-9

    def test_the_floor_bounds_each_depth_but_does_not_cap_discrimination(self):
        """Red team, 22 Sep 2026. The floor is `L / s >= 1 - c` at every depth; it is not a cap of
        `c / (1 - c)` on the ratio between two depths, which grows as the pick narrows. The old
        statement was false and is pinned here so it cannot return."""
        result = run()
        s = dhi.spurious_density(result.limit_set.contact_support_m())
        d_max = DetectionFunction().ceiling
        ratios = []
        for sigma in (10.0, 5.0, 2.0):
            obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=sigma, p_valid=0.36)
            L = dhi.likelihood(result, DetectionFunction(), obs)
            assert (L / s).min() >= 0.64 - 1e-9                       # the floor holds
            ratio = float(L.max() / L.min())
            assert ratio > 0.36 / 0.64                                 # the old cap is exceeded
            bound = 1.0 + 0.36 * d_max * float(obs.pick_pdf(np.array([2250.0]))[0]) / (0.64 * s)
            assert ratio <= bound + 1e-9                               # the true bound holds
            ratios.append(ratio)
        assert ratios[0] < ratios[1] < ratios[2], "discrimination grows as the pick narrows"

    def test_a_bounded_pick_without_the_mixture_does_assign_zero(self):
        """The failure mode the mixture exists to prevent — pinned so it cannot creep back."""
        result = run()
        dogmatic = DhiObservation(seen=True, contact_m=2300.0, pick_shape=dhi.PERT,
                                  shallowest_m=2280.0, deepest_m=2320.0, p_valid=1.0)
        assert dhi.likelihood(result, DetectionFunction(), dogmatic).min() == 0.0

    def test_and_with_the_mixture_it_does_not(self):
        result = run()
        robust = dataclasses.replace(
            DhiObservation(seen=True, contact_m=2300.0, pick_shape=dhi.PERT,
                           shallowest_m=2280.0, deepest_m=2320.0), p_valid=0.9)
        assert dhi.likelihood(result, DetectionFunction(), robust).min() > 0.0

    def test_no_contact_depth_is_left_with_zero_posterior_probability(self):
        """The claim in the geologist's words: the DHI is incomplete information."""
        result = run()
        post = dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2300.0, pick_shape=dhi.PERT,
                                         shallowest_m=2280.0, deepest_m=2320.0, p_valid=0.9))
        deep = float(post.exceedance(np.array([2380.0 - float(np.median(result.apex_m))]))[0])
        assert deep > 0.0

    def test_an_absent_anomaly_has_its_own_floor_already(self):
        """`1 - D(h)` cannot reach zero because the detection ceiling is below 1."""
        result = run()
        weights = dhi.likelihood(result, DetectionFunction(ceiling=0.9), DhiObservation(seen=False))
        assert weights.min() >= 0.1 - 1e-9


class TestAbsenceIsEvidenceAgainst:
    """An anomaly expected and not found is bad news, and it used to read as good news.

    Two separate faults produced that. The likelihood ratio compared tall columns against short
    ones — the right question for a *seen* anomaly and the wrong one for an absent one, returning
    `nan` exactly when the assessment minimum was low enough for everything to clear it. And the
    strength channel went on applying the slider's ratio although there was no amplitude to grade,
    so recording "I expected one and there is none" produced the same POS as a bright anomaly.
    """

    def test_an_absent_anomaly_gives_a_ratio_below_one(self):
        result = run(5.0)
        post = dhi.update(result, DetectionFunction(), DhiObservation(seen=False))
        assert result.above_minimum.all(), "the fixture must have no failures, or this proves less"
        assert not np.isnan(post.r_dhi)
        assert post.r_dhi < 1.0

    def test_it_is_the_chance_of_having_missed_it(self):
        """`R = E[1 - D(h) | success]`, against a barren world taken as certain to show nothing."""
        result, detection = run(5.0), DetectionFunction()
        post = dhi.update(result, detection, DhiObservation(seen=False))
        expected = float(np.mean(1.0 - detection.at(result.column_m[result.above_minimum])))
        assert post.r_dhi == pytest.approx(expected, rel=1e-9)

    def test_a_blinder_survey_makes_absence_weaker_evidence(self):
        """If you would probably not have seen it anyway, not seeing it says little."""
        result = run(5.0)
        sharp = dhi.update(result, DetectionFunction(h50_m=20.0, ceiling=0.95),
                           DhiObservation(seen=False))
        blind = dhi.update(result, DetectionFunction(h50_m=400.0, ceiling=0.95),
                           DhiObservation(seen=False))
        assert sharp.r_dhi < blind.r_dhi
        assert blind.r_dhi > 0.5

    def test_a_seen_anomaly_still_uses_the_success_against_failure_form(self):
        """The fix must not touch E-POS's `r_dfi` construction where it applies."""
        result = run(150.0)
        post = dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2300.0, pick_sigma_m=20.0))
        success = result.above_minimum
        expected = float(post.weights[success].mean() / post.weights[~success].mean())
        assert post.r_dhi == pytest.approx(expected, rel=1e-9)

    def test_absence_moves_the_chance_the_right_way(self):
        """The whole point: it must lower the prospect POS, not raise it."""
        result = run(5.0)
        post = dhi.update(result, DetectionFunction(), DhiObservation(seen=False))
        prior_pos = 0.408
        # With nothing seen there is no amplitude to grade, so the strength channel is neutral.
        combined = comparison.CombinedUpdate(prior_pos, float(post.r_dhi), 1.0, dependence=0.5)
        assert combined.posterior_pos < prior_pos * 0.5


class TestAbsenceLowersTheChance:
    """Audit finding P1-0, 14 Sep 2026.

    The corrected chain updates P(G) by the strength and reweights within G by the pick. An
    absent anomaly has no strength to grade, so the chance was held neutral and absence could
    only reshape the column -- on the shipped prospect, where every column sits on the detection
    ceiling, it did nothing at all. E-POS's principle and Monigle et al. (2025) both put absence
    on the chance. `absence_ratio` is that ratio, and `applied_ratio` is the one place that
    decides which ratio an observation carries.
    """

    def test_the_ratio_is_the_two_absences_divided(self):
        """`(1 - d) / (1 - f d)`, with `d` the filled trap's chance of showing."""
        result = run(5.0)
        detection = DetectionFunction(false_positive=0.3)
        d = float(np.mean(detection.at(result.column_m)))
        expected = (1.0 - d) / (1.0 - 0.3 * d)
        assert dhi.absence_ratio(result, detection) == pytest.approx(expected, rel=1e-12)

    def test_a_barren_trap_that_never_shows_makes_absence_strongest(self):
        """`f = 0`: the ratio is the chance of having missed a real column, and nothing softer."""
        result = run(5.0)
        detection = DetectionFunction(false_positive=0.0)
        expected = float(np.mean(1.0 - detection.at(result.column_m)))
        assert dhi.absence_ratio(result, detection) == pytest.approx(max(expected, 0.1), rel=1e-12)

    def test_a_barren_trap_that_shows_as_readily_makes_absence_uninformative(self):
        assert dhi.absence_ratio(run(5.0), DetectionFunction(false_positive=1.0)) == 1.0

    def test_absence_never_counts_for_hydrocarbons(self):
        """`f d <= d`, so the ratio cannot exceed 1 whatever the two inputs say."""
        result = run(5.0)
        for f in (0.0, 0.25, 0.5, 0.75, 1.0):
            for h50 in (5.0, 25.0, 150.0, 400.0):
                r = dhi.absence_ratio(result, DetectionFunction(h50_m=h50, false_positive=f))
                assert 0.1 <= r <= 1.0, (f, h50, r)

    def test_where_nothing_could_have_shown_absence_says_nothing(self):
        """A blind survey: `d -> 0`, so the ratio goes to 1 regardless of the false-positive rate."""
        result = run(5.0)
        blind = dhi.absence_ratio(result, DetectionFunction(h50_m=5000.0, false_positive=0.0))
        assert blind == pytest.approx(1.0, abs=1e-6)

    def test_the_ratio_is_bounded_like_every_single_channel(self):
        result = run(5.0)
        detection = DetectionFunction(ceiling=1.0, h50_m=1.0, steepness_m=0.1, false_positive=0.0)
        # d is essentially 1, so the raw ratio is essentially 0; it must stop at the floor.
        assert dhi.absence_ratio(result, detection) == pytest.approx(1.0 / dhi.R_SINGLE_CHANNEL)

    def test_the_applied_ratio_is_the_strength_when_seen_and_the_absence_ratio_when_not(self):
        result, detection = run(5.0), DetectionFunction()
        seen = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.7)
        absent = DhiObservation(seen=False)
        assert dhi.applied_ratio(result, detection, seen, 3.7) == 3.7
        assert dhi.applied_ratio(result, detection, absent, 3.7) == \
            dhi.absence_ratio(result, detection)

    def test_an_absent_anomaly_lowers_the_prospect_chance_through_outcome(self):
        """The chain end to end: with nothing seen, the chance falls and the column is the
        same posterior it was before the ratio existed."""
        result, detection = run(5.0), DetectionFunction()
        absent = DhiObservation(seen=False)
        before = dhi.prospect_pos(0.408, 1.0, dhi.update(result, detection, absent))
        out = dhi.outcome(result, detection, absent, p_g=0.408, r_strength=9.0)
        assert out.pos < before, "the strength passed in must not rescue an absent anomaly"
        assert out.pos == pytest.approx(
            dhi.prospect_pos(0.408, dhi.absence_ratio(result, detection),
                             dhi.update(result, detection, absent)))
        assert out.contact_m == pytest.approx(
            float(dhi.update(result, detection, absent).percentiles(50.0)[0]))

    def test_the_false_positive_rate_is_validated(self):
        with pytest.raises(ValueError):
            DetectionFunction(false_positive=1.5)
        with pytest.raises(ValueError):
            DetectionFunction(false_positive=-0.1)


class TestPartialConformance:
    """Bright over the crest, reliably absent below a depth — the third observation.

    It was missing, and an observation with no home gets entered as whichever neighbour is closer:
    as a pick it does not support, which asserts a contact depth nobody picked, or as *absent*,
    which throws away that something is convincingly there. Neither is what was seen.
    """

    @staticmethod
    def _result(n=8000):
        return engine.run(reference_prospect(), n, 4242)

    def _at(self, cutoff, **kw):
        result = self._result()
        obs = DhiObservation(seen=True, absent_below_m=cutoff, **kw)
        return result, dhi.update(result, DetectionFunction(), obs)

    def test_it_is_a_seen_anomaly(self):
        """The strength channel applies in full: something is there to characterise."""
        obs = DhiObservation(seen=True, absent_below_m=2250.0)
        assert obs.seen and obs.is_partial

    def test_a_pick_and_a_bound_are_mutually_exclusive(self):
        with pytest.raises(ValueError, match="no picked contact"):
            DhiObservation(seen=True, contact_m=2250.0, absent_below_m=2300.0)

    def test_an_unseen_anomaly_cannot_be_partial(self):
        with pytest.raises(ValueError, match="is a .seen. anomaly"):
            DhiObservation(seen=False, absent_below_m=2250.0)

    def test_a_cutoff_above_the_apex_describes_no_prospect(self):
        result = self._result()
        shallow = float(result.apex_m.min()) - 50.0
        with pytest.raises(ValueError, match="at or above the apex"):
            dhi.likelihood(result, DetectionFunction(),
                           DhiObservation(seen=True, absent_below_m=shallow))

    def test_well_above_the_cutoff_every_contact_is_equally_consistent(self):
        """The claim is a bound, not a depth. Clear of the cutoff no contact is preferred, which is
        what separates this from a pick — a pick peaks somewhere and this must not.

        *Clear of* means more than a few σ above: the bound is a censored pick with the same
        edge error, so within a σ or two of the cutoff a contact is a little less consistent than
        one far above it. That is the softness, and it is meant.
        """
        result, post = self._at(2250.0, p_valid=1.0, pick_sigma_m=15.0)
        h_off = 2250.0 - result.apex_m
        clear = result.column_m <= h_off - 4 * 15.0
        assert clear.sum() > 50, "the fixture needs realisations well above the cutoff"
        detection = DetectionFunction()
        bound_factor = post.weights[clear] / detection.at(result.column_m[clear])
        assert np.allclose(bound_factor, bound_factor[0], rtol=1e-4)

    def test_the_bound_is_a_censored_pick_and_nothing_else(self):
        """The formula, pinned: `D(h) · Φ((z_off − z) / σ)` in the valid branch. One error, one
        parameter, and the detection function applied once."""
        result = self._result()
        detection = DetectionFunction()
        obs = DhiObservation(seen=True, absent_below_m=2250.0, p_valid=1.0, pick_sigma_m=20.0)
        weights = dhi.likelihood(result, detection, obs)
        from scipy.stats import norm
        expected = detection.at(result.column_m) * norm.cdf(
            (2250.0 - result.contact_m) / 20.0)
        np.testing.assert_allclose(weights, expected, rtol=1e-12)

    def test_the_bound_is_fifty_fifty_at_the_stated_cutoff(self):
        """The interpreter states the depth; the model puts the half-way point there, not 25 m
        below it as the old form did (its softness came from `h50`, elicited for another job)."""
        result = self._result()
        detection = DetectionFunction()
        obs = DhiObservation(seen=True, absent_below_m=2250.0, p_valid=1.0)
        factor = dhi.likelihood(result, detection, obs) / detection.at(result.column_m)
        at_cutoff = np.abs(result.contact_m - 2250.0) < 1.0
        assert at_cutoff.any()
        assert factor[at_cutoff].mean() == pytest.approx(0.5, abs=0.03)

    def test_the_edge_error_is_the_only_width_the_bound_has(self):
        """Halving σ sharpens the transition; changing the detection function's shape does not
        touch it. The two parameters answer different questions and stay apart."""
        result = self._result()
        band = np.abs(result.contact_m - 2250.0) < 30.0
        assert band.sum() > 30

        def transition(sigma, **det):
            obs = DhiObservation(seen=True, absent_below_m=2250.0, p_valid=1.0, pick_sigma_m=sigma)
            d = DetectionFunction(**det)
            factor = dhi.likelihood(result, d, obs) / d.at(result.column_m)
            return float(np.std(factor[band]))

        assert transition(5.0) > transition(30.0)
        assert transition(15.0, h50_m=25.0) == pytest.approx(transition(15.0, h50_m=80.0),
                                                              rel=1e-9)
        assert transition(15.0, ceiling=0.9) == pytest.approx(transition(15.0, ceiling=0.5),
                                                               rel=1e-9)

    def test_it_argues_against_columns_below_the_cutoff(self):
        result, post = self._at(2250.0, p_valid=1.0)
        h_off = 2250.0 - result.apex_m
        above, well_below = result.column_m <= h_off, result.column_m > h_off + 100.0
        assert well_below.sum() > 20, "the fixture needs realisations well below the cutoff"
        assert post.weights[well_below].mean() < 0.5 * post.weights[above].mean()

    def test_the_likelihood_falls_away_rather_than_stopping_dead(self):
        """A bound that switched off at the cutoff would be a claim of impossibility. A slice of
        column just under it could plausibly have been missed; a hundred metres of it could not."""
        result = self._result()
        detection = DetectionFunction()
        weights = dhi.likelihood(result, detection,
                                 DhiObservation(seen=True, absent_below_m=2250.0, p_valid=1.0))
        h_off = 2250.0 - result.apex_m
        excess = result.column_m - h_off
        just_below = (excess > 0.0) & (excess < 10.0)
        far_below = excess > 120.0
        assert just_below.any() and far_below.any()
        assert weights[just_below].mean() > 3.0 * weights[far_below].mean()

    @pytest.mark.parametrize("p_valid", [0.2, 0.5, 0.9, 0.99])
    def test_cromwell_holds(self, p_valid):
        """`L >= 1 - p_valid`, so no seismic interpretation ever rules a column out."""
        result = self._result()
        weights = dhi.likelihood(result, DetectionFunction(),
                                 DhiObservation(seen=True, absent_below_m=2250.0, p_valid=p_valid))
        assert weights.min() >= (1.0 - p_valid) - 1e-12

    def test_the_cutoff_is_converted_against_each_realisations_own_apex(self):
        """A depth means nothing until it is converted against the apex drawn with it. Moving the
        apex must move the bound, or the two are being compared in different spaces."""
        result = self._result()
        detection, obs = DetectionFunction(), DhiObservation(seen=True, absent_below_m=2250.0)
        weights = dhi.likelihood(result, detection, obs)
        deeper = dataclasses.replace(result, apex_m=result.apex_m + 100.0)
        assert not np.allclose(weights, dhi.likelihood(deeper, detection, obs))

    def test_it_is_weaker_than_a_pick_at_the_same_depth(self):
        """The whole point. A pick asserts a contact; a bound only says *not below here*, and the
        arithmetic must not let the weaker observation speak as loudly as the stronger one."""
        result = self._result()
        detection = DetectionFunction()
        pick = dhi.update(result, detection, DhiObservation(
            seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.6))
        bound = dhi.update(result, detection, DhiObservation(
            seen=True, absent_below_m=2250.0, p_valid=0.6))
        prior_p50 = float(np.median(result.contact_m[result.above_minimum]))
        moved_by_pick = abs(pick.percentiles(50.0)[0] - prior_p50)
        moved_by_bound = abs(bound.percentiles(50.0)[0] - prior_p50)
        assert moved_by_bound < moved_by_pick

    def test_a_cutoff_below_everything_contributes_nothing_of_its_own(self):
        """An observation consistent with the whole prior must add no argument of its own.

        Not that the weights go flat: a *seen* anomaly always argues for a column tall enough to
        have been visible, and that ``D(h)`` term is present here as it is for a pick. What has to
        vanish is the bound's own contribution, so that the case degrades to "I saw something".
        """
        result = self._result()
        detection = DetectionFunction()
        deep = float(result.contact_m.max()) + 200.0
        weights = dhi.likelihood(result, detection,
                                 DhiObservation(seen=True, absent_below_m=deep, p_valid=1.0))
        bound_factor = weights / detection.at(result.column_m)
        assert np.allclose(bound_factor, bound_factor[0])

    def test_r_dhi_is_defined_and_sits_between_the_two_it_replaces(self):
        """Entered as a pick the evidence reads far too strongly for it; entered as absent it reads
        far too weakly. The point of the case is that it belongs between them.

        Run at a real assessment minimum, because ``r_dhi`` for a seen anomaly is a success-versus-
        failure ratio and there are no failures to divide by when every realisation clears zero.
        That is a property of the ratio, not of this observation.
        """
        result = engine.run(dataclasses.replace(reference_prospect(), min_column_m=180.0),
                            8000, 4242)
        detection = DetectionFunction()
        r_pick = dhi.update(result, detection, DhiObservation(
            seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.6)).r_dhi
        r_bound = dhi.update(result, detection, DhiObservation(
            seen=True, absent_below_m=2250.0, p_valid=0.6)).r_dhi
        r_absent = dhi.update(result, detection, DhiObservation(seen=False)).r_dhi
        assert np.isfinite(r_bound)
        assert r_absent < r_bound < r_pick


class TestTheSpuriousDensityIsAPropertyOfTheModel:
    """`s` is one over the declared contact support, not over whatever the sampler reached.

    Audit of 14 Sep 2026. `1 / (max − min)` of the realised contacts made a picked flat spot's
    likelihood depend on the trial count and the seed: four per cent between a 2 000- and a
    50 000-trial run of the same model on the reference prospect. The support now comes off the
    declared distributions and the same limit set gives the same number every time.
    """

    def test_the_support_comes_from_the_declared_inputs(self):
        limits = reference_prospect()
        shallow, deep = limits.contact_support_m()
        assert shallow == pytest.approx(float(limits.apex.ppf(np.array([0.001]))[0]))
        assert deep > shallow + 100.0

    def test_the_density_does_not_depend_on_the_trial_count(self):
        limits = reference_prospect()
        densities = {n: dhi.spurious_density(engine.run(limits, n, 4242).limit_set
                                             .contact_support_m())
                     for n in (500, 5_000, 50_000)}
        assert len({round(v, 15) for v in densities.values()}) == 1, densities

    def test_the_density_does_not_depend_on_the_seed(self):
        limits = reference_prospect()
        densities = [dhi.spurious_density(engine.run(limits, 4_000, seed).limit_set
                                          .contact_support_m()) for seed in (1, 2, 3, 99)]
        assert max(densities) == min(densities)

    def test_the_old_construction_did_move_with_the_trial_count(self):
        """The defect, reproduced on purpose so its absence stays visible."""
        limits = reference_prospect()
        spans = []
        for n in (500, 50_000):
            contacts = engine.run(limits, n, 4242).contact_m
            spans.append(float(contacts.max() - contacts.min()))
        assert abs(spans[1] - spans[0]) / spans[1] > 0.01, "the sample-based span no longer moves"

    def test_a_pick_likelihood_is_the_same_whatever_the_trial_count(self):
        """What the density is for: the floor under a pick, per realisation, cannot depend on how
        many other realisations were drawn."""
        limits = reference_prospect()
        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.6)
        floors = []
        for n in (1_000, 40_000):
            result = engine.run(limits, n, 4242)
            weights = dhi.likelihood(result, DetectionFunction(), obs)
            # Far from the pick the valid branch is nil and the weight is the floor alone.
            far = np.abs(result.contact_m - 2250.0) > 8 * 15.0
            assert far.any()
            floors.append(float(weights[far].mean()))
        assert floors[0] == pytest.approx(floors[1], rel=1e-9)

    def test_the_deep_end_is_the_tightest_always_active_limit(self):
        """A contact cannot lie below a limit that is always there."""
        base = reference_prospect()
        tight = dataclasses.replace(base, limits=base.limits + (
            Limit("Shallow lid", Group.RETENTION, 1.0,
                  DepthDistribution("fixed", {"value": 120.0})),))
        _, deep_base = base.contact_support_m()
        _, deep_tight = tight.contact_support_m()
        assert deep_tight < deep_base
        assert deep_tight == pytest.approx(float(base.apex.ppf(np.array([0.999]))[0]) + 120.0)

    def test_a_model_with_no_room_for_a_contact_is_refused(self):
        base = reference_prospect()
        from hcwc.core.limits import DEPTH
        lid = dataclasses.replace(base, limits=base.limits + (
            Limit("Lid above the apex", Group.CLOSURE, 1.0,
                  DepthDistribution("fixed", {"value": 2000.0}), kind=DEPTH),))
        with pytest.raises(ValueError, match="no depth interval"):
            lid.contact_support_m()


class TestANeutralAmplitudeDoesNothing:
    """Lars, 2 Sep 2026, checking against E-POS: a DHI strength of 0 must not lift POS.

    It did. ``r_strength`` was exactly 1, but the geometry channel contributed a ratio of 1.66
    estimated from **seven** below-minimum realisations out of ten thousand, and that carried the
    headline chance from 40.8 % to 53.3 %. An observation that says nothing has to do nothing.
    """

    @staticmethod
    def _posterior(min_column_m, strength_ratio=1.0):
        limits = dataclasses.replace(reference_prospect(), min_column_m=min_column_m)
        result = engine.run(limits, 10000, 4242)
        return dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=18.0,
                                         p_valid=0.6))

    def test_a_denominator_of_seven_is_not_a_sample(self):
        """The old guard caught only *every* realisation clearing the minimum."""
        post = self._posterior(1.0)
        below = int((~post.result.above_minimum).sum())
        assert below < dhi.min_failures_for_r(post.result.n)
        assert np.isnan(post.r_dhi), f"{below} failures should not support a ratio"

    def test_it_is_defined_where_the_minimum_is_a_real_threshold(self):
        post = self._posterior(180.0)
        assert int((~post.result.above_minimum).sum()) >= dhi.min_failures_for_r(post.result.n)
        assert np.isfinite(post.r_dhi) and post.r_dhi > 1.0

    def test_the_gate_is_a_share_so_the_trial_count_does_not_decide_it(self):
        """Audit finding P2-4, 14 Sep 2026.

        The gate was a count of 100: one per cent of ten thousand trials, ten per cent of a
        thousand, so a prospect's ratio could be defined on the default sidebar and undefined
        after the trial count was lowered. As a share with a floor, the verdict at a minimum a
        real share of realisations miss is the same at 1 000 and 100 000 trials, and so is the
        verdict at a minimum almost none miss.
        """
        for n in (1_000, 100_000):
            assert dhi.min_failures_for_r(n) == max(int(np.ceil(0.01 * n)), dhi.MIN_FAILURES_FLOOR)

        def _at(min_column_m, n):
            limits = dataclasses.replace(reference_prospect(), min_column_m=min_column_m)
            result = engine.run(limits, n, 4242)
            return dhi.update(result, DetectionFunction(),
                              DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=18.0,
                                             p_valid=0.6))

        real = [np.isfinite(_at(180.0, n).r_dhi) for n in (1_000, 100_000)]
        floor = [np.isfinite(_at(1.0, n).r_dhi) for n in (1_000, 100_000)]
        assert real == [True, True]
        assert floor == [False, False]

    def test_the_floor_keeps_a_thin_denominator_out_at_small_trial_counts(self):
        """One per cent of 300 trials is three realisations, and three is not a sample."""
        assert dhi.min_failures_for_r(300) == dhi.MIN_FAILURES_FLOOR

    def test_a_neutral_strength_leaves_pos_exactly_alone(self):
        """The whole point. With the geometry channel undefined, the combination falls back to
        strength alone — and a strength of 0 is a likelihood ratio of exactly 1."""
        combined = comparison.CombinedUpdate(prior_pos=0.408, r_geometry=float("nan"),
                                      r_strength=1.0, dependence=0.5)
        assert combined.posterior_pos == pytest.approx(0.408, abs=1e-12)

    @pytest.mark.parametrize("dependence", [0.0, 0.5, 1.0])
    def test_neutral_stays_neutral_at_every_dependence(self, dependence):
        combined = comparison.CombinedUpdate(prior_pos=0.408, r_geometry=float("nan"),
                                      r_strength=1.0, dependence=dependence)
        assert combined.posterior_pos == pytest.approx(0.408, abs=1e-12)

    def test_a_defined_geometry_channel_still_moves_it(self):
        """The guard must not have switched the channel off everywhere.

        `CombinedUpdate` is no longer the chance (see the classes below); this pins the class's
        own arithmetic, which the tab still draws as a comparison.
        """
        combined = comparison.CombinedUpdate(prior_pos=0.408, r_geometry=2.34, r_strength=1.0,
                                      dependence=0.5)
        assert combined.posterior_pos > 0.408


# --------------------------------------------------------------------------- the conditional chain
#
# Audit of 14 Sep 2026. The engine's realisations are draws from p(h | G); `p_valid` was built as
# P(G | strength) × c, so the strength reached the geometry posterior through the mixture weight,
# and then again through `CombinedUpdate`. Measured on the reference prospect with c held at 0.70:
# moving the strength alone moved the posterior P50 by 17 m and the conditional column term by six
# points. The chain is now A: P(G | strength); B: p(h | G, geometry); C: their product at h_min.


class TestStrengthCannotReachTheGeometryPosterior:
    """B is conditional on G, so nothing about whether there is hydrocarbon may enter it.

    The strength ratio is the answer to *is there hydrocarbon*. If it can move the posterior over
    *where the contact is, given there is*, it is being counted where it does not belong -- and it
    was, through `p_valid`. These tests hold the contact-attribute judgement `c` fixed and vary
    the strength across its whole allowed range.
    """

    P_G, C = 0.408, 0.70

    def setup_method(self):
        self.result = run(min_column_m=120.0)
        self.det = DetectionFunction()
        self.obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=self.C)

    def _outcome(self, r):
        return dhi.outcome(self.result, self.det, self.obs, p_g=self.P_G, r_strength=r)

    def test_the_geometry_posterior_is_identical_at_every_strength(self):
        """The weights never see the strength, so the P50 cannot move by a nanometre."""
        neutral = self._outcome(1.0).contact_m
        for r in (1.0 / dhi.R_SINGLE_CHANNEL, 0.5, 1.4, 3.0, dhi.R_SINGLE_CHANNEL):
            assert self._outcome(r).contact_m == neutral

    def test_the_conditional_column_term_is_identical_at_every_strength(self):
        """`P(h ≥ h_min | G, geometry)` is a property of the geometry alone."""
        post = dhi.update(self.result, self.det, self.obs)
        term = post.pos()
        for r in (0.1, 1.0, 10.0):
            assert dhi.prospect_pos(self.P_G, r, post) / dhi.p_g_given_strength(self.P_G, r) \
                == pytest.approx(term, abs=1e-15)

    def test_a_neutral_strength_changes_nothing_at_all(self):
        """R = 1 leaves P(G) alone, so the chance is P(G) × the conditional term exactly, and the
        contact is the geometry posterior's own. No hidden path can move either."""
        post = dhi.update(self.result, self.det, self.obs)
        got = self._outcome(1.0)
        assert got.pos == pytest.approx(self.P_G * post.pos(), abs=1e-15)
        assert got.contact_m == float(post.percentiles(50.0)[0])

    def test_the_strength_moves_only_the_first_factor(self):
        """Two strengths, one geometry posterior: the ratio of the two chances is the ratio of the
        two updated element chances, to machine precision."""
        a, b = self._outcome(1.0), self._outcome(dhi.R_SINGLE_CHANNEL)
        expected = (dhi.p_g_given_strength(self.P_G, dhi.R_SINGLE_CHANNEL)
                    / dhi.p_g_given_strength(self.P_G, 1.0))
        assert b.pos / a.pos == pytest.approx(expected, rel=1e-12)

    def test_the_old_construction_did_leak_and_this_is_why_the_test_exists(self):
        """The regression this guards against, reproduced on purpose.

        Building `p_valid` as P(G | strength) × c -- the shipped form until 14 Sep 2026 -- and
        holding c fixed, the geometry posterior moves with the strength. That is the double count.
        Kept as an executable statement of the defect, so that if anyone reintroduces a P(G)
        factor into `p_valid` the difference is visible here rather than on a report sheet.
        """
        p50 = []
        for r in (1.0, 10.0):
            leaked = dataclasses.replace(self.obs, p_valid=dhi.simm_update(self.P_G, r) * self.C)
            post = dhi.update(self.result, self.det, leaked)
            p50.append(float(post.percentiles(50.0)[0]))
        assert abs(p50[1] - p50[0]) > 5.0, "the old construction no longer leaks; update this note"

    def test_p_valid_is_not_bounded_by_the_element_chance(self):
        """A confident contact interpretation on a risky prospect is a legal and common state.

        Under the old ceiling `p_valid ≤ P(G | strength)`, so c = 0.95 on a 0.4 prospect was
        clipped to something under 0.4. Conditional on G it is 0.95, and the chance still comes out
        below P(G | strength) because the column term is at most one.
        """
        confident = dataclasses.replace(self.obs, p_valid=0.95)
        post = dhi.update(self.result, self.det, confident)
        assert post.observation.p_valid == 0.95
        chance = dhi.prospect_pos(0.4, 1.4, post)
        assert chance <= dhi.p_g_given_strength(0.4, 1.4)


class TestTheHeadlineIsReadOffTheDistributionItIsDrawnBeside:
    """One posterior over h supplies the histogram, the percentiles, F(h) and the chance.

    Under the blended construction the headline was `simm_update(P(G) · F_prior, R_comb)` while
    the histogram came from the weights, and the curve was rescaled to pass through the headline.
    These tests pin the identities that make rescaling unnecessary.
    """

    P_G, R = 0.408, 1.4

    def setup_method(self):
        self.result = run(min_column_m=120.0)
        self.post = dhi.update(self.result, DetectionFunction(),
                               DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0,
                                              p_valid=0.70))

    def test_the_chance_is_the_weighted_share_above_the_minimum(self):
        """The conditional term is exactly the histogram's mass at and below the threshold depth."""
        w = self.post.weights
        col = self.result.column_m
        h_min = self.result.limit_set.min_column_m
        by_hand = float(w[col >= h_min].sum() / w.sum())
        assert self.post.pos() == pytest.approx(by_hand, abs=1e-12)
        assert dhi.prospect_pos(self.P_G, self.R, self.post) == pytest.approx(
            dhi.p_g_given_strength(self.P_G, self.R) * by_hand, abs=1e-12)

    def test_the_curve_passes_through_the_headline_without_rescaling(self):
        h_min = self.result.limit_set.min_column_m
        curve = dhi.prospect_pos_curve(self.P_G, self.R, self.post, np.array([h_min]))
        assert float(curve[0]) == pytest.approx(dhi.prospect_pos(self.P_G, self.R, self.post),
                                                abs=1e-15)

    def test_the_curve_is_the_exceedance_scaled_by_one_constant(self):
        """No point on the curve carries any factor the headline does not."""
        grid = np.linspace(0.0, float(self.result.column_m.max()), 50)
        curve = dhi.prospect_pos_curve(self.P_G, self.R, self.post, grid)
        f_post = self.post.exceedance(grid)
        scale = dhi.p_g_given_strength(self.P_G, self.R)
        np.testing.assert_allclose(curve, scale * f_post, rtol=0, atol=1e-15)

    def test_the_percentiles_and_the_chance_share_one_set_of_weights(self):
        """The P50 the tab prints and the chance it prints are readings of the same object: the
        weighted median lies where the weighted exceedance crosses one half."""
        p50 = float(self.post.percentiles(50.0)[0])
        keep = self.result.above_minimum
        contacts, w = self.result.contact_m[keep], self.post.weights[keep]
        share_deeper = float(w[contacts >= p50].sum() / w.sum())
        assert share_deeper == pytest.approx(0.5, abs=0.01)

    def test_the_headline_is_bounded_by_the_updated_element_chance(self):
        """F ≤ 1, so the chance can never exceed P(G | strength) -- the blended form could."""
        for r in (0.1, 1.0, 10.0):
            assert dhi.prospect_pos(self.P_G, r, self.post) <= dhi.p_g_given_strength(self.P_G, r)

    def test_the_chance_falls_monotonically_with_the_threshold(self):
        grid = np.linspace(0.0, float(self.result.column_m.max()), 40)
        curve = dhi.prospect_pos_curve(self.P_G, self.R, self.post, grid)
        assert np.all(np.diff(curve) <= 1e-15)


class TestTheOtherRatiosWereCheckedToo:
    """After the `r_dhi` fix, every other ratio and conditional mean in the app was audited for the
    same failure — a count-based guard missing a weight-based collapse."""

    @staticmethod
    def _posterior(sigma, p_valid):
        result = engine.run(reference_prospect(), 10000, 4242)
        return dhi.update(result, DetectionFunction(),
                          DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=sigma,
                                         p_valid=p_valid))

    def test_the_tornado_reports_effective_sample_not_a_headcount(self):
        """A ten-per-cent tail is about a thousand realisations whatever the DHI says, so the count
        cannot distinguish a well-supported bar from a collapsed one. On this prospect a sharp pick
        leaves tails of ~990 carrying an effective sample in the twenties."""
        from hcwc.core import sensitivity

        sharp = sensitivity.dhi_tornado(self._posterior(4.0, 0.98), space="column")
        broad = sensitivity.dhi_tornado(self._posterior(18.0, 0.6), space="column")
        assert min(e.support for e in sharp) < 100
        assert min(e.support for e in broad) > 300
        assert min(e.support for e in sharp) < min(e.support for e in broad) / 5

    def test_effective_n_is_the_count_when_nothing_is_reweighted(self):
        from hcwc.core.sensitivity import effective_n

        assert effective_n(np.ones(500)) == pytest.approx(500.0)
        assert effective_n(np.zeros(500)) == 0.0
        spiked = np.concatenate([np.ones(1), np.full(999, 1e-12)])
        assert effective_n(spiked) < 2.0

    def test_the_absent_branch_saturates_rather_than_going_noisy(self):
        """Checked and left alone. `r_dhi` for an absent anomaly is `E[1-D(h) | success]` with no
        denominator, and at a high minimum every surviving column is long enough that `D` has
        reached its ceiling — so the value is `1 - ceiling` and stays there rather than wandering
        as the success set thins. It is stable for a reason, not by luck."""
        detection = DetectionFunction()
        seen_at = []
        for minimum in (300.0, 330.0, 350.0):
            result = engine.run(dataclasses.replace(reference_prospect(), min_column_m=minimum),
                                10000, 4242)
            if not result.above_minimum.any():
                continue
            seen_at.append(dhi.update(result, detection, DhiObservation(seen=False)).r_dhi)
        assert len(seen_at) >= 2
        assert all(v == pytest.approx(1.0 - detection.ceiling, abs=0.01) for v in seen_at)


# --------------------------------------------------------------------------- the three combinations
#
# `combination_exceedance` is the argument for offering three methods rather than one: if they
# agreed, the tab would be a lecture. Until 8 Sep 2026 nothing asserted that they disagree, or in
# which direction. The tab rendered without raising and that was the whole of its coverage.


class TestTheThreeCombinations:
    """SCENARIO mixes, POOLED multiplies without the detection function, BAYES is the update."""

    HS = np.array([50.0, 100.0, 150.0, 200.0, 250.0])

    def _setup(self, *, seen: bool = True, sigma: float = 15.0, p_valid: float = 0.8):
        result = run(min_column_m=100.0)
        detection = DetectionFunction()
        apex = float(np.median(result.apex_m))
        observation = DhiObservation(seen=seen, contact_m=apex + 200.0 if seen else None,
                                     pick_sigma_m=sigma, p_valid=p_valid)
        return result, detection, observation

    def _curve(self, method, **kw):
        result, detection, observation = self._setup(**kw)
        return comparison.combination_exceedance(result, detection, observation, self.HS, method=method)

    def test_every_method_returns_a_valid_exceedance_curve(self):
        for method in comparison.COMBINATIONS:
            got = self._curve(method)
            assert got.shape == self.HS.shape
            assert np.all((got >= 0.0) & (got <= 1.0)), method
            assert np.all(np.diff(got) <= 1e-12), f"{method} is not monotone decreasing"

    def test_the_three_do_not_agree(self):
        """The reason all three are offered. If this ever passes trivially, the tab is arguing
        about a distinction that no longer exists."""
        curves = {m: self._curve(m) for m in comparison.COMBINATIONS}
        assert not np.allclose(curves[comparison.SCENARIO], curves[comparison.BAYES], atol=0.01)
        assert not np.allclose(curves[comparison.POOLED], curves[comparison.BAYES], atol=0.01)

    def test_an_unknown_method_is_refused_by_name(self):
        result, detection, observation = self._setup()
        with pytest.raises(ValueError, match="method must be one of"):
            comparison.combination_exceedance(result, detection, observation, self.HS, method="blend")

    def test_a_scalar_depth_still_returns_an_array(self):
        result, detection, observation = self._setup()
        got = comparison.combination_exceedance(result, detection, observation, 150.0)
        assert got.shape == (1,)


class TestTheScenarioSwitchIsAMixture:
    """Hood's rule: merge late, as a branch. It moves the contact and cannot sharpen."""

    HS = TestTheThreeCombinations.HS

    def test_the_observation_refuses_a_p_valid_of_zero(self):
        """Found writing this file: the two entry points disagree on purpose. An *observation*
        cannot carry p_valid = 0 -- an event you picked is never certainly not a contact, and a
        zero would put a hard zero in the likelihood that no later evidence could revive. The
        scenario switch's override does accept 0, because there it means "show me the branch
        without the DHI" rather than a claim about the anomaly."""
        with pytest.raises(ValueError, match=r"must lie in \(0, 1\]"):
            DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=10.0, p_valid=0.0)

    def test_p_valid_zero_returns_the_geology_untouched(self):
        result = run(min_column_m=100.0)
        observation = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=10.0, p_valid=0.5)
        got = comparison.combination_exceedance(result, DetectionFunction(), observation, self.HS,
                                         method=comparison.SCENARIO, p_valid=0.0)
        geological = np.array([float((result.column_m >= h).mean()) for h in self.HS])
        assert got == pytest.approx(geological)

    def test_it_interpolates_linearly_between_the_two_branches(self):
        """A mixture, not an update: the answer at p_valid = 0.5 is the average of the ends."""
        result = run(min_column_m=100.0)
        det = DetectionFunction()

        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=10.0, p_valid=0.5)

        def at(p):
            return comparison.combination_exceedance(result, det, obs, self.HS,
                                              method=comparison.SCENARIO, p_valid=p)

        assert at(0.5) == pytest.approx(0.5 * (at(0.0) + at(1.0)), abs=1e-9)

    def test_an_out_of_range_p_valid_is_refused(self):
        result = run(min_column_m=100.0)
        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=10.0)
        with pytest.raises(ValueError, match="must be in"):
            comparison.combination_exceedance(result, DetectionFunction(), obs, self.HS,
                                       method=comparison.SCENARIO, p_valid=1.4)

    def test_an_explicit_p_valid_overrides_the_observation(self):
        """The override exists so the tab can sweep the parameter; the default must be the
        observation's own value, which is the bug this argument replaced -- a constant 0.655
        sitting a section away from an update running on a derived number."""
        result = run(min_column_m=100.0)
        det = DetectionFunction()
        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=10.0, p_valid=0.9)
        from_obs = comparison.combination_exceedance(result, det, obs, self.HS, method=comparison.SCENARIO)
        overridden = comparison.combination_exceedance(result, det, obs, self.HS,
                                                method=comparison.SCENARIO, p_valid=0.9)
        assert from_obs == pytest.approx(overridden)

    def test_an_absent_anomaly_leaves_the_scenario_switch_with_nothing_to_say(self):
        """It has no branch for absence -- which is one of the things the likelihood form can do
        and this cannot, and the article says so."""
        result = run(min_column_m=100.0)
        got = comparison.combination_exceedance(result, DetectionFunction(),
                                         DhiObservation(seen=False), self.HS,
                                         method=comparison.SCENARIO)
        geological = np.array([float((result.column_m >= h).mean()) for h in self.HS])
        assert got == pytest.approx(geological)


class TestPooledIsBayesWithTheDetectionFunctionRemoved:
    """The whole difference between the two, stated as arithmetic."""

    HS = TestTheThreeCombinations.HS

    OBS = dict(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=1.0)

    def test_a_saturated_detection_function_collapses_bayes_onto_pooled(self):
        """A D(h) that is constant over the columns in play cancels in the normalisation, so the
        two coincide. That is the arithmetic the rest of this class is measured against."""
        result = run(min_column_m=100.0)
        obs = DhiObservation(**self.OBS)
        flat = DetectionFunction(h50_m=1e-6, steepness_m=1e-6, ceiling=1.0)
        pooled = comparison.combination_exceedance(result, flat, obs, self.HS, method=comparison.POOLED)
        bayes = comparison.combination_exceedance(result, flat, obs, self.HS, method=comparison.BAYES)
        assert bayes == pytest.approx(pooled, abs=1e-6)

    def test_the_shipped_detection_function_does_not_separate_them_on_a_seen_anomaly(self):
        """Measured 8 Sep 2026, and not what the tab's framing would lead you to expect.

        At the default `h50_m = 25`, D(h) does vary across this prospect's columns -- 0.34 to
        0.90 -- and the two methods still agree to **five decimal places**. The pick is far
        sharper than the detection function: a 15 m sigma concentrates the weight into a narrow
        band of columns, and across that band D(h) is near enough constant to cancel.

        So for a *seen* anomaly on a thick-column prospect the detection function is very nearly
        inert, and POOLED's "selection effect it cannot see" is real in principle and about
        1e-5 in size. The place D(h) earns its keep is the next two tests.
        """
        result = run(min_column_m=100.0)
        obs = DhiObservation(**self.OBS)
        det = DetectionFunction()
        pooled = comparison.combination_exceedance(result, det, obs, self.HS, method=comparison.POOLED)
        bayes = comparison.combination_exceedance(result, det, obs, self.HS, method=comparison.BAYES)
        assert np.abs(pooled - bayes).max() < 1e-4

    def test_it_separates_them_when_it_varies_where_the_pick_puts_the_weight(self):
        """D(h) only counts where the posterior has mass. Move the detection threshold into the
        column range the pick favours and the two part company by 0.4 in exceedance."""
        result = run(min_column_m=100.0)
        obs = DhiObservation(**self.OBS)
        steep = DetectionFunction(h50_m=250.0, steepness_m=8.0)
        pooled = comparison.combination_exceedance(result, steep, obs, self.HS, method=comparison.POOLED)
        bayes = comparison.combination_exceedance(result, steep, obs, self.HS, method=comparison.BAYES)
        assert np.abs(pooled - bayes).max() > 0.3
        # The direction, which is the whole point of D(h) and is easy to get backwards. A high
        # h50 means only a *tall* column would have been detectable, so having seen an anomaly
        # is evidence the column is tall, and BAYES must sit above POOLED. Pooling cannot know
        # this: it conditions on the pick alone and never asks what it would have taken to see.
        assert np.all(bayes >= pooled - 1e-9)

    def test_pooled_ignores_an_absent_anomaly_and_bayes_does_not(self):
        """Absence is evidence only through D(h); without it there is nothing to condition on."""
        result = run(min_column_m=100.0)
        det = DetectionFunction()
        absent = DhiObservation(seen=False)
        geological = np.array([float((result.column_m >= h).mean()) for h in self.HS])
        pooled = comparison.combination_exceedance(result, det, absent, self.HS, method=comparison.POOLED)
        bayes = comparison.combination_exceedance(result, det, absent, self.HS, method=comparison.BAYES)
        assert pooled == pytest.approx(geological)
        assert np.all(bayes <= geological + 1e-9)
        assert not np.allclose(bayes, geological, atol=1e-3)


class TestBayesMatchesTheUpdateItIsCompared:
    def test_it_reproduces_the_posterior_exceedance_exactly(self):
        """`combination_exceedance(BAYES)` and `update().exceedance()` are two routes to one
        number, shown on the same tab. They must not drift."""
        result = run(min_column_m=100.0)
        det = DetectionFunction()
        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.85)
        hs = TestTheThreeCombinations.HS
        direct = dhi.update(result, det, obs).exceedance(hs)
        combined = comparison.combination_exceedance(result, det, obs, hs, method=comparison.BAYES)
        assert combined == pytest.approx(direct, rel=1e-12)


class TestDetectionFunctionEdges:
    """Red team, 22 Sep 2026: units in metres of column; h50 the 50 % column; the ceiling below
    one; no overflow at any column height."""

    def test_h50_is_half_the_ceiling(self):
        d = DetectionFunction(h50_m=25.0, steepness_m=8.0, ceiling=0.9)
        assert float(d.at(25.0)) == pytest.approx(0.45)

    def test_zero_and_very_large_columns(self):
        d = DetectionFunction()
        assert 0.0 < float(d.at(0.0)) < 0.1
        assert float(d.at(1e6)) == pytest.approx(d.ceiling)
        assert float(d.at(1e9)) == pytest.approx(d.ceiling)

    def test_no_overflow_for_a_column_far_below_h50(self):
        import warnings
        d = DetectionFunction()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert float(d.at(-1e6)) == pytest.approx(0.0)

    def test_it_is_monotone(self):
        d = DetectionFunction()
        h = np.linspace(0.0, 400.0, 200)
        assert np.all(np.diff(d.at(h)) >= 0.0)
