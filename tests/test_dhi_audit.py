"""The mathematical audit of the DHI model, 16 Sep 2026.

The architecture under audit, in the order the chain runs:

    A.  P(G | strength)             the character channel updates the chance of hydrocarbons
    B.  p(h | G, geometry)          ∝ p(h | G) · L(geometry | h, G), the pick within G
    C.  POS(h) = P(G | strength) · P(H ≥ h | G, geometry)

One set of weights from B supplies the histogram, the percentiles, the exceedance curve and the
conditional term in C. The strength never enters B; the geometry never updates G; nothing is
counted twice. Each class below pins one of the audit's items with its limiting cases, so a
future change that breaks the architecture fails here by name rather than on a report sheet.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from hcwc.core import dhi, engine
from hcwc.core.dhi import DetectionFunction, DhiObservation
from hcwc.core.limits import LimitSet, reference_prospect

N = 40_000
P_G = 0.408


def run(min_column_m: float = 100.0):
    base = reference_prospect()
    return engine.run(LimitSet(apex=base.apex, limits=base.limits, name=base.name,
                               min_column_m=min_column_m), N)


@pytest.fixture(scope="module")
def result():
    return run(120.0)


def _spread(post, *, posterior=True):
    """P90-to-P10 width of the contact, in metres, the tab's measure of depth uncertainty."""
    p = post.percentiles(np.array([90.0, 10.0]), posterior=posterior)
    return float(p[1] - p[0])


# --------------------------------------------------------------------------- 1 · p_valid
class TestMonigleRuleIsAComparisonOnly:
    """`w = min(2 x score, 0.95)`, Monigle et al. (2025), shown beside the slider and the
    graded attributes (Lars, 17 Sep 2026). A source of c, not a change to what c does."""

    def test_the_rule_doubles_the_score_and_stops_at_the_ceiling(self):
        assert dhi.contact_weight_from_score(0.10) == pytest.approx(0.20)
        assert dhi.contact_weight_from_score(0.18) == pytest.approx(0.36)
        assert dhi.contact_weight_from_score(0.475) == pytest.approx(0.95)
        assert dhi.contact_weight_from_score(0.50) == dhi.CONTACT_WEIGHT_CEILING
        assert dhi.contact_weight_from_score(1.00) == dhi.CONTACT_WEIGHT_CEILING

    def test_the_ceiling_is_hoods_and_monigles_0_95(self):
        assert dhi.CONTACT_WEIGHT_CEILING == 0.95

    def test_the_default_score_gives_the_shipped_c(self):
        """An untouched third route agrees with an untouched slider."""
        from hcwc.ui import dhi_tab
        assert dhi.contact_weight_from_score(dhi_tab.DEFAULT_DHI_SCORE) == pytest.approx(
            dhi_tab.DEFAULT_CONTACT_GIVEN_HC)

    def test_a_score_outside_0_to_1_is_clipped_not_raised(self):
        assert dhi.contact_weight_from_score(-0.2) == 0.0
        assert dhi.contact_weight_from_score(3.0) == dhi.CONTACT_WEIGHT_CEILING


class TestPValidIsAContactAttributeJudgementOnly:
    """`p_valid = P(the picked event is the HCWC | G, contact attributes)`. It must not contain
    P(G | strength), and it must not depend on the column height."""

    def test_the_likelihood_never_sees_the_strength(self, result):
        """The weights are a function of the observation and the detection function alone."""
        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.36)
        w = dhi.likelihood(result, DetectionFunction(), obs)
        # There is no argument to pass a strength through; the signature is the proof. What the
        # chain does with the strength is one multiplication in C.
        for r in (0.1, 1.0, 10.0):
            post = dhi.update(result, DetectionFunction(), obs)
            np.testing.assert_array_equal(post.weights, w)
            assert dhi.prospect_pos(P_G, r, post) == pytest.approx(
                dhi.p_g_given_strength(P_G, r) * post.pos(), abs=1e-15)

    def test_the_mixture_weight_is_the_same_at_every_column_height(self, result):
        """Item 6: c is independent of h within the model. The likelihood is exactly
        `c · valid(h) + (1 − c) · s` with one c for every realisation, so solving for c from any
        two realisations returns the number typed."""
        det = DetectionFunction()
        c = 0.36
        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=c)
        valid = det.at(result.column_m) * obs.pick_pdf(result.contact_m)
        s = dhi.spurious_density(result.limit_set.contact_support_m())
        expected = c * valid + (1.0 - c) * s
        np.testing.assert_allclose(dhi.likelihood(result, det, obs), expected, rtol=0, atol=1e-18)
        # And the implied c per realisation, where the valid branch differs from s, is constant.
        got = dhi.likelihood(result, det, obs)
        distinct = np.abs(valid - s) > 1e-9
        implied = (got[distinct] - s) / (valid[distinct] - s)
        np.testing.assert_allclose(implied, c, rtol=1e-9)

    def test_p_valid_at_one_is_the_pick_alone_and_at_the_floor_is_nearly_flat(self, result):
        """Item 8: p_valid → 1 removes the floor; p_valid → 0 removes the pick."""
        det = DetectionFunction()
        pick = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=1.0)
        w1 = dhi.likelihood(result, det, pick)
        np.testing.assert_allclose(w1, det.at(result.column_m) * pick.pick_pdf(result.contact_m))
        nearly_none = dataclasses.replace(pick, p_valid=1e-6)
        post = dhi.update(result, det, nearly_none)
        # The posterior is the prior to within the share the pick is still allowed.
        assert abs(post.pos() - post.pos(posterior=False)) < 1e-3
        assert abs(_spread(post) - _spread(post, posterior=False)) < 1.0


