"""The charge branch, against an independently computed reference case.

The area–depth integration is deterministic, so it is exact parity. The fluid conversions are
arithmetic and are checked against the same case. What is deliberately *not* reproduced is a lookup
that runs off the end of the table — the tests below pin the correction rather than that behaviour.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hcwc.core import charge
from hcwc.core.charge import AreaDepthTable

# The shipped case's reservoir properties, `HCWC from Volume Charge`!I13:K13.
NTG, POR, SAT = 0.65, 0.25, 0.65
K = NTG * POR * SAT
BO, GOR, INV_BG, CGR = 1.35, 400.0, 235.0, 17.1


@pytest.fixture(scope="module")
def table() -> AreaDepthTable:
    return AreaDepthTable.reference()


class TestAreaDepthIntegration:
    def test_the_table_is_the_reference_one(self, table):
        assert table.depths_m.size == 37
        assert table.apex_m == 2040.0
        assert table.deepest_m == 2400.0

    def test_grv_reproduces_the_cached_column_exactly(self, table):
        cached = pd.read_csv(charge.REFERENCE / "area_depth.csv",
                             comment="#").grv_1e6m3_cached.to_numpy(float)
        assert np.allclose(table.grv_1e6m3, cached, rtol=1e-9, atol=1e-9)

    def test_capacity_matches_the_last_cached_value(self, table):
        assert table.capacity_1e6m3 == pytest.approx(1506.99994, rel=1e-9)

    def test_hcpv_at_the_base_matches_the_sheet(self, table):
        """`M49` = GRV x NTG x phi x Sh."""
        assert table.capacity_1e6m3 * K == pytest.approx(159.17687, rel=1e-6)

    def test_grv_starts_at_zero_and_increases(self, table):
        grv = table.grv_1e6m3
        assert grv[0] == 0.0
        assert np.all(np.diff(grv) > 0)

    def test_a_base_area_above_the_top_area_is_refused(self):
        with pytest.raises(ValueError, match="swapped"):
            AreaDepthTable(np.array([0.0, 10.0]), np.array([0.0, 1.0]), np.array([0.0, 2.0]))

    def test_depths_must_ascend(self):
        with pytest.raises(ValueError, match="must increase"):
            AreaDepthTable(np.array([10.0, 0.0]), np.array([1.0, 0.0]), np.array([0.0, 0.0]))


class TestChargeBeyondTheTable:
    """The correction: charge that fills past the table is not a limit, not a limit at the base.

    A lookup range that extends past the 37-row table runs into blanks, so where charge exceeds
    capacity the interpolation extrapolates **below the mapped structure**: a gas contact at
    2540.7 m and a mixed-separate oil–water contact at 3702.5 m, against a base of 2400 m. Those
    are not contacts, and here they are infinity.
    """

    def test_charge_beyond_capacity_returns_infinity(self, table):
        beyond = table.capacity_1e6m3 * K * 1.5
        got = charge.oil_contact(table, np.array([beyond / BO / K * K]), np.array([BO]),
                                 np.array([K])).contact_m
        assert np.isinf(got[0])

    def test_it_never_returns_a_depth_below_the_table(self, table):
        volumes = np.linspace(0.0, table.capacity_1e6m3 * K * 3.0, 400)
        got = table.depth_at_grv(volumes / K)
        finite = got[np.isfinite(got)]
        assert finite.max() <= table.deepest_m + 1e-9
        assert not np.any((got > table.deepest_m) & np.isfinite(got))

    def test_the_gas_case_is_flagged_rather_than_extrapolated(self, table):
        """`G6` = 168.5 against a capacity of 159.2, so charge is not limiting."""
        res = charge.gas_contact(table, np.array([39600.0]), np.array([INV_BG]), np.array([K]))
        assert res.reservoir_volume_1e6m3[0] == pytest.approx(168.5106, rel=1e-4)
        assert res.reservoir_volume_1e6m3[0] > table.capacity_1e6m3 * K
        assert res.not_limiting[0]
        assert np.isinf(res.contact_m[0])

    def test_a_non_limiting_charge_loses_the_minimum(self, table):
        """The reason infinity is the right answer: it cannot win an argmin against a real limit."""
        res = charge.gas_contact(table, np.array([39600.0]), np.array([INV_BG]), np.array([K]))
        spill = 2400.0
        assert min(res.contact_m[0], spill) == spill


class TestOil:
    def test_the_shipped_case_reproduces(self, table):
        """139.5 x 1e6 m3 of reservoir volume -> a contact at 2353.66 m, inside the table."""
        res = charge.oil_contact(table, np.array([650.0 / 6.29]), np.array([BO]), np.array([K]))
        assert res.reservoir_volume_1e6m3[0] == pytest.approx(139.5072, rel=1e-4)
        assert res.contact_m[0] == pytest.approx(2353.66, abs=0.5)

    def test_more_charge_fills_deeper(self, table):
        v = np.array([50.0, 80.0, 110.0])
        got = charge.oil_contact(table, v, np.full(3, BO), np.full(3, K)).contact_m
        assert np.all(np.diff(got) > 0)

    def test_no_charge_leaves_the_contact_at_the_apex(self, table):
        got = charge.oil_contact(table, np.array([0.0]), np.array([BO]), np.array([K])).contact_m
        assert got[0] == pytest.approx(table.apex_m)

    def test_a_worse_reservoir_needs_more_rock_for_the_same_charge(self, table):
        good = charge.oil_contact(table, np.array([80.0]), np.array([BO]), np.array([K]))
        poor = charge.oil_contact(table, np.array([80.0]), np.array([BO]), np.array([K * 0.5]))
        assert poor.contact_m[0] > good.contact_m[0]


class TestGas:
    def test_conversion_uses_inverse_bg(self, table):
        res = charge.gas_contact(table, np.array([20000.0]), np.array([INV_BG]), np.array([K]))
        assert res.reservoir_volume_1e6m3[0] == pytest.approx(20000.0 / INV_BG)

    def test_a_non_positive_inverse_bg_is_refused(self, table):
        with pytest.raises(ValueError, match="1/Bg"):
            charge.gas_contact(table, np.array([100.0]), np.array([0.0]), np.array([K]))


class TestMixedSeparate:
    def test_the_gas_oil_contact_sits_above_the_oil_water_contact(self, table):
        res = charge.mixed_separate(table, np.array([30.0]), np.array([8000.0]),
                                    np.array([BO]), np.array([INV_BG]), np.array([K]))
        assert res.gas_oil_contact_m[0] < res.contact_m[0]

    def test_the_owc_is_set_by_the_total_volume(self, table):
        res = charge.mixed_separate(table, np.array([30.0]), np.array([8000.0]),
                                    np.array([BO]), np.array([INV_BG]), np.array([K]))
        total = 30.0 * BO + 8000.0 / INV_BG
        assert res.reservoir_volume_1e6m3[0] == pytest.approx(total)
        assert res.contact_m[0] == pytest.approx(
            charge.oil_contact(table, np.array([total / BO]), np.array([BO]),
                               np.array([K])).contact_m[0])


class TestMixedJoint:
    def test_the_split_recovers_the_totals(self, table):
        """O + CGR x Q = total oil, and GOR x O + Q = total gas."""
        total_oil, total_gas = 103.34, 38800.0
        cgr = CGR / 1e6
        oil = (total_oil - cgr * total_gas) / (1.0 - cgr * GOR)
        free_gas = total_gas - GOR * oil
        assert oil + cgr * free_gas == pytest.approx(total_oil, rel=1e-9)
        assert GOR * oil + free_gas == pytest.approx(total_gas, rel=1e-9)

    def test_the_shipped_case_has_no_free_gas_cap(self, table):
        """Q = -2553: every molecule of gas is accounted for as solution gas."""
        res = charge.mixed_joint(table, np.array([103.34]), np.array([38800.0]),
                                 np.array([GOR]), np.array([CGR]), np.array([BO]),
                                 np.array([INV_BG]), np.array([K]))
        assert np.isnan(res.gas_oil_contact_m[0]), (
            "no free gas means no gas-oil contact, not one at the apex")

    def test_a_gas_rich_case_does_have_a_cap(self, table):
        res = charge.mixed_joint(table, np.array([20.0]), np.array([30000.0]),
                                 np.array([GOR]), np.array([CGR]), np.array([BO]),
                                 np.array([INV_BG]), np.array([K]))
        assert np.isfinite(res.gas_oil_contact_m[0])
        assert res.gas_oil_contact_m[0] < res.contact_m[0]

    def test_a_degenerate_cgr_gor_product_is_refused(self, table):
        with pytest.raises(ValueError, match="cannot be separated"):
            charge.mixed_joint(table, np.array([100.0]), np.array([1000.0]),
                               np.array([1e6 / CGR]), np.array([CGR]), np.array([BO]),
                               np.array([INV_BG]), np.array([K]))


class TestVectorisation:
    def test_the_whole_thing_runs_on_a_realisation_array(self, table):
        rng = np.random.default_rng(1)
        n = 20_000
        res = charge.oil_contact(table,
                                 rng.normal(650.0 / 6.29, 168.0 / 6.29, n),
                                 rng.normal(BO, 0.05, n),
                                 rng.normal(K, 0.01, n).clip(0.01))
        assert res.contact_m.size == n
        assert np.isfinite(res.contact_m).mean() > 0.5
        finite = res.contact_m[np.isfinite(res.contact_m)]
        assert finite.min() >= table.apex_m
        assert finite.max() <= table.deepest_m + 1e-9

    def test_column_heights_pass_infinity_through(self):
        contacts = np.array([2200.0, np.inf, 2350.0])
        got = charge.column_height_from_contact(contacts, np.full(3, 2050.0))
        assert got[0] == pytest.approx(150.0)
        assert np.isinf(got[1])


class TestAsAnEngineLimit:
    """The charge branch has no closed form, so it enters the engine as a quantile table."""

    def samples(self, table):
        rng = np.random.default_rng(3)
        res = charge.oil_contact(table, rng.normal(103.3, 26.7, 20_000).clip(0.0),
                                 np.full(20_000, BO), np.full(20_000, K))
        return res, charge.column_height_from_contact(res.contact_m, table.apex_m)

    def test_it_round_trips_through_a_quantile_table(self, table):
        from hcwc.core.limits import DepthDistribution
        _, columns = self.samples(table)
        dist = DepthDistribution.from_samples(columns)
        drawn = dist.ppf(np.random.default_rng(0).random(50_000))
        finite = columns[np.isfinite(columns)]
        assert np.median(drawn) == pytest.approx(np.median(finite), rel=0.02)
        assert drawn.min() >= finite.min() - 1e-6
        assert drawn.max() <= finite.max() + 1e-6

    def test_the_quantile_table_serialises(self, table):
        from hcwc.core.limits import DepthDistribution
        _, columns = self.samples(table)
        d = DepthDistribution.from_samples(columns)
        assert DepthDistribution.from_dict(d.to_dict()) == d

    def test_non_limiting_realisations_go_to_p_active_not_the_table(self, table):
        """Infinity is a statement about *whether* charge binds, not about *where*."""
        from hcwc.core.limits import DepthDistribution
        res, columns = self.samples(table)
        assert res.fraction_not_limiting > 0.1
        dist = DepthDistribution.from_samples(columns)
        assert np.all(np.isfinite(dist.ppf(np.linspace(0, 1, 101))))
        assert max(dist.params["value"]) <= table.deepest_m - table.apex_m + 1e-9

    def test_a_charge_that_never_binds_is_refused_rather_than_flattened(self, table):
        from hcwc.core.limits import DepthDistribution
        with pytest.raises(ValueError, match="remove the row"):
            DepthDistribution.from_samples(np.array([np.inf, np.inf, np.inf]))

    def test_a_handover_carries_a_distribution_and_a_probability(self, table):
        """The contract every source obeys, and the reason one Source column can stand for all.

        The split is the point: the distribution carries *where* a mechanism bites, the probability
        carries *whether* it does. Charge makes it vivid — a charge filling past the deepest mapped
        depth is not a shallow limit, it is no limit.
        """
        from hcwc.core.limits import DepthDistribution
        from hcwc.ui.sources import Handover
        res, columns = self.samples(table)
        h = Handover(DepthDistribution.from_samples(columns),
                     1.0 - res.fraction_not_limiting, "Pure oil")
        assert 0.0 < h.p_active < 1.0
        assert h.distribution.kind == "empirical"
        assert h.summary

    def test_a_handover_builds_a_working_limit(self, table):
        from hcwc.core import engine
        from hcwc.core.limits import (DepthDistribution, Group, Limit, LimitSet,
                                      reference_prospect)
        res, columns = self.samples(table)
        base = reference_prospect()
        swapped = tuple(
            Limit("Charge", Group.CHARGE, 1.0 - res.fraction_not_limiting,
                  DepthDistribution.from_samples(columns), "computed: Pure oil")
            if x.name == "Charge" else x
            for x in base.limits)
        ls = LimitSet(apex=base.apex, limits=swapped, name=base.name)
        r = engine.run(ls, 20_000)
        assert np.isfinite(r.column_m).all()
        assert r.controlling_shares()["Charge"] > 0.0

    def test_every_calculator_is_reachable_from_at_least_one_limit(self):
        """A calculator nobody can open is dead weight, and one silently *became* dead in the
        tab-③ rebuild: the empirical NCS source survived in `sources.py` while the new tab offered
        only charge and seal, so it was code with no route to it for two days.
        """
        from hcwc.ui.limiters_tab import COMPUTED, SPECS
        named = {spec.computed for spec in SPECS if spec.computed}
        # "empirical" is offered on every column-stated limit rather than named in SPECS.
        assert named | {"empirical"} == set(COMPUTED)
        assert all(callable(fn) for fn in COMPUTED.values())
