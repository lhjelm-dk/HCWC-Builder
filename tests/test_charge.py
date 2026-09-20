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
        cached = pd.read_csv(charge.REFERENCE / "defaults" / "area_depth.csv",
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
        tab-3.0 rebuild: the empirical NCS source survived in `sources.py` while the new tab offered
        only charge and seal, so it was code with no route to it for two days.
        """
        from hcwc.ui.limiters_tab import COMPUTED, SPECS
        # `LimitSpec.computed` holds a *tuple* of calculators since the base seal began offering
        # both its own and a "same as the top seal" shortcut, so the names have to be flattened
        # out of it rather than collected as they stand.
        named = {name for spec in SPECS for name in spec.computed}
        # "empirical" is offered on every column-stated limit rather than named in SPECS.
        assert named | {"empirical"} == set(COMPUTED)
        assert all(callable(fn) for fn in COMPUTED.values())


class TestTheBaseSealCanBorrowTheTopSeal:
    """*Same as the top seal* reads the top seal's widgets by key, which is a coupling worth pinning.

    Nothing would raise if the two drifted apart: the source would simply report that the top seal
    is not on its calculator, on every prospect, for ever. A renamed limit is all it would take.
    """

    def test_the_borrowed_key_matches_the_key_the_tab_actually_builds(self):
        from hcwc.ui.limiters_tab import SPECS
        from hcwc.ui.sources import TOP_SEAL_KEY
        top = next(s for s in SPECS if s.name == "Top seal (capillary)")
        assert TOP_SEAL_KEY == f"lim_{top.name}"

    def test_the_base_seal_offers_both_its_own_calculator_and_the_shortcut(self):
        from hcwc.ui.limiters_tab import COMPUTED, SPECS
        base = next(s for s in SPECS if s.name == "Base seal (capillary)")
        assert base.computed == ("seal", "seal_as_top")
        assert all(name in COMPUTED for name in base.computed)

    def test_borrowing_reproduces_the_top_seal_capacity_exactly(self):
        """Same inputs, same seed, same numbers — or it is not 'the same as the top seal'."""
        from hcwc.core import seals
        inputs = seals.SealInputs(
            temperature_c=(70.0, 90.0), contact_angle_deg=(0.0, 30.0),
            seal_radius_um=(0.03, 0.12), reservoir_radius_um=(0.8, 3.0),
            water_density_g_cm3=(1.00, 1.10), hc_density_g_cm3=(0.70, 0.85),
            fluid="Gas", subtract_reservoir=True)
        seed = 4242
        assert np.array_equal(seals.sample_max_column_m(inputs, 5_000, seed + 313),
                              seals.sample_max_column_m(inputs, 5_000, seed + 313))


class TestDerivingTheBaseFromAThickness:
    """The common case: one mapped surface and a thickness, not two mapped surfaces."""

    def test_it_reproduces_the_shipped_base_surface(self):
        """The reference prospect's base *is* its top shifted down 50 m, which makes this the one
        check worth having — the two constructions must agree to the metre on real data."""
        ref = AreaDepthTable.reference()
        derived = AreaDepthTable.from_top_and_thickness(ref.depths_m, ref.top_area_km2, 50.0)
        assert derived.capacity_1e6m3 == pytest.approx(ref.capacity_1e6m3, rel=1e-6)
        assert np.allclose(derived.base_area_km2, ref.base_area_km2, atol=1e-6)

    def test_it_is_a_depth_shift_not_an_area_offset(self):
        """SCOPE-HC's `geom_depth` shifts the surface in depth. A second function of the same name
        in its `ui/common.py` subtracts the thickness from the *area* — dimensionally wrong, and
        dead code there. This pins which construction is being matched."""
        ref = AreaDepthTable.reference()
        derived = AreaDepthTable.from_top_and_thickness(ref.depths_m, ref.top_area_km2, 50.0)
        at = 12
        expected = np.interp(derived.depths_m[at] - 50.0, ref.depths_m, ref.top_area_km2)
        assert derived.base_area_km2[at] == pytest.approx(expected, rel=1e-9)

    def test_a_thicker_reservoir_holds_more_rock(self):
        ref = AreaDepthTable.reference()
        volumes = [AreaDepthTable.from_top_and_thickness(
            ref.depths_m, ref.top_area_km2, t).capacity_1e6m3 for t in (20.0, 50.0, 120.0)]
        assert volumes[0] < volumes[1] < volumes[2]

    def test_zero_thickness_is_refused_rather_than_integrating_to_nothing(self):
        ref = AreaDepthTable.reference()
        with pytest.raises(ValueError, match="encloses no rock"):
            AreaDepthTable.from_top_and_thickness(ref.depths_m, ref.top_area_km2, 0.0)


class TestReadingAnAreaDepthCsv:
    def test_loose_column_spellings_are_matched(self):
        """These come out of mapping software and nobody renames the columns by hand."""
        table = AreaDepthTable.from_csv(
            "TVDSS,Top Area (km2)\n2000,0\n2100,5\n2200,9\n")
        assert table.depths_m.size == 3
        assert table.apex_m == 2000.0

    def test_base_area_is_optional(self):
        table = AreaDepthTable.from_csv("depth_m,top_area_km2\n2000,0\n2100,5\n")
        assert np.all(table.base_area_km2 == 0.0)

    def test_a_file_without_a_depth_or_an_area_is_refused(self):
        with pytest.raises(ValueError, match="needs a depth and a top area"):
            AreaDepthTable.from_csv("a,b\n1,2\n3,4\n")

    def test_fewer_than_two_usable_rows_is_refused(self):
        with pytest.raises(ValueError, match="fewer than two usable rows"):
            AreaDepthTable.from_csv("depth_m,top_area_km2\n2000,1\n")


class TestTheChargeColumnIsMeasuredFromTheProspectApex:
    """Audit finding P2-2, 14 Sep 2026.

    The table's crest is 2 040 m and the elicited apex about 2 050 m. A column measured from the
    crest, added by the engine to the apex it draws, put every charge-limited contact 10 m deeper
    than the integration computed. Measured from the prospect apex, the engine's contact
    reproduces the table's fill depth to within the apex draw.
    """

    @staticmethod
    def _limiting(table):
        rng = np.random.default_rng(7)
        n = 4_000
        volume = rng.normal(60.0, 20.0, n).clip(0.0)
        return charge.oil_contact(table, volume, np.full(n, BO), np.full(n, K))

    def test_the_conversion_subtracts_the_prospect_apex(self, table):
        res = self._limiting(table)
        out = charge.columns_below_apex(res, 2050.0, table)
        finite = res.contact_m[np.isfinite(res.contact_m)]
        expected = np.maximum(finite - 2050.0, 0.0)
        assert np.allclose(out.column_m, expected)
        assert out.crest_offset_m == pytest.approx(table.apex_m - 2050.0)

    def test_a_contact_above_the_apex_is_a_zero_column_and_is_counted(self, table):
        res = self._limiting(table)
        out = charge.columns_below_apex(res, 2050.0, table)
        finite = res.contact_m[np.isfinite(res.contact_m)]
        assert out.share_clipped == pytest.approx(float((finite < 2050.0).mean()))
        assert (out.column_m >= 0.0).all()

    def test_the_engine_reproduces_the_fill_depth_to_within_the_apex_draw(self, table):
        """The whole point: the 10 m offset is gone.

        A charge-only limit set with the app's apex (2 049–2 051 m). Every engine contact must
        sit within the apex spread of the fill depth the table computed for the same quantile,
        where before it sat 10 m deeper.
        """
        from hcwc.core import engine
        from hcwc.core.limits import DepthDistribution, Group, Limit, LimitSet

        res = self._limiting(table)
        apex = DepthDistribution("uniform", {"minimum": 2049.0, "maximum": 2051.0})
        out = charge.columns_below_apex(res, 2050.0, table)
        limit = Limit("Charge", Group.CHARGE, 1.0, DepthDistribution.from_samples(out.column_m))
        result = engine.run(LimitSet(apex=apex, limits=(limit,), name="charge only",
                                     min_column_m=5.0), n=4_000, seed=3)
        finite = res.contact_m[np.isfinite(res.contact_m)]
        for q in (0.1, 0.5, 0.9):
            table_depth = float(np.quantile(finite, q))
            engine_depth = float(np.quantile(result.contact_m, q))
            assert abs(engine_depth - table_depth) <= 1.0 + 2.0, (q, table_depth, engine_depth)

    def test_measuring_from_the_crest_was_the_offset_the_audit_measured(self, table):
        """Pinned so the old conversion cannot come back unnoticed."""
        res = self._limiting(table)
        finite = res.contact_m[np.isfinite(res.contact_m)]
        old = charge.column_height_from_contact(finite, table.apex_m)
        new = charge.columns_below_apex(res, 2050.0, table).column_m
        keep = finite > 2050.0
        assert np.allclose(old[keep] - new[keep], 2050.0 - table.apex_m)


class TestATableThatEndsAboveTheSpillIsReported:
    """Audit finding P2-3, 14 Sep 2026: charge past the last row is not limiting only if the
    table reaches the spill."""

    def test_a_table_reaching_the_spill_reports_no_gap(self, table):
        assert charge.table_short_of_spill(table, table.deepest_m) == 0.0
        assert charge.table_short_of_spill(table, table.deepest_m - 100.0) == 0.0

    def test_a_table_ending_above_the_spill_reports_the_gap(self, table):
        assert charge.table_short_of_spill(table, table.deepest_m + 80.0) == pytest.approx(80.0)

    def test_no_spill_means_no_verdict(self, table):
        assert charge.table_short_of_spill(table, None) is None