# --------------------------------------------------------------------------- 2 · seen likelihood
class TestTheSeenLikelihoodIsCoherent:
    """`L = c · D(h) · f_pick(z | h) + (1 − c) · s`: both branches are densities in depth, and
    `s` comes from the declared support, not the sample."""

    def test_both_branches_are_densities_in_depth(self, result):
        """Scaling the depth axis by a factor scales both branches by its inverse: a density.
        Checked by integrating each branch over depth and getting a dimensionless number."""
        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.36)
        z = np.linspace(1500.0, 3500.0, 200_001)
        pick_mass = float(np.trapezoid(obs.pick_pdf(z), z))
        assert pick_mass == pytest.approx(1.0, abs=1e-6)
        lo, hi = result.limit_set.contact_support_m()
        s = dhi.spurious_density((lo, hi))
        assert s * (hi - lo) == pytest.approx(1.0)

    def test_the_spurious_density_is_one_over_the_declared_span(self, result):
        lo, hi = result.limit_set.contact_support_m()
        assert dhi.spurious_density((lo, hi)) == pytest.approx(1.0 / (hi - lo))
        # Not the sampled range: the two differ, and the likelihood uses the declared one.
        sampled = 1.0 / (float(result.contact_m.max()) - float(result.contact_m.min()))
        assert sampled != pytest.approx(dhi.spurious_density((lo, hi)), rel=1e-3)

    def test_the_floor_is_exactly_what_the_mixture_says(self, result):
        """`L / s ≥ 1 − c` everywhere, with equality where the pick is far away."""
        det, c = DetectionFunction(), 0.36
        obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=c)
        s = dhi.spurious_density(result.limit_set.contact_support_m())
        ratio = dhi.likelihood(result, det, obs) / s
        assert np.all(ratio >= (1.0 - c) - 1e-12)
        far = np.abs(result.contact_m - 2250.0) > 8 * 15.0
        assert far.any()
        np.testing.assert_allclose(ratio[far], 1.0 - c, atol=1e-9)


# --------------------------------------------------------------------------- 3 · partial
class TestPartialConformanceIsASoftCensoredBound:
    """The valid branch is `D(h) · Φ((z_off − z) / σ)`, a probability of the event *edge above
    z_off*; the spurious branch is the constant 1, the same event's probability in the world
    where the bright thing is not the column. Both are probabilities, so the mixture is coherent,
    and the constant 1 is the conservative choice: the highest floor the mixture can have."""

    def setup_method(self):
        self.det = DetectionFunction()
        self.obs = DhiObservation(seen=True, absent_below_m=2250.0, pick_sigma_m=15.0,
                                  p_valid=0.36)

    def test_the_valid_branch_is_a_probability_in_zero_one(self, result):
        valid = dhi.likelihood(result, self.det, dataclasses.replace(self.obs, p_valid=1.0))
        assert np.all(valid >= 0.0) and np.all(valid <= self.det.ceiling + 1e-12)

    def test_the_mixture_is_c_times_valid_plus_one_minus_c(self, result):
        valid = dhi.likelihood(result, self.det, dataclasses.replace(self.obs, p_valid=1.0))
        got = dhi.likelihood(result, self.det, self.obs)
        np.testing.assert_allclose(got, 0.36 * valid + 0.64, atol=1e-15)

    def test_it_is_soft_and_never_zero(self, result):
        """A column far below the cutoff keeps `1 − c` of the likelihood, not zero."""
        got = dhi.likelihood(result, self.det, self.obs)
        deep = result.contact_m > 2250.0 + 6 * 15.0
        assert deep.any()
        np.testing.assert_allclose(got[deep], 0.64, atol=1e-9)
        assert got.min() > 0.0

    def test_it_is_weaker_than_a_pick_at_the_same_depth(self, result):
        """A censored bound cannot sharpen the contact more than a pick at the cutoff does."""
        bound = dhi.update(result, self.det, self.obs)
        pick = dhi.update(result, self.det, DhiObservation(seen=True, contact_m=2250.0,
                                                          pick_sigma_m=15.0, p_valid=0.36))
        assert _spread(bound) >= _spread(pick)


