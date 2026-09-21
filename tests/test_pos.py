"""`hcwc.core.pos`: the chance, once (Phase 3 of the clean-up, 18 Sep 2026).

Equivalence tests: the eight inline products the tabs used to compute must equal the one
function, and the engine's exceedance must equal the broadcast it replaced in the calculators.
"""
from __future__ import annotations

import numpy as np
import pytest

from hcwc.core import engine, pos
from hcwc.core.limits import Group, reference_prospect


class TestAccumulationChance:
    def test_it_is_the_product_of_the_element_chances(self):
        element_pos = {Group.CHARGE: 0.9, Group.CLOSURE: 1.0, Group.RESERVOIR: 0.63,
                       Group.RETENTION: 0.72}
        assert pos.accumulation_chance(element_pos) == pytest.approx(0.9 * 1.0 * 0.63 * 0.72)
        # the expression every tab wrote out before
        assert pos.accumulation_chance(element_pos) == float(
            np.prod([float(v) for v in element_pos.values()]))

    def test_no_element_chances_reads_as_one(self):
        """The conditional reading, element risk left out, which is what the callers did."""
        assert pos.accumulation_chance({}) == 1.0
        assert pos.accumulation_chance(None) == 1.0

    def test_it_carries_no_threshold(self):
        """P(G) is the accumulation chance of any size; h_min enters through F(h_min) only."""
        element_pos = {Group.CHARGE: 0.5, Group.CLOSURE: 0.5}
        assert pos.accumulation_chance(element_pos) == 0.25


class TestChanceCurve:
    def test_it_is_the_product_at_every_threshold(self):
        result = engine.run(reference_prospect(), n=2_000, seed=1)
        grid = np.linspace(0.0, 400.0, 50)
        f = result.exceedance(grid)
        np.testing.assert_allclose(pos.chance_curve(0.4082, f), 0.4082 * f)
        assert pos.chance_curve(0.4082, result.pos) == pytest.approx(0.4082 * result.pos)


class TestDepthAxis:
    def test_it_places_a_column_at_the_median_apex(self):
        result = engine.run(reference_prospect(), n=2_000, seed=1)
        grid = np.array([0.0, 100.0])
        np.testing.assert_allclose(pos.depth_axis(result, grid),
                                   float(np.median(result.apex_m)) + grid)


def test_the_exceedance_equals_the_broadcast_it_replaced():
    """`ui/sources.py` drew a capacity curve with `(x[None, :] >= grid[:, None]).mean(axis=1)`."""
    rng = np.random.default_rng(3)
    capacity = rng.normal(150.0, 40.0, 5_000)
    grid = np.linspace(capacity.min(), capacity.max(), 240)
    np.testing.assert_allclose(engine.exceedance(capacity, grid),
                               (capacity[None, :] >= grid[:, None]).mean(axis=1))


class TestDepthSpace:
    """The exact depth-space exceedance against the column-space one (8.1.4)."""

    def test_a_wide_apex_separates_the_two_readings(self):
        """With depth-conversion uncertainty on the apex, F(h) shifted by the median apex and
        the exact depth-space curve differ; the well reads the exact one (P1-3 of the audit)."""
        import dataclasses

        from hcwc.core.limits import DepthDistribution
        wide = dataclasses.replace(
            reference_prospect(),
            apex=DepthDistribution("normal_alt", {"p1": 0.10, "x1": 2020.0, "p2": 0.90, "x2": 2080.0}))
        result = engine.run(wide, 4_000, seed=3)
        assert np.ptp(result.apex_m) > 40.0
        apex = float(np.median(result.apex_m))
        z = np.linspace(2100.0, 2400.0, 60)
        shifted = result.exceedance(z - apex)
        exact = pos.depth_exceedance(result, z)
        assert np.max(np.abs(shifted - exact)) > 0.02
        # and the well reading is the exact one
        z_well = 2230.0
        well = float(engine.exceedance(result.contact_m, z_well)[0])
        assert well == pytest.approx(float(pos.depth_exceedance(result, z_well)[0]))

    def test_it_is_the_exceedance_of_the_realised_contacts(self):
        result = engine.run(reference_prospect(), 3_000, seed=1)
        z = np.array([2150.0, 2230.0, 2300.0])
        np.testing.assert_allclose(pos.depth_exceedance(result, z),
                                   engine.exceedance(result.contact_m, z))
        w = np.random.default_rng(0).uniform(0.1, 1.0, result.n)
        np.testing.assert_allclose(pos.depth_exceedance(result, z, w),
                                   engine.exceedance(result.contact_m, z, w))

    def test_it_equals_the_column_curve_when_the_apex_is_pinned(self):
        result = engine.run(reference_prospect(), 3_000, seed=1)
        apex = float(np.median(result.apex_m))
        h = np.linspace(0.0, 350.0, 50)
        by_column = result.exceedance(h)
        by_depth = pos.depth_exceedance(result, apex + h)
        # the shipped apex spans about 3 m, so the two agree to a few thousandths
        assert np.max(np.abs(by_column - by_depth)) < 0.01

    def test_the_well_reading_is_the_curve_at_the_entry_depth(self):
        result = engine.run(reference_prospect(), 3_000, seed=1)
        z_well = 2230.0
        curve = pos.depth_exceedance(result, pos.depth_grid(result))
        at_well = float(np.interp(z_well, pos.depth_grid(result), curve))
        exact = float(pos.depth_exceedance(result, z_well)[0])
        assert abs(at_well - exact) < 0.01

    def test_the_grid_spans_the_run(self):
        result = engine.run(reference_prospect(), 2_000, seed=1)
        z = pos.depth_grid(result, 50)
        assert z[0] == pytest.approx(float(result.apex_m.min()))
        assert z[-1] >= float(result.contact_m.max())
        assert z.shape == (50,)
