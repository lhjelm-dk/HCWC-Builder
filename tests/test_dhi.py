"""The DHI update, and the claim `docs/DHI_alignment.md` was written to make.

That claim is testable in one line: the updated POS and the updated contact distribution must be
the *same object*, read at different thresholds. If `pos()` is ever anything other than
`exceedance(h_min)`, the note is wrong and so is the tool.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from hcwc.core import dhi, engine
from hcwc.core.dhi import DetectionFunction, DhiObservation
from hcwc.core.limits import LimitSet, reference_prospect

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


class TestScenarioSwitch:
    """Formulation A — the scenario switch."""

    def test_it_moves_the_contact_but_not_pos(self):
        result = run(100.0)
        switched = dhi.scenario_switch(result, 0.655, 2300.0, 20.0)
        assert switched.shape == result.contact_m.shape
        assert not np.allclose(switched, result.contact_m)

    def test_p_valid_zero_leaves_the_contact_untouched(self):
        result = run()
        assert np.allclose(dhi.scenario_switch(result, 0.0, 2300.0, 20.0), result.contact_m)

    def test_p_valid_one_replaces_every_contact(self):
        result = run()
        switched = dhi.scenario_switch(result, 1.0, 2300.0, 20.0)
        assert switched.mean() == pytest.approx(2300.0, abs=1.0)

    def test_the_switched_fraction_matches_p_valid(self):
        result = run()
        switched = dhi.scenario_switch(result, 0.655, 2300.0, 5.0)
        replaced = np.abs(switched - result.contact_m) > 1e-9
        assert replaced.mean() == pytest.approx(0.655, abs=0.01)

    def test_an_out_of_range_validity_is_refused(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            dhi.scenario_switch(run(), 1.5, 2300.0, 20.0)


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

    def test_r_is_floored_and_capped(self):
        m = dhi.StrengthModel()
        assert m.r_at(-10_000.0) >= dhi.R_FLOOR
        assert m.r_at(10_000.0) <= dhi.R_CAP

    def test_r_is_scale_invariant_in_the_strength_axis(self):
        """Only the relative heights matter, so rescaling the axis cannot change R."""
        base = dhi.StrengthModel().r_at(25.0)
        scaled = dhi.StrengthModel(dhi.StrengthCase(-500.0, 1000.0),
                                   dhi.StrengthCase(-1000.0, 500.0)).r_at(250.0)
        assert scaled == pytest.approx(base, rel=1e-9)


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
        c = dhi.CombinedUpdate(0.4, r_geometry=2.5, r_strength=1.4, dependence=0.0)
        assert c.r_combined == pytest.approx(2.5 * 1.4, rel=1e-6)

    def test_dependence_one_takes_the_stronger_alone(self):
        c = dhi.CombinedUpdate(0.4, r_geometry=2.5, r_strength=1.4, dependence=1.0)
        assert c.r_combined == pytest.approx(2.5, rel=1e-6)

    def test_a_half_dependence_sits_between(self):
        half = dhi.CombinedUpdate(0.4, 2.5, 1.4, 0.5).r_combined
        assert 2.5 < half < 2.5 * 1.4

    def test_the_posterior_uses_the_combined_ratio(self):
        c = dhi.CombinedUpdate(0.432, 2.5, 1.4, 0.5)
        assert c.posterior_pos == pytest.approx(dhi.simm_update(0.432, c.r_combined))

    def test_two_downward_channels_still_combine_downward(self):
        c = dhi.CombinedUpdate(0.5, r_geometry=0.5, r_strength=0.4, dependence=0.0)
        assert c.r_combined < 0.5
        assert c.posterior_pos < 0.5

    def test_a_missing_geometry_channel_falls_back_to_strength(self):
        c = dhi.CombinedUpdate(0.4, r_geometry=float("nan"), r_strength=1.4)
        assert c.r_combined == pytest.approx(1.4)

    def test_dependence_out_of_range_refused(self):
        with pytest.raises(ValueError, match="dependence must be"):
            dhi.CombinedUpdate(0.4, 2.0, 1.5, dependence=1.5)


class TestTheUpdateIsAnchoredToTheGeologicalPos:
    """What the DHI update multiplies, and the bug that came of getting it wrong.

    **E-POS anchors its DFI update to the geological POS** — the ∏-pillars product, or the ESL
    mass-rollup via `prior_pg_override` (`logic/dfi_bayes.py::compute_dfi_posterior`). It never
    anchors to a geometric exceedance probability.

    This tool anchored to `F(h_min)` alone, which is `P(column reaches the threshold | the prospect
    works)`. At a zero assessment minimum that is exactly 1.0, so a perfectly ordinary DHI appeared
    to leave POS at 100 %: nothing can move certainty. The prospect POS is the **product** of the
    two, and both halves already existed — the element chances on tab ② and the exceedance from the
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
        c = dhi.spurious_density(result.contact_m)
        assert (weights / c).min() >= (1.0 - p_valid) - 1e-9

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
        combined = dhi.CombinedUpdate(prior_pos, float(post.r_dhi), 1.0, dependence=0.5)
        assert combined.posterior_pos < prior_pos * 0.5


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

    def test_everything_above_the_cutoff_is_equally_consistent(self):
        """The claim is a bound, not a depth. Above the cutoff no contact is preferred, which is
        what separates this from a pick — a pick peaks somewhere and this must not."""
        result, post = self._at(2250.0, p_valid=1.0)
        h_off = 2250.0 - result.apex_m
        above = result.column_m <= h_off
        assert above.sum() > 50, "the fixture needs realisations on both sides of the cutoff"
        # Above the cutoff the only variation left is D(h) itself, so the bound contributes a
        # constant. Divide it out and what remains must be flat.
        detection = DetectionFunction()
        bound_factor = post.weights[above] / detection.at(result.column_m[above])
        assert np.allclose(bound_factor, bound_factor[0])

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
        assert below < dhi.MIN_FAILURES_FOR_R
        assert np.isnan(post.r_dhi), f"{below} failures should not support a ratio"

    def test_it_is_defined_where_the_minimum_is_a_real_threshold(self):
        post = self._posterior(180.0)
        assert int((~post.result.above_minimum).sum()) >= dhi.MIN_FAILURES_FOR_R
        assert np.isfinite(post.r_dhi) and post.r_dhi > 1.0

    def test_a_neutral_strength_leaves_pos_exactly_alone(self):
        """The whole point. With the geometry channel undefined, the combination falls back to
        strength alone — and a strength of 0 is a likelihood ratio of exactly 1."""
        combined = dhi.CombinedUpdate(prior_pos=0.408, r_geometry=float("nan"),
                                      r_strength=1.0, dependence=0.5)
        assert combined.posterior_pos == pytest.approx(0.408, abs=1e-12)

    @pytest.mark.parametrize("dependence", [0.0, 0.5, 1.0])
    def test_neutral_stays_neutral_at_every_dependence(self, dependence):
        combined = dhi.CombinedUpdate(prior_pos=0.408, r_geometry=float("nan"),
                                      r_strength=1.0, dependence=dependence)
        assert combined.posterior_pos == pytest.approx(0.408, abs=1e-12)

    def test_a_defined_geometry_channel_still_moves_it(self):
        """The guard must not have switched the channel off everywhere."""
        combined = dhi.CombinedUpdate(prior_pos=0.408, r_geometry=2.34, r_strength=1.0,
                                      dependence=0.5)
        assert combined.posterior_pos > 0.408


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