# --------------------------------------------------------------------------- 4 · absence
class TestAbsenceIsSplitBetweenTheTwoChannels:
    """`P(absent | G) / P(absent | not G)` is evidence on G; `1 − D(h)` reshapes the column."""

    def test_the_weights_are_one_minus_d_and_nothing_else(self, result):
        det = DetectionFunction()
        w = dhi.likelihood(result, det, DhiObservation(seen=False))
        np.testing.assert_allclose(w, 1.0 - det.at(result.column_m), atol=1e-15)

    def test_the_chance_is_updated_by_the_absence_ratio_not_the_strength(self, result):
        det = DetectionFunction()
        obs = DhiObservation(seen=False)
        for r_strength in (0.1, 1.0, 10.0):
            assert dhi.applied_ratio(result, det, obs, r_strength) == pytest.approx(
                dhi.absence_ratio(result, det))

    def test_the_ratio_is_the_stated_form_and_the_false_positive_is_the_elicited_input(self,
                                                                                        result):
        d = float(np.mean(DetectionFunction().at(result.column_m)))
        for f in (0.0, 0.5, 1.0):
            det = DetectionFunction(false_positive=f)
            expected = np.clip((1.0 - d) / (1.0 - f * d), 1.0 / dhi.R_SINGLE_CHANNEL, 1.0)
            assert dhi.absence_ratio(result, det) == pytest.approx(float(expected))
        assert DetectionFunction().false_positive == 0.5, "the maximum-ignorance default moved"

    def test_absence_within_g_shallows_the_contact_without_touching_the_chance_factor(self,
                                                                                     result):
        det = DetectionFunction()
        post = dhi.update(result, det, DhiObservation(seen=False))
        assert post.percentiles(50.0)[0] <= post.percentiles(50.0, posterior=False)[0]
        # The chance's first factor is the absence ratio applied once, in C.
        pos = dhi.prospect_pos(P_G, dhi.absence_ratio(result, det), post)
        assert pos == pytest.approx(dhi.simm_update(P_G, dhi.absence_ratio(result, det))
                                    * post.pos(), abs=1e-15)


# --------------------------------------------------------------------------- 5 · strength
class TestStrengthMovesTheChanceAndNotTheDepth:
    def setup_method(self):
        self.det = DetectionFunction()
        self.obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.36)

    def test_neutral_strength_leaves_p_g_alone(self, result):
        """Item 8: neutral strength → no change in P(G)."""
        assert dhi.p_g_given_strength(P_G, 1.0) == P_G
        post = dhi.update(result, self.det, self.obs)
        assert dhi.prospect_pos(P_G, 1.0, post) == pytest.approx(P_G * post.pos(), abs=1e-15)

    def test_the_strongest_allowed_strength_raises_p_g_to_its_cap_and_leaves_the_depth_spread(
            self, result):
        """Item 8: very strong positive strength → P(G) approaches its bound, and the HCWC keeps
        its pick and depth uncertainty. The bound is the single-channel cap, 10 : 1, so P(G)
        cannot reach 1 from one line of evidence; that is Simm's ceiling, by design."""
        post = dhi.update(result, self.det, self.obs)
        r_max = dhi.StrengthModel().r_at(100.0)   # the axis end; further out both curves underflow
        assert r_max == dhi.R_SINGLE_CHANNEL
        p_strong = dhi.p_g_given_strength(P_G, r_max)
        assert p_strong > 0.85 and p_strong < 1.0
        assert p_strong == pytest.approx(r_max * P_G / (r_max * P_G + 1 - P_G))
        # Depth uncertainty is untouched by the strength: same weights, same spread, and the
        # spread is a real number of metres, not zero.
        assert _spread(post) > 10.0
        for r in (1.0, r_max):
            assert dhi.outcome(result, self.det, self.obs, p_g=P_G, r_strength=r).contact_m \
                == float(post.percentiles(50.0)[0])

    def test_a_weak_dhi_leaves_the_posterior_close_to_the_geology(self, result):
        """Item 8: weak DHI → posterior remains close to geological. A near-neutral strength and
        a pick with a low c and a broad sigma move neither factor by much."""
        weak = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=200.0, p_valid=0.05)
        post = dhi.update(result, self.det, weak)
        assert abs(post.pos() - post.pos(posterior=False)) < 0.02
        assert abs(float(post.percentiles(50.0)[0] - post.percentiles(50.0, posterior=False)[0])) \
            < 5.0
        r_weak = dhi.StrengthModel().r_at(dhi.DEFAULT_STRENGTH * 0.1)
        assert abs(dhi.p_g_given_strength(P_G, r_weak) - P_G) < 0.02


