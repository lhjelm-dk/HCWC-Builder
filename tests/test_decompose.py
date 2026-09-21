"""The per-element decomposition, and the identity it is checked against.

The central claim is that the element curves multiply back to the contact distribution when the
limits are independent. That is testable exactly, so it is tested exactly — and the cases where it
*should* fail (dependent limits, a shared apex, reservoir effectiveness) are tested too, because a
consistency check that can never fail is not a check.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.core import decompose, engine
from hcwc.core.decompose import ELEMENTS, ReservoirEffectiveness
from hcwc.core.limits import DepthDistribution, Group, Limit, LimitSet, reference_prospect

N = 60_000


def limit(name: str, group: Group, lo: float, hi: float, p: float = 1.0) -> Limit:
    return Limit(name, group, p,
                 DepthDistribution("uniform", {"minimum": lo, "maximum": hi}))


def fixed_apex(depth: float = 2000.0) -> DepthDistribution:
    return DepthDistribution("fixed", {"value": depth})


def two_element_set(apex: DepthDistribution | None = None) -> LimitSet:
    return LimitSet(apex=apex or fixed_apex(), limits=(
        limit("charge", Group.CHARGE, 0.0, 400.0),
        limit("spill", Group.CLOSURE, 0.0, 600.0),
    ))


class TestTheIdentity:
    """`prod_e P_e(z) = P(contact > z)` when the limits are independent."""

    def test_it_holds_in_column_space(self):
        d = decompose.decompose(engine.run(two_element_set(), N))
        assert d.max_abs_residual_column < 0.01

    def test_it_holds_in_depth_space_when_the_apex_is_certain(self):
        d = decompose.decompose(engine.run(two_element_set(), N))
        assert d.max_abs_residual_depth < 0.01

    def test_the_product_matches_the_analytic_answer(self):
        """Two independent uniforms: `P(min > z) = (1 - z/400)(1 - z/600)`."""
        d = decompose.decompose(engine.run(two_element_set(), N))
        for z in (50.0, 150.0, 250.0):
            i = int(np.argmin(np.abs(d.columns_m - z)))
            expect = max(0.0, 1 - z / 400.0) * max(0.0, 1 - z / 600.0)
            assert d.direct_column[i] == pytest.approx(expect, abs=0.01)
            assert d.product_column[i] == pytest.approx(expect, abs=0.01)

    def test_every_element_gets_a_curve(self):
        d = decompose.decompose(engine.run(reference_prospect(), 20_000))
        present = {g for g in ELEMENTS if reference_prospect().indices_in(g).size}
        assert set(d.by_element_depth) == present
        assert set(d.by_element_column) == present

    def test_curves_are_monotone_decreasing_with_depth(self):
        d = decompose.decompose(engine.run(reference_prospect(), 20_000))
        for element, curve in d.by_element_depth.items():
            assert np.all(np.diff(curve) <= 1e-12), f"{element} is not monotone"

    def test_an_element_that_never_binds_is_absent_not_flat(self):
        d = decompose.decompose(engine.run(reference_prospect(), 5000))
        assert Group.RESERVOIR not in d.by_element_depth


class TestWhenTheIdentityShouldFail:
    """A check that cannot fail is not a check."""

    def test_a_shared_apex_breaks_the_depth_space_identity(self):
        """Elements share one apex draw, so their *contact* curves are dependent.

        The columns stay independent, so column space is unaffected — which is what makes the
        difference between the two residuals a clean measure of the apex's contribution.
        """
        wide_apex = DepthDistribution("normal_alt",
                                      {"p1": 0.01, "x1": 1600.0, "p2": 0.99, "x2": 2400.0})
        d = decompose.decompose(engine.run(two_element_set(wide_apex), N))
        assert d.max_abs_residual_column < 0.02, "column space stays clean"
        assert d.max_abs_residual_depth > 0.03, "depth space should not"
        assert d.apex_contribution > 0.02

    def test_the_apex_contribution_grows_with_apex_uncertainty(self):
        got = []
        for half_width in (5.0, 100.0, 400.0):
            apex = DepthDistribution("normal_alt", {"p1": 0.01, "x1": 2000.0 - half_width,
                                                    "p2": 0.99, "x2": 2000.0 + half_width})
            got.append(decompose.decompose(
                engine.run(two_element_set(apex), 30_000)).apex_contribution)
        assert got[0] < got[1] < got[2]

    def test_a_certain_apex_leaves_no_apex_contribution(self):
        d = decompose.decompose(engine.run(two_element_set(), N))
        assert abs(d.apex_contribution) < 0.01

    def test_a_tightly_picked_apex_is_narrow_enough_to_ignore(self):
        """2049-2051 m. On an apex this tight the subtlety can be left unremarked."""
        d = decompose.decompose(engine.run(reference_prospect(), N))
        assert abs(d.apex_contribution) < 0.02


class TestReservoirEffectiveness:
    def test_off_by_default(self):
        r = ReservoirEffectiveness()
        assert not r.active
        assert np.allclose(r.at(np.array([1000.0, 5000.0])), 1.0)

    def test_it_ramps_between_the_two_depths(self):
        r = ReservoirEffectiveness(full_to_m=3000.0, none_below_m=4000.0)
        assert r.at(np.array([2500.0]))[0] == pytest.approx(1.0)
        assert r.at(np.array([3500.0]))[0] == pytest.approx(0.5)
        assert r.at(np.array([4500.0]))[0] == pytest.approx(0.0)

    def test_an_inverted_pair_is_refused(self):
        with pytest.raises(ValueError, match="cannot stop being effective"):
            ReservoirEffectiveness(full_to_m=4000.0, none_below_m=3000.0)

    def test_it_does_not_move_the_contact(self):
        """R1 is not a limit. It must not appear in the contact distribution."""
        result = engine.run(reference_prospect(), 20_000)
        plain = decompose.decompose(result)
        damped = decompose.decompose(result, reservoir=ReservoirEffectiveness(2100.0, 2300.0))
        assert np.allclose(plain.direct_depth, damped.direct_depth)
        assert np.allclose(plain.product_depth, damped.product_depth)

    def test_it_does_reduce_the_chance_at_depth(self):
        result = engine.run(reference_prospect(), 20_000)
        pos = {g: 1.0 for g in ELEMENTS}
        plain = decompose.decompose(result).direct_pos(pos)
        damped = decompose.decompose(
            result, reservoir=ReservoirEffectiveness(2100.0, 2300.0)).direct_pos(pos)
        assert np.all(damped <= plain + 1e-12)
        # Compare in the middle of the ramp. At the deepest grid point both are zero, because no
        # realisation is deeper than the deepest realisation — nothing to reduce.
        d = decompose.decompose(result)
        i = int(np.argmin(np.abs(d.depths_m - 2250.0)))
        assert damped[i] < plain[i]


class TestFactorisedVersusDirect:
    """The factorised and direct readings, and the double-count their gap would expose."""

    POS = {Group.CHARGE: 0.9, Group.CLOSURE: 1.0, Group.RESERVOIR: 0.6, Group.RETENTION: 0.8}

    def test_they_agree_for_independent_limits(self):
        d = decompose.decompose(engine.run(two_element_set(), N))
        pos = {Group.CHARGE: 0.9, Group.CLOSURE: 0.8}
        assert np.max(np.abs(d.factorised_pos(pos) - d.direct_pos(pos))) < 0.02

    def test_the_gap_is_the_residual_scaled(self):
        d = decompose.decompose(engine.run(reference_prospect(), 20_000))
        pos = {Group.CHARGE: 0.9, Group.CLOSURE: 1.0, Group.RETENTION: 0.8}
        gap = d.factorised_pos(pos) - d.direct_pos(pos)
        scale = 0.9 * 1.0 * 0.8
        assert np.max(np.abs(gap - scale * d.residual_depth)) < 1e-9

    def test_an_element_with_no_limit_still_carries_its_chance(self):
        """Audit finding P0-1, 14 Sep 2026.

        The reference prospect has no Reservoir limit. An element with no limit never controls
        the contact, so its depth curve is one everywhere -- but its element chance is still a
        factor of the prospect chance. `element_pos_at_depth` used to leave such an element out
        of the dict, and `factorised_pos` and the derived P(well) then ran without its chance:
        with P(Reservoir) = 0.6 the derived P(well) was 1 / 0.6 times the allocated one, and the
        comparison on tab 4.2 was of two different quantities.
        """
        d = decompose.decompose(engine.run(reference_prospect(), 20_000))
        assert Group.RESERVOIR not in d.by_element_depth
        curves = d.element_pos_at_depth(self.POS)
        assert Group.RESERVOIR in curves
        np.testing.assert_allclose(curves[Group.RESERVOIR], 0.6)
        gap = d.factorised_pos(self.POS) - d.direct_pos(self.POS)
        scale = 0.9 * 1.0 * 0.6 * 0.8
        assert np.max(np.abs(gap - scale * d.residual_depth)) < 1e-9

    def test_derived_and_allocated_p_well_agree_when_limits_are_independent(self):
        """The two columns of the comparison table are the same number up to the residual, and
        that has to hold with an element chance on an element that has no limit."""
        d = decompose.decompose(engine.run(reference_prospect(), 20_000))
        out = decompose.allocation_comparison(d, self.POS, 2230.0)
        assert out["derived::P_well"] == pytest.approx(out["allocated::P_well"], abs=0.01)
        assert out["derived::Reservoir"] == pytest.approx(0.6)

    def test_element_pos_scales_the_curves(self):
        d = decompose.decompose(engine.run(reference_prospect(), 10_000))
        curves = d.element_pos_at_depth(self.POS)
        for element, curve in curves.items():
            if element is Group.RESERVOIR:
                continue
            assert np.allclose(curve, self.POS[element] * d.by_element_depth[element])

    def test_a_missing_element_defaults_to_certain(self):
        d = decompose.decompose(engine.run(reference_prospect(), 5000))
        assert np.allclose(d.factorised_pos({}), d.product_depth)


class TestAllocationComparison:
    """Derived curves against the allocation WellVolPOS would apply to the same run."""

    POS = {Group.CHARGE: 0.9, Group.CLOSURE: 1.0, Group.RESERVOIR: 0.6, Group.RETENTION: 0.8}

    def test_both_routes_report_a_well_chance(self):
        d = decompose.decompose(engine.run(reference_prospect(), 20_000))
        out = decompose.allocation_comparison(d, self.POS, 2200.0)
        assert 0.0 <= out["derived::P_well"] <= 1.0
        assert 0.0 <= out["allocated::P_well"] <= 1.0

    def test_the_allocation_preserves_the_product_by_construction(self):
        """WellVolPOS's schemes all reproduce the same P_well; only the split differs."""
        d = decompose.decompose(engine.run(reference_prospect(), 20_000))
        out = decompose.allocation_comparison(d, self.POS, 2200.0)
        rebuilt = np.prod([out[f"allocated::{e.value}"] for e in ELEMENTS])
        assert rebuilt == pytest.approx(out["allocated::P_well"], rel=1e-9)

    def test_the_derived_split_can_disagree_with_the_allocated_one(self):
        """The whole point: the derived curves carry information the allocation cannot."""
        d = decompose.decompose(engine.run(reference_prospect(), 20_000))
        out = decompose.allocation_comparison(d, self.POS, 2250.0)
        assert any(abs(out[f"derived::{e.value}"] - out[f"allocated::{e.value}"]) > 0.02
                   for e in (Group.CHARGE, Group.CLOSURE, Group.RETENTION))

    def test_it_picks_the_nearest_depth_on_the_grid(self):
        d = decompose.decompose(engine.run(reference_prospect(), 5000), n_points=50)
        deep = decompose.allocation_comparison(d, self.POS, float(d.depths_m[-1]))
        shallow = decompose.allocation_comparison(d, self.POS, float(d.depths_m[0]))
        assert shallow["r_location"] > deep["r_location"]

    # -- the index update, spread by the rule (Lars, 21 Sep 2026) ---------------------------------

    def test_without_an_updated_p_g_nothing_changes(self):
        d = decompose.decompose(engine.run(reference_prospect(), 5000))
        a = decompose.allocation_comparison(d, self.POS, 2230.0)
        b = decompose.allocation_comparison(d, self.POS, 2230.0, p_g_updated=None)
        assert a == b
        assert a["p_g_applied"] == pytest.approx(0.9 * 1.0 * 0.6 * 0.8)

    def test_given_the_dhi_p_well_is_p_g_given_s_times_r(self):
        """The defect of 21 Sep 2026: tab 5.3.4 read P(G) x r_post where 5.1.5 read P(G | s) x
        r_post. The comparison now takes the updated chance and reproduces it in the total."""
        d = decompose.decompose(engine.run(reference_prospect(), 5000))
        out = decompose.allocation_comparison(d, self.POS, 2230.0, p_g_updated=0.55)
        assert out["p_g_applied"] == pytest.approx(0.55, rel=1e-9)
        applied = decompose.element_pos_given_index(self.POS, 0.55)
        assert np.prod(list(applied.values())) == pytest.approx(0.55, rel=1e-9)
        assert applied[Group.CLOSURE] == 1.0 and applied[Group.RESERVOIR] == 0.6
        assert out["allocated::P_well"] == pytest.approx(0.55 * out["r_location"], rel=1e-12)
        rebuilt = np.prod([out[f"allocated::{e.value}"] for e in ELEMENTS])
        assert rebuilt == pytest.approx(out["allocated::P_well"], rel=1e-9)

    def test_element_pos_given_index_is_the_identity_without_an_update(self):
        out = decompose.element_pos_given_index(self.POS, None)
        assert out == {e: self.POS[e] for e in ELEMENTS}

    def test_the_spread_is_the_shipped_rule_when_the_factor_is_at_most_one(self):
        out = decompose.spread_by_rule(self.POS, 0.5)
        for e in (Group.CHARGE, Group.CLOSURE, Group.RETENTION):
            assert out[e] == pytest.approx(self.POS[e] * 0.5 ** (1 / 3))
        assert out[Group.RESERVOIR] == self.POS[Group.RESERVOIR]

    def test_an_element_is_held_at_one_and_passes_its_share_on(self):
        """Closure ships at 1.00, so any factor above one caps it; the excess goes to the other
        two, and the product of the four is still the target."""
        out = decompose.spread_by_rule(self.POS, 1.2)
        assert out[Group.CLOSURE] == 1.0
        assert out[Group.RESERVOIR] == self.POS[Group.RESERVOIR]
        assert out[Group.CHARGE] > self.POS[Group.CHARGE]
        assert out[Group.RETENTION] > self.POS[Group.RETENTION]
        assert np.prod(list(out.values())) == pytest.approx(0.9 * 0.6 * 0.8 * 1.2, rel=1e-9)

    def test_reservoir_takes_a_share_only_when_the_other_three_are_at_one(self):
        out = decompose.spread_by_rule(self.POS, 1.9)
        assert all(out[e] == 1.0 for e in (Group.CHARGE, Group.CLOSURE, Group.RETENTION))
        assert out[Group.RESERVOIR] == pytest.approx(0.9 * 0.6 * 0.8 * 1.9, rel=1e-9)

    def test_the_spread_never_exceeds_one_anywhere(self):
        out = decompose.spread_by_rule(self.POS, 10.0)
        assert all(v <= 1.0 + 1e-12 for v in out.values())


