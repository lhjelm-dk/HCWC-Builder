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