# --------------------------------------------------------------------------- 8 · pick width
class TestThePickWidthLimits:
    def setup_method(self):
        self.det = DetectionFunction()

    def test_a_very_broad_pick_returns_the_geology(self, result):
        """Item 8: very broad pick uncertainty → the valid branch is nearly flat across the
        support, so the posterior equals the prior to within a small tolerance."""
        broad = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=5_000.0, p_valid=0.9)
        post = dhi.update(result, self.det, broad)
        assert abs(post.pos() - post.pos(posterior=False)) < 0.02
        assert abs(_spread(post) - _spread(post, posterior=False)) < 5.0

    def test_a_very_narrow_pick_concentrates_the_valid_share_and_keeps_the_floor(self, result):
        """Item 8: very narrow pick uncertainty → the posterior concentrates near the pick, but
        the floor keeps `1 − c` of the mass spread as the geology had it, so the spread does not
        collapse to zero and no realisation is ruled out."""
        c = 0.36
        narrow = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=0.5, p_valid=c)
        post = dhi.update(result, self.det, narrow)
        assert post.weights.min() > 0.0
        assert _spread(post) < _spread(post, posterior=False)
        assert _spread(post) > 0.0
        # The posterior mass within ±2 m of the pick is large but bounded by what the pick can
        # buy against the floor: the valid branch cannot claim more than c / (1 − c) : 1 per
        # unit of spurious density, and the floor spreads the rest.
        keep = result.above_minimum
        near = np.abs(result.contact_m[keep] - 2250.0) < 2.0
        share_near = float(post.weights[keep][near].sum() / post.weights[keep].sum())
        assert 0.0 < share_near < 1.0

    def test_a_neutral_geometry_likelihood_returns_the_geology_exactly(self, result):
        """Item 8: neutral geometry likelihood → posterior HCWC equals geological. Constant
        weights are the identity update, whatever the constant."""
        post = dhi.DhiPosterior(result=result, weights=np.full(result.n, 0.37))
        assert post.pos() == pytest.approx(post.pos(posterior=False), abs=1e-12)
        for p in (90.0, 50.0, 10.0):
            assert float(post.percentiles(p)[0]) == pytest.approx(
                float(post.percentiles(p, posterior=False)[0]), abs=1e-9)
        grid = np.linspace(0.0, float(result.column_m.max()), 50)
        np.testing.assert_allclose(post.exceedance(grid), post.exceedance(grid, posterior=False),
                                   atol=1e-12)