class TestLimitCurvesAtDepth:
    """The sub-element breakdown: one curve per *mechanism*, not per risk element.

    What it answers that the element curves cannot: at 2 200 m, is it the top seal or the fault
    that is costing you the column? The element view aggregates that away by construction, because
    it takes the shallowest active limit *within* the element.
    """

    @pytest.fixture(scope="class")
    def result(self):
        from hcwc.core import engine
        from hcwc.core.limits import reference_prospect
        return engine.run(reference_prospect(), 20_000)

    def test_there_is_one_curve_per_limit(self, result):
        depths = np.linspace(2000.0, 2500.0, 50)
        curves = decompose.limit_curves_at_depth(result, depths)
        assert set(curves) == set(result.limit_set.names)
        assert all(c.shape == depths.shape for c in curves.values())

    def test_each_curve_falls_with_depth(self, result):
        depths = np.linspace(2000.0, 2500.0, 60)
        for name, curve in decompose.limit_curves_at_depth(result, depths).items():
            assert (np.diff(curve) <= 1e-12).all(), f"{name} is not monotone"

    def test_a_curve_flattens_at_its_own_p_active(self, result):
        """The reason the curve is deliberately *not* conditional on the limit being active.

        A limit that only exists in half the realisations flattens at 0.50, and reading that
        straight off the axis tells you the mechanism is optional. The conditional form normalises
        that away and makes a rare severe limit look like a common mild one.
        """
        depths = np.linspace(2000.0, 4000.0, 200)
        curves = decompose.limit_curves_at_depth(result, depths)
        for limit in result.limit_set.limits:
            if limit.p_active < 1.0:
                # Deep enough that the limit has certainly bitten if it was ever going to.
                assert curves[limit.name][-1] == pytest.approx(1.0 - limit.p_active, abs=0.02), \
                    f"{limit.name} should flatten at 1 - p_active"

    def test_no_limit_curve_sits_below_the_contact_curve(self, result):
        """The contact is the *minimum* over limits, so every individual limit must be at least as
        likely to be deeper than any given depth as the contact is. A violation would mean the
        engine's argmin and this decomposition disagree about the same realisations."""
        depths = np.linspace(2000.0, 2600.0, 80)
        contact = (result.contact_m[None, :] > depths[:, None]).mean(axis=1)
        for name, curve in decompose.limit_curves_at_depth(result, depths).items():
            assert (curve >= contact - 1e-9).all(), f"{name} falls below the contact curve"

    def test_the_element_curve_respects_the_frechet_bound_on_its_limits(self, result):
        """The curve of the minimum is **not** the minimum of the curves, and conflating them is an
        easy way to get a decomposition subtly wrong.

        An element bites where its *shallowest active* limit does, so
        ``P(element deeper than z) = P(every one of its limits is deeper than z)``, which is at most
        ``min_j P(limit j deeper than z)`` -- the Frechet upper bound, with equality only if the
        limits are perfectly dependent. It equals the **product** only under independence, and on
        this prospect the correlated seal pairs push it a couple of points above that. Both
        relations are asserted so a future indexing slip cannot satisfy one by accident.
        """
        d = decompose.decompose(result)
        per_limit = decompose.limit_curves_at_depth(result, d.depths_m)
        checked = 0
        for group, element_curve in d.by_element_depth.items():
            members = [per_limit[x.name] for x in result.limit_set.limits if x.group is group]
            if not members:
                continue
            checked += 1
            # The Frechet bound is exact and holds realisation by realisation, so it gets a tight
            # tolerance.
            assert (element_curve <= np.minimum.reduce(members) + 1e-9).all(), group
            # The product is only the *independent* case, and it is compared across two separate
            # Monte Carlo estimates, so it gets a sampling tolerance. At 20 000 trials one standard
            # error on a probability near 0.5 is about 0.0035; 0.02 is a few of those. This is a
            # sanity band, not an identity -- correlated limits genuinely depart from it.
            assert np.allclose(element_curve, np.prod(members, axis=0), atol=0.02), group
        assert checked >= 2, "the fixture no longer has a multi-limit element to test"

    def test_a_single_limit_element_is_exactly_its_one_curve(self, result):
        """Charge has one limit, so the bound above collapses to equality. If it does not, the two
        levels are not looking at the same realisations."""
        from hcwc.core.limits import Group
        d = decompose.decompose(result)
        per_limit = decompose.limit_curves_at_depth(result, d.depths_m)
        singles = [x for x in result.limit_set.limits if x.group is Group.CHARGE]
        assert len(singles) == 1
        assert np.allclose(d.by_element_depth[Group.CHARGE], per_limit[singles[0].name], atol=1e-9)


