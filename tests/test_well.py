"""Well control — the one observation about a contact that needs no argument.

A DHI is an inference and tab 5.0 spends four sub-tabs earning it. A logged water leg is a
measurement. These tests are about the arithmetic keeping that distinction: the fluid call is
reliable, its *relevance* to the segment being assessed is not, and only the second is uncertain.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from hcwc.core import dhi, engine, well
from hcwc.core.limits import reference_prospect
from hcwc.core.well import WellControl


@pytest.fixture(scope="module")
def result():
    return engine.run(reference_prospect(), 8000, 4242)


class TestWhatItRefuses:
    def test_a_penetration_that_saw_nothing_is_not_evidence(self):
        with pytest.raises(ValueError, match="at least one depth"):
            WellControl()

    def test_hydrocarbons_below_the_water_leg_is_two_accumulations(self):
        with pytest.raises(ValueError, match="must be above the water"):
            WellControl(hc_down_to_m=2300.0, water_at_m=2250.0)

    def test_the_depth_uncertainty_must_be_positive(self):
        with pytest.raises(ValueError, match="depth uncertainty must be positive"):
            WellControl(water_at_m=2250.0, depth_sigma_m=0.0)

    @pytest.mark.parametrize("p", [0.0, -0.1, 1.5])
    def test_connectivity_is_a_probability(self, p):
        with pytest.raises(ValueError, match="p_connected"):
            WellControl(water_at_m=2250.0, p_connected=p)


class TestTheDirectionOfTheEvidence:
    def test_water_argues_the_contact_is_shallower(self, result):
        w = well.likelihood(result, WellControl(water_at_m=2250.0, p_connected=1.0))
        deeper, shallower = result.contact_m > 2280.0, result.contact_m < 2220.0
        assert deeper.any() and shallower.any()
        assert w[deeper].mean() < 0.25 * w[shallower].mean()

    def test_hydrocarbons_argue_the_contact_is_deeper(self, result):
        w = well.likelihood(result, WellControl(hc_down_to_m=2250.0, p_connected=1.0))
        deeper, shallower = result.contact_m > 2280.0, result.contact_m < 2220.0
        assert w[shallower].mean() < 0.25 * w[deeper].mean()

    def test_a_bracket_is_sharper_than_either_half(self, result):
        """The appraisal case, and the reason to support both depths at once."""
        def spread(observation):
            w = well.likelihood(result, observation)
            post = dhi.DhiPosterior(result=result, weights=w,
                                    detection=dhi.DetectionFunction(),
                                    observation=dhi.DhiObservation(seen=False))
            lo, hi = post.percentiles([90.0, 10.0])
            return hi - lo

        # Placed inside the prior's bulk. Put the bracket out in a tail and the floor takes over
        # instead -- see the saturation test below, which is a real property rather than a caveat.
        lo, hi = (float(np.percentile(result.contact_m, p)) for p in (35.0, 65.0))
        both = spread(WellControl(hc_down_to_m=lo, water_at_m=hi))
        assert both < spread(WellControl(water_at_m=hi))
        assert both < spread(WellControl(hc_down_to_m=lo))

    def test_an_observation_the_model_finds_impossible_reverts_to_the_prior(self, result):
        """The same saturation the partial-conformance DHI has, and for the same reason.

        Once the bracket sits where the prior has almost no mass, every realisation is penalised by
        the same amount, the likelihood goes flat at its floor, and the posterior comes back to the
        prior. That is correct Bayes and a trap for a reader: it looks like the well said nothing,
        when what happened is that the well contradicted the model outright.
        """
        far = float(np.percentile(result.contact_m, 99.5))
        w = well.likelihood(result, WellControl(hc_down_to_m=far + 60.0, water_at_m=far + 90.0))
        assert w.max() / w.min() < 1.05, "the likelihood should be nearly flat out here"
        prior_p50 = float(np.median(result.contact_m))
        assert abs(np.average(result.contact_m, weights=w) - prior_p50) < 0.05 * prior_p50

    def test_an_observation_below_everything_says_almost_nothing(self, result):
        deep = float(result.contact_m.max()) + 200.0
        w = well.likelihood(result, WellControl(water_at_m=deep, p_connected=1.0))
        assert np.allclose(w, w[0], atol=1e-6)


class TestTheFloor:
    @pytest.mark.parametrize("p_connected", [0.3, 0.6, 0.9, 0.99])
    def test_cromwell_holds_however_certain_the_log_was(self, result, p_connected):
        """A penetration can never rule a contact out. The fluid call is reliable; whether it
        belongs to this accumulation is not, and the floor is where that doubt lives."""
        w = well.likelihood(result, WellControl(water_at_m=2250.0, p_connected=p_connected))
        assert w.min() >= (1.0 - p_connected) - 1e-12

    def test_connectivity_doubt_weakens_the_update_monotonically(self, result):
        def moved(p_connected):
            w = well.likelihood(result, WellControl(water_at_m=2230.0, p_connected=p_connected))
            return abs(np.average(result.contact_m, weights=w) - result.contact_m.mean())

        assert moved(0.4) < moved(0.7) < moved(1.0)

    def test_a_wider_depth_tie_blurs_the_step(self, result):
        sharp = well.likelihood(result, WellControl(water_at_m=2250.0, depth_sigma_m=2.0))
        blurred = well.likelihood(result, WellControl(water_at_m=2250.0, depth_sigma_m=60.0))
        just_below = (result.contact_m > 2250.0) & (result.contact_m < 2270.0)
        assert just_below.any()
        assert blurred[just_below].mean() > sharp[just_below].mean()


class TestWhatItDoesNotClaim:
    def test_water_alone_says_nothing_about_whether_the_prospect_works(self):
        """Water down-dip is entirely consistent with a column up-dip. The interface reads this to
        decide whether to raise the question of the element chances at all."""
        assert not WellControl(water_at_m=2250.0).proves_hydrocarbons

    def test_a_proven_column_is_flagged_rather_than_acted_on(self):
        """Hydrocarbons proven in the closure make the prospect a discovery, which is a much larger
        statement than anything about depth. The module surfaces it and does not touch P(G)."""
        assert WellControl(hc_down_to_m=2200.0).proves_hydrocarbons

    def test_it_reweights_rather_than_adding_a_limit(self, result):
        """A penetration observes the outcome of the mechanisms already modelled; it is not a new
        mechanism. So the realisations, and the controlling-limit bookkeeping, are untouched."""
        w = well.likelihood(result, WellControl(water_at_m=2250.0))
        assert w.shape == (result.n,)
        assert len(result.limit_set.limits) == len(reference_prospect().limits)


class TestCombiningChannels:
    def test_a_well_and_a_dhi_multiply(self, result):
        d = dhi.likelihood(result, dhi.DetectionFunction(),
                           dhi.DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=18.0,
                                              p_valid=0.6))
        w = well.likelihood(result, WellControl(water_at_m=2250.0))
        assert np.allclose(well.combine(d, w), d * w)

    def test_combining_nothing_is_refused(self):
        with pytest.raises(ValueError, match="nothing to combine"):
            well.combine()

    def test_evidence_that_disagrees_widens_the_answer(self, result):
        """Agreement narrows, disagreement widens — and a reader will check this by eye.

        This lived as an app-level test against the shipped defaults until those defaults moved the
        contact 76 m and stranded its hard-coded depths. The property is about the combination, not
        about any prospect, so it belongs here where both sides can be placed deliberately.
        """
        def spread(w):
            post = dhi.DhiPosterior(result=result, weights=w, detection=dhi.DetectionFunction(),
                                    observation=dhi.DhiObservation(seen=False))
            lo, hi = post.percentiles([90.0, 10.0])
            return hi - lo

        pick_at = float(np.percentile(result.contact_m, 50))
        d = dhi.likelihood(result, dhi.DetectionFunction(),
                           dhi.DhiObservation(seen=True, contact_m=pick_at, pick_sigma_m=15.0,
                                              p_valid=0.8))
        agrees = well.likelihood(result, WellControl(hc_down_to_m=pick_at - 20.0,
                                                     water_at_m=pick_at + 20.0))
        disagrees = well.likelihood(result, WellControl(water_at_m=pick_at - 60.0))
        assert spread(well.combine(d, agrees)) < spread(d)
        assert spread(well.combine(d, disagrees)) > spread(d)

    def test_two_channels_land_between_what_each_says_alone(self, result):
        """Not a law of probability, but the sanity check a reader will apply: a well arguing
        shallow and a pick arguing deep should meet somewhere between them."""
        def p50(w):
            post = dhi.DhiPosterior(result=result, weights=w, detection=dhi.DetectionFunction(),
                                    observation=dhi.DhiObservation(seen=False))
            return post.percentiles(50.0)[0]

        d = dhi.likelihood(result, dhi.DetectionFunction(),
                           dhi.DhiObservation(seen=True, contact_m=2280.0, pick_sigma_m=18.0,
                                              p_valid=0.8))
        w = well.likelihood(result, WellControl(water_at_m=2240.0))
        assert min(p50(d), p50(w)) <= p50(well.combine(d, w)) <= max(p50(d), p50(w))


class TestTheDepthIsTiedToTheApexTheModelUses:
    def test_moving_the_apex_moves_what_the_observation_means(self, result):
        """The well reports a depth in m TVDSS and the model competes in column height. Nothing is
        being compared until the two are on the same datum."""
        w = well.likelihood(result, WellControl(water_at_m=2250.0, p_connected=1.0))
        # `contact_m` is derived from the apex, so the apex is what there is to move.
        deeper = dataclasses.replace(result, apex_m=result.apex_m + 80.0)
        assert not np.allclose(w, well.likelihood(deeper, WellControl(water_at_m=2250.0,
                                                                     p_connected=1.0)))


class TestOneWellHasOneTieError:
    """Audit finding P3-5, 15 Sep 2026.

    The bracket was `Φ(a) · Φ(b)`, the form for two independent tie errors. A well's two depths
    are tied to the mapped surface by the same error, so the chance the contact lies between
    them is `P(z − z_w ≤ ε ≤ z − z_hc) = Φ(a) + Φ(b) − 1`. The difference is small on the
    defaults and it is the right expression.
    """

    def test_the_bracket_is_the_difference_of_two_cumulatives(self, result):
        from scipy.stats import norm
        control = WellControl(hc_down_to_m=2200.0, water_at_m=2260.0, depth_sigma_m=20.0,
                              p_connected=1.0)
        got = well.likelihood(result, control)
        a = (result.contact_m - 2200.0) / 20.0
        b = (2260.0 - result.contact_m) / 20.0
        expected = np.clip(norm.cdf(a) + norm.cdf(b) - 1.0, 0.0, 1.0)
        assert np.allclose(got, expected)

    def test_the_shared_form_is_never_above_the_product_form(self, result):
        """`Φa + Φb − 1 ≤ Φa·Φb` because `(1 − Φa)(1 − Φb) ≥ 0`: one error cannot make the
        bracket more likely than two independent ones would."""
        from scipy.stats import norm
        control = WellControl(hc_down_to_m=2200.0, water_at_m=2260.0, depth_sigma_m=20.0,
                              p_connected=1.0)
        got = well.likelihood(result, control)
        a = (result.contact_m - 2200.0) / 20.0
        b = (2260.0 - result.contact_m) / 20.0
        assert np.all(got <= norm.cdf(a) * norm.cdf(b) + 1e-12)

    def test_a_single_depth_is_a_single_step_either_way(self, result):
        from scipy.stats import norm
        got = well.likelihood(result, WellControl(water_at_m=2250.0, depth_sigma_m=15.0,
                                                  p_connected=1.0))
        assert np.allclose(got, norm.cdf((2250.0 - result.contact_m) / 15.0))
