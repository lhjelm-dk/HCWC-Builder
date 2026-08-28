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