# --------------------------------------------------------------------------- 9 · consistency
class TestTheCriticalConsistencyIdentity:
    """headline POS = P(G | strength) × posterior_HCWC_exceedance(h_min), and one set of weights
    produces the histogram, the percentiles, the curve and the chance."""

    R = 1.4

    def setup_method(self):
        self.det = DetectionFunction()
        self.obs = DhiObservation(seen=True, contact_m=2250.0, pick_sigma_m=15.0, p_valid=0.36)

    def test_the_identity_holds_in_the_core(self, result):
        post = dhi.update(result, self.det, self.obs)
        h_min = result.limit_set.min_column_m
        w = post.weights
        f_post = float(w[result.column_m >= h_min].sum() / w.sum())
        headline = dhi.prospect_pos(P_G, self.R, post)
        assert headline == pytest.approx(dhi.p_g_given_strength(P_G, self.R) * f_post, abs=1e-12)
        assert float(dhi.prospect_pos_curve(P_G, self.R, post, np.array([h_min]))[0]) \
            == pytest.approx(headline, abs=1e-15)
        # The histogram the tab draws is `np.histogram(contact_m, weights=w)`: the same w.
        edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 61)
        counts, _ = np.histogram(result.contact_m, bins=edges, weights=w)
        deep_edge = edges[np.searchsorted(edges, float(np.median(result.apex_m)) + h_min)]
        mass_below_edge = counts[edges[:-1] >= deep_edge].sum() / counts.sum()
        # Same object, read coarsely: the binned mass at and below the threshold agrees with the
        # exact weighted share to within one bin's worth of contacts.
        assert abs(mass_below_edge - f_post) < 0.06

    @pytest.mark.render
    def test_the_well_reads_the_same_on_tab_5_2_4_and_tab_5_3_4(self):
        """Lars, 21 Sep 2026: at a 2 230 m well tab 5.2.4 read 36.1 % and tab 5.3.4 read 31.5 %.
        Both are P(well) given the DHI; 5.3.4 had kept the geological P(G) with the posterior r.
        The comparison table now takes P(G | s) from the overlay and the two agree."""
        import pathlib

        from streamlit.testing.v1 import AppTest

        from hcwc.core import decompose, engine

        app = pathlib.Path(__file__).resolve().parent.parent / "app.py"
        at = AppTest.from_file(str(app), default_timeout=900)
        at.run()
        assert not at.exception, "\n".join(str(e.value) for e in at.exception)
        overlay = at.session_state["dhi_overlay"]
        post = at.session_state["dhi_posterior"]
        pos = at.session_state["element_pos"]
        z = 2230.0
        # Tab 5.2.4: P(G | s) times the weighted exceedance at the entry depth.
        r_post = float(engine.exceedance(post.result.contact_m, np.array([z]), post.weights)[0])
        well_515 = float(overlay["p_g_given_amplitude"]) * r_post
        # Tab 5.3.4: the comparison table built the way the tab builds it.
        d = decompose.decompose(post.result, weights=post.weights)
        comp = decompose.allocation_comparison(d, pos, z,
                                               p_g_updated=float(overlay["p_g_given_amplitude"]))
        assert comp["allocated::P_well"] == pytest.approx(well_515, abs=2e-3)
        assert comp["allocated::P_well"] > float(np.prod(list(pos.values()))) * r_post + 0.02, (
            "the given-the-DHI well chance must carry the index update, not the prior P(G)")

    @pytest.mark.render
    def test_the_identity_holds_on_the_rendered_tab(self):
        """The app's own numbers: the overlay tab 5.1 writes for tabs 4 and 6 carries the
        headline, the updated element chance, the threshold and the weights. The headline must be
        the product of the element chance and the weighted exceedance at the threshold, computed
        from the stored weights on the run's own realisations, and the histogram figure's bars
        must be those weights binned."""
        import pathlib

        from streamlit.testing.v1 import AppTest

        from hcwc.ui import numbering

        app = pathlib.Path(__file__).resolve().parent.parent / "app.py"
        at = AppTest.from_file(str(app), default_timeout=900)
        at.session_state["dhi_in_strength"] = 25.0
        at.run()
        assert not at.exception, "\n".join(str(e.value) for e in at.exception)

        overlay = at.session_state["dhi_overlay"]
        post = at.session_state["dhi_posterior"]
        w = np.asarray(overlay["weights"], dtype=float)
        np.testing.assert_array_equal(w, post.weights)
        res = post.result
        h_min = float(overlay["h_min"])
        f_post = float(w[res.column_m >= h_min].sum() / w.sum())
        assert float(overlay["posterior_pos"]) == pytest.approx(
            float(overlay["p_g_given_amplitude"]) * f_post, abs=1e-12)
        # The chance curve the overlay carries passes through the headline at h_min.
        depths = np.asarray(overlay["depths_m"], dtype=float)
        curve = np.asarray(overlay["pos_curve"], dtype=float)
        apex = float(np.median(res.apex_m))
        at_h_min = float(np.interp(apex + h_min, depths, curve))
        assert at_h_min == pytest.approx(float(overlay["posterior_pos"]), abs=2e-3)

        # The posterior histogram on tab 5.1 is the weights binned on the run's contacts.
        figures = at.session_state[numbering.FIGURES_KEY]
        # The posterior contact histogram: the first tab-5.1 figure whose traces are two
        # horizontal bar series, one geological and one given the evidence.
        label = next(k for k, (fig, _) in figures.items()
                     if k.startswith("Figure 5.1.")
                     and len(fig.data) == 2
                     and all(getattr(t, "orientation", None) == "h" for t in fig.data)
                     and str(fig.data[0].name).lower().startswith("geological"))
        fig = figures[label][0]
        updated = fig.data[1]
        edges = np.linspace(float(res.contact_m.min()), float(res.contact_m.max()), 61)
        counts, _ = np.histogram(res.contact_m, bins=edges, weights=w)
        np.testing.assert_allclose(np.asarray(updated.x, dtype=float), counts / counts.sum(),
                                   atol=1e-12)