class TestWeightedDecomposition:
    """The DHI-updated decomposition, and the boundary it must not cross.

    Reweighting the whole decomposition by `DhiPosterior.weights` looks, at first glance, like
    exactly what E-POS's resolution ceiling forbids. It is not, and the distinction is the point:

    * *Given the prospect failed, which element failed?* A fluid indicator cannot say. The element
      **chances** are inputs and this module never touches them.
    * *Given it worked and the contact is here, which mechanism stopped it there?* The contact depth
      is **observed** and the controlling limit is coupled to it — ordinary inference.

    So: multipliers fixed, curves reweight. These tests hold that line.
    """

    @pytest.fixture(scope="class")
    def result(self):
        import dataclasses
        from hcwc.core import engine
        from hcwc.core.limits import reference_prospect
        return engine.run(dataclasses.replace(reference_prospect(), min_column_m=40.0), 20_000)

    @staticmethod
    def _weights(result):
        from hcwc.core import dhi
        post = dhi.update(
            result, dhi.DetectionFunction(h50_m=25.0, steepness_m=8.0, ceiling=0.9),
            dhi.DhiObservation(seen=True,
                               contact_m=float(np.percentile(result.contact_m, 35)),
                               pick_sigma_m=20.0))
        return post.weights

    def test_uniform_weights_reproduce_the_unweighted_decomposition(self):
        """The identity that makes the feature safe: weighting by a constant must change nothing,
        or every posterior curve carries a silent offset from the reweighting itself."""
        import dataclasses
        from hcwc.core import engine
        from hcwc.core.limits import reference_prospect
        result = engine.run(dataclasses.replace(reference_prospect(), min_column_m=40.0), 4_000)
        plain = decompose.decompose(result)
        weighted = decompose.decompose(result, weights=np.ones(result.n))
        for group, curve in plain.by_element_depth.items():
            assert np.allclose(curve, weighted.by_element_depth[group])
        assert np.allclose(plain.direct_depth, weighted.direct_depth)

    def test_the_curves_move_and_the_multipliers_do_not(self, result):
        """The resolution ceiling, enforced rather than promised. `element_pos_at_depth` scales by
        the chances from tab 2.0; those are an argument, so the posterior cannot touch them, and only
        the shape underneath may change."""
        from hcwc.core.limits import Group
        pos = {Group.CHARGE: 0.9, Group.CLOSURE: 1.0,
               Group.RESERVOIR: 0.63, Group.RETENTION: 0.72}
        weights = self._weights(result)
        plain = decompose.decompose(result)
        updated = decompose.decompose(result, weights=weights)

        before = plain.element_pos_at_depth(pos)
        after = updated.element_pos_at_depth(pos)

        # Every curve is still capped by its own element chance — the multiplier is intact.
        for group, value in pos.items():
            if group in after:
                assert after[group].max() <= value + 1e-9

        # And at least one element genuinely moved, or the reweighting is doing nothing.
        assert any(not np.allclose(before[g], after[g], atol=1e-3) for g in before)

    def test_the_depth_grid_is_shared_so_the_two_can_be_overlaid(self, result):
        """Tab 7.0 draws geological and posterior on one figure. If the grids differed it would have
        to interpolate, and an interpolation between two curves that are already estimates is a
        third thing neither of them is."""
        weights = self._weights(result)
        assert np.allclose(decompose.decompose(result).depths_m,
                           decompose.decompose(result, weights=weights).depths_m)

    def test_per_limit_curves_take_the_same_weights(self, result):
        depths = np.linspace(2100.0, 2400.0, 60)
        weights = self._weights(result)
        plain = decompose.limit_curves_at_depth(result, depths)
        updated = decompose.limit_curves_at_depth(result, depths, weights)
        assert set(plain) == set(updated)
        assert any(not np.allclose(plain[k], updated[k], atol=1e-3) for k in plain)

    def test_degenerate_weights_fall_back_rather_than_dividing_by_zero(self, result):
        """A posterior can collapse — an impossible observation drives every weight to zero. The
        honest response is the prior, not a NaN curve that renders as a blank figure."""
        zeros = decompose.decompose(result, weights=np.zeros(result.n))
        assert np.allclose(zeros.direct_depth, decompose.decompose(result).direct_depth)


class TestTiesAndInterpolation:
    """Audit findings P3-2 and P3-6, 15 Sep 2026."""

    def test_the_shallowest_grid_point_counts_every_realisation(self):
        """`>=`, as the engine: at the shallowest contact the exceedance is 1, not `1 − 1/n`."""
        d = decompose.decompose(engine.run(reference_prospect(), 2_000))
        assert d.direct_depth[0] == pytest.approx(1.0)

    def test_the_entry_depth_is_interpolated_rather_than_snapped(self):
        d = decompose.decompose(engine.run(reference_prospect(), 5_000))
        i = len(d.depths_m) // 2
        z0, z1 = float(d.depths_m[i]), float(d.depths_m[i + 1])
        r0 = decompose.allocation_comparison(d, {}, z0)["r_location"]
        r1 = decompose.allocation_comparison(d, {}, z1)["r_location"]
        mid = decompose.allocation_comparison(d, {}, 0.5 * (z0 + z1))["r_location"]
        assert r0 == pytest.approx(float(d.direct_depth[i]))
        assert mid == pytest.approx(0.5 * (r0 + r1))
