"""The engine, checked against analytic cases.

A Monte Carlo cannot be validated trial-for-trial against anything. What it *can* be validated
against is arithmetic that has a closed form: one active limit
must reproduce that limit exactly; two independent limits must satisfy
``P(min > z) = P(A > z) P(B > z)``; a limit at ``p_active = 0`` must never win. Those pin the
construction, and they are stronger than a parity number would be because they say *why*.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from hcwc.core import engine
from hcwc.core import limits as limits_mod
from hcwc.core.limits import DepthDistribution, Group, Limit, LimitSet, reference_prospect

N = 40_000


def one_limit(minimum: float, maximum: float, p: float = 1.0, name: str = "A") -> Limit:
    return Limit(name, Group.CLOSURE, p, DepthDistribution("uniform",
                                                           {"minimum": minimum, "maximum": maximum}))


def flat_apex(depth: float = 2000.0) -> DepthDistribution:
    return DepthDistribution("fixed", {"value": depth})


class TestSingleLimit:
    def test_one_uniform_limit_reproduces_that_uniform(self):
        ls = LimitSet(apex=flat_apex(), limits=(one_limit(100.0, 300.0),))
        r = engine.run(ls, N)
        assert r.column_m.min() >= 100.0
        assert r.column_m.max() <= 300.0
        assert r.column_m.mean() == pytest.approx(200.0, abs=2.0)

    def test_the_contact_is_apex_plus_column(self):
        ls = LimitSet(apex=flat_apex(2000.0), limits=(one_limit(100.0, 300.0),))
        r = engine.run(ls, 1000)
        assert np.allclose(r.contact_m, 2000.0 + r.column_m)

    def test_the_only_limit_always_controls(self):
        ls = LimitSet(apex=flat_apex(), limits=(one_limit(100.0, 300.0),))
        r = engine.run(ls, 1000)
        assert r.controlling_shares() == {"A": 1.0}


class TestCompetingLimits:
    """`P(min > z) = P(A > z) P(B > z)` for independent limits — the identity the whole model rests on."""

    def build(self):
        return LimitSet(apex=flat_apex(), limits=(
            one_limit(0.0, 400.0, name="A"),
            one_limit(0.0, 600.0, name="B"),
        ))

    @pytest.mark.parametrize("z", [50.0, 100.0, 200.0, 300.0])
    def test_the_product_rule_holds(self, z):
        r = engine.run(self.build(), 200_000)
        got = float(r.exceedance(z)[0])
        expect = max(0.0, 1 - z / 400.0) * max(0.0, 1 - z / 600.0)
        assert got == pytest.approx(expect, abs=0.006)

    def test_the_shallower_limit_wins_more_often(self):
        shares = engine.run(self.build(), N).controlling_shares()
        assert shares["A"] > shares["B"]
        assert shares["A"] + shares["B"] == pytest.approx(1.0)

    def test_the_winner_is_the_minimum_of_the_active_ones(self):
        r = engine.run(self.build(), 5000)
        effective = np.where(r.active, r.sampled_m, np.inf)
        assert np.allclose(r.column_m, effective.min(axis=1))
        assert np.array_equal(r.controller, effective.argmin(axis=1))


class TestActivation:
    def test_an_inactive_limit_never_controls(self):
        ls = LimitSet(apex=flat_apex(), limits=(
            one_limit(200.0, 400.0, name="always"),
            one_limit(1.0, 5.0, p=0.0, name="never"),
        ))
        r = engine.run(ls, N)
        assert r.controlling_shares()["never"] == 0.0
        assert r.column_m.min() >= 200.0, "the switched-off shallow limit must not bite"

    def test_activation_frequency_matches_p_active(self):
        ls = LimitSet(apex=flat_apex(), limits=(
            one_limit(500.0, 600.0, name="always"),
            one_limit(100.0, 200.0, p=0.3, name="sometimes"),
        ))
        r = engine.run(ls, N)
        assert r.active[:, 1].mean() == pytest.approx(0.3, abs=0.01)
        # It is always shallower when it fires, so its share *is* its probability.
        assert r.controlling_shares()["sometimes"] == pytest.approx(0.3, abs=0.01)

    def test_a_set_with_no_always_active_limit_is_refused(self):
        with pytest.raises(ValueError, match="p_active = 1"):
            LimitSet(apex=flat_apex(), limits=(one_limit(100.0, 200.0, p=0.9),))

    def test_the_refusal_explains_the_large_finite_sentinel(self):
        """The refusal has to name the failure mode it prevents, not just the rule it enforces.

        Substituting a large finite depth for an inactive limit is the obvious shortcut and it
        produces a 10 km column instead of an error, which is why the message says so.
        """
        with pytest.raises(ValueError, match="10 km column"):
            LimitSet(apex=flat_apex(), limits=(one_limit(100.0, 200.0, p=0.5),))


class TestExceedanceAndPos:
    def test_exceedance_is_monotone_decreasing(self):
        r = engine.run(reference_prospect(), N)
        grid = np.linspace(0.0, 500.0, 60)
        f = r.exceedance(grid)
        assert np.all(np.diff(f) <= 1e-12)

    def test_exceedance_at_zero_is_one(self):
        r = engine.run(reference_prospect(), 5000)
        assert r.exceedance(0.0)[0] == pytest.approx(1.0)

    def test_pos_is_exceedance_read_at_the_assessment_minimum(self):
        """The point of `docs/DHI_alignment.md`: POS is a reading, not a separate number."""
        base = reference_prospect()
        ls = LimitSet(apex=base.apex, limits=base.limits, min_column_m=150.0)
        r = engine.run(ls, N)
        assert r.pos == pytest.approx(float(r.exceedance(150.0)[0]))

    def test_a_higher_minimum_gives_a_lower_pos(self):
        base = reference_prospect()
        poss = []
        for h_min in (0.0, 100.0, 200.0, 300.0):
            ls = LimitSet(apex=base.apex, limits=base.limits, min_column_m=h_min)
            poss.append(engine.run(ls, N).pos)
        assert poss == sorted(poss, reverse=True)

    def test_the_assessment_minimum_flags_rather_than_drops(self):
        base = reference_prospect()
        ls = LimitSet(apex=base.apex, limits=base.limits, min_column_m=200.0)
        r = engine.run(ls, 5000)
        assert r.n == 5000, "failures stay in the array so POS and the contact reconcile"
        assert r.above_minimum.sum() < 5000


class TestGroupMinima:
    def test_a_group_minimum_is_at_least_the_overall_minimum(self):
        r = engine.run(reference_prospect(), 20_000)
        for group in (Group.CHARGE, Group.CLOSURE, Group.RETENTION):
            assert np.all(r.group_minimum(group) >= r.column_m - 1e-9)

    def test_the_overall_minimum_is_the_minimum_over_groups(self):
        r = engine.run(reference_prospect(), 20_000)
        stacked = np.vstack([r.group_minimum(g) for g in Group])
        assert np.allclose(stacked.min(axis=0), r.column_m)

    def test_an_empty_group_returns_infinity_not_an_error(self):
        r = engine.run(reference_prospect(), 500)
        assert np.all(np.isinf(r.group_minimum(Group.RESERVOIR)))


class TestControllingShares:
    def test_shares_sum_to_one(self):
        r = engine.run(reference_prospect(), N)
        assert sum(r.controlling_shares().values()) == pytest.approx(1.0)
        assert sum(r.controlling_shares(successes_only=True).values()) == pytest.approx(1.0)

    def test_restricting_to_successes_changes_the_answer(self):
        """The selection effect this tool criticises elsewhere, committed one level up if ignored."""
        base = reference_prospect()
        ls = LimitSet(apex=base.apex, limits=base.limits, min_column_m=200.0)
        r = engine.run(ls, N)
        allc = r.controlling_shares()
        succ = r.controlling_shares(successes_only=True)
        assert any(abs(allc[k] - succ[k]) > 0.02 for k in allc)

    def test_a_severe_limit_is_under_represented_among_survivors(self):
        """A limit that usually kills the prospect is rarer among successes *because* it is severe."""
        ls = LimitSet(apex=flat_apex(), min_column_m=100.0, limits=(
            one_limit(300.0, 400.0, name="benign"),
            one_limit(5.0, 20.0, p=0.4, name="severe"),
        ))
        r = engine.run(ls, N)
        assert r.controlling_shares()["severe"] == pytest.approx(0.4, abs=0.01)
        assert r.controlling_shares(successes_only=True)["severe"] == 0.0

    def test_ranking_is_sorted_and_complete(self):
        ranking = engine.limit_ranking(engine.run(reference_prospect(), N))
        assert [v for _, v in ranking] == sorted([v for _, v in ranking], reverse=True)
        assert len(ranking) == len(reference_prospect())


class TestControllingShareByDepth:
    def test_columns_sum_to_one_in_populated_bins(self):
        r = engine.run(reference_prospect(), N)
        edges = np.linspace(r.contact_m.min(), r.contact_m.max(), 12)
        shares = engine.controlling_share_by_depth(r, edges)
        stacked = np.vstack(list(shares.values()))
        populated = stacked.sum(axis=0) > 0
        assert np.allclose(stacked.sum(axis=0)[populated], 1.0)

    def test_needs_at_least_two_edges(self):
        r = engine.run(reference_prospect(), 500)
        with pytest.raises(ValueError, match="two bin edges"):
            engine.controlling_share_by_depth(r, np.array([2000.0]))


class TestReproducibility:
    def test_the_same_seed_gives_the_same_run(self):
        a = engine.run(reference_prospect(), 5000, seed=7)
        b = engine.run(reference_prospect(), 5000, seed=7)
        assert np.array_equal(a.column_m, b.column_m)
        assert np.array_equal(a.controller, b.controller)

    def test_a_different_seed_gives_a_different_run(self):
        a = engine.run(reference_prospect(), 5000, seed=7)
        b = engine.run(reference_prospect(), 5000, seed=8)
        assert not np.array_equal(a.column_m, b.column_m)
        assert a.column_m.mean() == pytest.approx(b.column_m.mean(), rel=0.05)

    def test_zero_realisations_refused(self):
        with pytest.raises(ValueError, match="at least one"):
            engine.run(reference_prospect(), 0)


class TestPercentileExport:
    def test_exceedance_percentiles_run_shallow_to_deep(self):
        r = engine.run(reference_prospect(), N)
        p = r.percentiles(np.array([100.0, 90.0, 50.0, 10.0, 0.0]))
        assert np.all(np.diff(p) > 0), "P100 shallowest, P0 deepest"

    def test_p50_is_the_median_contact_of_the_success_cases(self):
        r = engine.run(reference_prospect(), N)
        assert r.percentiles(50.0)[0] == pytest.approx(
            float(np.median(r.contact_m[r.above_minimum])))


class TestLimitSetSerialisation:
    def test_round_trips_through_json(self, tmp_path):
        original = reference_prospect()
        loaded = LimitSet.load(original.save(tmp_path / "prospect.json"))
        assert loaded.to_dict() == original.to_dict()

    def test_a_reloaded_set_reproduces_the_run(self, tmp_path):
        original = reference_prospect()
        loaded = LimitSet.load(original.save(tmp_path / "p.json"))
        assert np.array_equal(engine.run(original, 3000, seed=3).column_m,
                              engine.run(loaded, 3000, seed=3).column_m)

    def test_the_saved_form_is_readable_json(self, tmp_path):
        path = reference_prospect().save(tmp_path / "p.json")
        d = json.loads(path.read_text(encoding="utf-8"))
        assert d["limits"][0]["name"] == "Charge"
        assert d["apex"]["kind"] == "normal_alt"


class TestLimitValidation:
    def test_duplicate_names_refused(self):
        with pytest.raises(ValueError, match="unique"):
            LimitSet(apex=flat_apex(), limits=(one_limit(1.0, 2.0, name="X"),
                                               one_limit(3.0, 4.0, name="X")))

    def test_unknown_distribution_refused(self):
        with pytest.raises(ValueError, match="unknown distribution"):
            DepthDistribution("gaussian", {"mu": 1.0})

    def test_a_missing_parameter_is_named(self):
        with pytest.raises(ValueError, match="maximum"):
            DepthDistribution("uniform", {"minimum": 1.0})

    def test_an_unexpected_parameter_is_refused_not_ignored(self):
        """A typo that is silently ignored becomes a wrong distribution that still runs."""
        with pytest.raises(ValueError, match="does not take"):
            DepthDistribution("uniform", {"minimum": 1.0, "maximum": 2.0, "mode": 1.5})

    def test_probability_out_of_range_names_the_limit(self):
        with pytest.raises(ValueError, match="Fault 9"):
            Limit("Fault 9", Group.CLOSURE, 1.4,
                  DepthDistribution("uniform", {"minimum": 1.0, "maximum": 2.0}))

    def test_an_unnamed_limit_is_refused(self):
        with pytest.raises(ValueError, match="needs a name"):
            Limit("  ", Group.CLOSURE, 1.0,
                  DepthDistribution("uniform", {"minimum": 1.0, "maximum": 2.0}))


class TestReferenceProspect:
    def test_it_runs_and_looks_like_the_reference_case(self):
        r = engine.run(reference_prospect(), N)
        assert 2050.0 < np.median(r.contact_m) < 2350.0
        assert r.column_m.min() > 0

    def test_every_group_except_reservoir_is_represented(self):
        from hcwc.core.limits import group_totals
        totals = group_totals(reference_prospect().limits)
        assert totals[Group.CHARGE] and totals[Group.CLOSURE] and totals[Group.RETENTION]
        assert totals[Group.RESERVOIR] == 0, "the reference prospect has no reservoir pinchout"

    def test_the_contact_never_exceeds_the_closure(self):
        """Closure is always active, so nothing can be deeper than spill."""
        r = engine.run(reference_prospect(), 20_000)
        spill_idx = reference_prospect().names.index("Closure / spill")
        assert np.all(r.column_m <= r.sampled_m[:, spill_idx] + 1e-9)


class TestLimitColours:
    """Hue carries the risk element, lightness separates the limits inside it."""

    def colours(self):
        from hcwc.ui.results_tab import limit_colours
        return limit_colours(reference_prospect())

    def test_every_limit_gets_its_own_colour(self):
        c = self.colours()
        assert set(c) == set(reference_prospect().names)
        assert len(set(c.values())) == len(c), "colouring by element alone made retention unreadable"

    def test_the_elements_use_the_e_pos_palette(self):
        from hcwc.ui import theme
        assert theme.PILLAR_COLOURS == {
            "Charge": "#F69292", "Closure": "#8CB7FC",
            "Reservoir": "#FFD44B", "Retention": "#B5E6A2",
        }

    def test_the_pure_element_colour_is_reserved(self):
        """Lars's rule: a limit is a *variation* of its element's hue, never the hue itself."""
        from hcwc.ui import theme
        pure = {v.upper() for v in theme.PILLAR_COLOURS.values()}
        assert not (pure & {v.upper() for v in self.colours().values()})

    def test_retention_limits_are_all_greens(self):
        """Fault leakage and the seals are retention mechanisms, so they are greens."""
        c = self.colours()
        retention = [name for name, g in zip(reference_prospect().names, reference_prospect().groups)
                     if g is Group.RETENTION]
        assert len(retention) >= 4
        for name in retention:
            r, g, b = (int(c[name][i:i + 2], 16) for i in (1, 3, 5))
            assert g > r and g > b, f"{name} is not green: {c[name]}"

    def test_closure_limits_are_all_blues(self):
        c = self.colours()
        for name, group in zip(reference_prospect().names, reference_prospect().groups):
            if group is Group.CLOSURE:
                r, g, b = (int(c[name][i:i + 2], 16) for i in (1, 3, 5))
                assert b > r and b > g, f"{name} is not blue: {c[name]}"

    def test_shading_goes_both_ways(self):
        from hcwc.ui.theme import shade_hex
        base = "#8CB7FC"
        assert shade_hex(base, 0.0).upper() == base.upper()
        assert shade_hex(base, 1.0).upper() == "#FFFFFF"
        assert shade_hex(base, -1.0).upper() == "#000000"
        lighter = shade_hex(base, 0.4)
        darker = shade_hex(base, -0.4)
        for i in (1, 3, 5):
            assert int(darker[i:i + 2], 16) < int(base[i:i + 2], 16) < int(lighter[i:i + 2], 16)

    def test_a_single_member_group_still_avoids_the_base(self):
        from hcwc.ui import theme
        only = theme.element_shades("Charge", 1)
        assert len(only) == 1
        assert only[0].upper() != theme.PILLAR_COLOURS["Charge"].upper()

    def test_shades_are_distinct_for_any_group_size(self):
        from hcwc.ui import theme
        for count in range(1, 9):
            shades = theme.element_shades("Retention", count)
            assert len(set(shades)) == count, f"{count} members collided"

    def test_an_unknown_element_is_an_error(self):
        from hcwc.ui import theme
        with pytest.raises(KeyError, match="unknown risk element"):
            theme.element_shades("Migration", 3)


class TestGroupEnumIsNotNumpySafe:
    """`np.array` on a str-Enum stringifies and truncates. Caught in the UI; pinned here.

    `np.array(limit_set.groups)` gives dtype `<U9` holding `'Group.CHA'`, `'Group.CLO'` and so on
    — the `str()` of the member, cut to the array's width — so comparing it against a `Group`
    silently returns nonsense instead of raising. Counting with `is` is the fix.
    """

    def test_numpy_mangles_the_enum(self):
        arr = np.array(reference_prospect().groups)
        assert arr.dtype.kind == "U"
        assert str(arr[0]).startswith("Group.")
        assert str(arr[0]) != Group.CHARGE.value

    def test_the_numpy_comparison_gives_the_wrong_count(self):
        arr = np.array(reference_prospect().groups)
        assert int((arr == Group.CHARGE).sum()) == 0        # there is one Charge limit

    def test_counting_with_is_gives_the_right_answer(self):
        groups = reference_prospect().groups
        assert sum(1 for g in groups if g is Group.CHARGE) == 1
        assert sum(1 for g in groups if g is Group.CLOSURE) == 2
        assert sum(1 for g in groups if g is Group.RETENTION) == 6
        assert sum(1 for g in groups if g is Group.RESERVOIR) == 0

    def test_indices_in_agrees(self):
        """`LimitSet.indices_in` uses `is` already, which is why the engine was never wrong."""
        ls = reference_prospect()
        for group in Group:
            assert ls.indices_in(group).size == sum(1 for g in ls.groups if g is group)


class TestDepthStatedLimits:
    """[D-33] A limit may be stated in m TVDSS instead of metres of column below the apex.

    The reason is that the two are natural for different things. A spill point, a fault
    juxtaposition window and a wedge pinch-out are read off a depth-converted map, and an assessor
    states them as depths. A seal capacity and a fault leakage threshold are *capacities* -- they do
    not move when the apex pick moves, and stating them as depths would make the assessor add the
    apex in their head every time.
    """

    @staticmethod
    def _one_limit(dist, kind, apex=2000.0):
        """A single always-active limit against a *fixed* apex, so the conversion is exact."""
        return LimitSet(
            apex=DepthDistribution("fixed", {"value": apex}),
            limits=(Limit("only", Group.CLOSURE, 1.0, dist, kind=kind),),
            name="test")

    def test_a_depth_limit_and_its_column_equivalent_agree_exactly(self):
        """The identity the whole feature rests on: with the apex fixed at 2000 m, a spill stated
        as 2200-2400 m TVDSS must give the same contacts as one stated as 200-400 m of column."""
        as_depth = self._one_limit(
            DepthDistribution("uniform", {"minimum": 2200.0, "maximum": 2400.0}), limits_mod.DEPTH)
        as_column = self._one_limit(
            DepthDistribution("uniform", {"minimum": 200.0, "maximum": 400.0}), limits_mod.COLUMN)
        a, b = engine.run(as_depth, 5_000, 7), engine.run(as_column, 5_000, 7)
        assert np.allclose(a.contact_m, b.contact_m)
        assert np.allclose(a.column_m, b.column_m)

    def test_the_conversion_uses_the_apex_of_the_same_realisation(self):
        """Not the mean apex. A depth-stated limit is a fixed surface, so as the apex draw moves
        the *column* moves with it while the contact stays put -- which is the whole difference
        between the two parameterisations."""
        spill_at = 2300.0
        limit_set = LimitSet(
            apex=DepthDistribution("uniform", {"minimum": 2000.0, "maximum": 2100.0}),
            limits=(Limit("spill", Group.CLOSURE, 1.0,
                          DepthDistribution("fixed", {"value": spill_at}),
                          kind=limits_mod.DEPTH),),
            name="test")
        r = engine.run(limit_set, 4_000)
        assert np.allclose(r.contact_m, spill_at)          # the surface does not move
        assert r.column_m.std() > 10.0                     # the column does
        assert np.allclose(r.column_m, spill_at - r.apex_m)

    def test_a_depth_limit_above_the_apex_is_refused_not_clipped(self):
        """The hazard the parameterisation introduces, and the reason it is a hard error.

        Apex and spill are picked off the *same* depth-converted surface, so treating them as
        independent draws is wrong in both directions -- the paper's own errors-in-variables problem
        arriving inside the tool. Clipping the negative column to zero would put a spike of
        realisations exactly at the apex, which reads as a geological result and is not one.
        """
        limit_set = LimitSet(
            apex=DepthDistribution("uniform", {"minimum": 2000.0, "maximum": 2400.0}),
            limits=(Limit("spill", Group.CLOSURE, 1.0,
                          DepthDistribution("uniform", {"minimum": 2100.0, "maximum": 2200.0}),
                          kind=limits_mod.DEPTH),),
            name="test")
        with pytest.raises(ValueError, match="above the apex"):
            engine.run(limit_set, 4_000)

    def test_the_refusal_names_the_limit_and_says_what_to_do(self):
        limit_set = LimitSet(
            apex=DepthDistribution("uniform", {"minimum": 2000.0, "maximum": 2400.0}),
            limits=(Limit("Wedge pinch-out", Group.CLOSURE, 1.0,
                          DepthDistribution("uniform", {"minimum": 2100.0, "maximum": 2200.0}),
                          kind=limits_mod.DEPTH),),
            name="test")
        with pytest.raises(ValueError) as exc:
            engine.run(limit_set, 2_000)
        message = str(exc.value)
        assert "Wedge pinch-out" in message
        assert "correlate" in message and "not clipped" in message

    def test_mixed_kinds_compete_on_the_same_axis(self):
        """A depth-stated spill and a column-stated seal must be comparable, or the argmin is
        meaningless. The seal is tighter here, so it should win most realisations."""
        limit_set = LimitSet(
            apex=DepthDistribution("uniform", {"minimum": 2000.0, "maximum": 2010.0}),
            limits=(Limit("spill", Group.CLOSURE, 1.0,
                          DepthDistribution("uniform", {"minimum": 2400.0, "maximum": 2500.0}),
                          kind=limits_mod.DEPTH),
                    Limit("top seal", Group.RETENTION, 1.0,
                          DepthDistribution("uniform", {"minimum": 50.0, "maximum": 150.0}),
                          kind=limits_mod.COLUMN)),
            name="test")
        r = engine.run(limit_set, 5_000)
        assert r.controlling_shares()["top seal"] == pytest.approx(1.0, abs=0.01)
        assert r.column_m.max() <= 150.0 + 1e-9

    def test_kind_round_trips_through_json(self):
        limit = Limit("spill", Group.CLOSURE, 1.0,
                      DepthDistribution("fixed", {"value": 2300.0}), kind=limits_mod.DEPTH)
        assert Limit.from_dict(limit.to_dict()).kind == limits_mod.DEPTH

    def test_an_old_limit_set_without_kind_still_loads_as_a_column(self):
        """Every limit set written before the depth option existed meant column height, and must go
        on meaning it."""
        payload = {"name": "spill", "group": "Closure", "p_active": 1.0,
                   "distribution": {"kind": "fixed", "params": {"value": 300.0}}}
        assert Limit.from_dict(payload).kind == limits_mod.COLUMN

    def test_an_unknown_kind_is_refused(self):
        with pytest.raises(ValueError, match="kind must be"):
            Limit("x", Group.CLOSURE, 1.0, DepthDistribution("fixed", {"value": 1.0}),
                  kind="tvdss")

    def test_the_unit_label_says_which_space_a_figure_is_in(self):
        dist = DepthDistribution("fixed", {"value": 1.0})
        assert "TVDSS" in Limit("a", Group.CLOSURE, 1.0, dist, kind=limits_mod.DEPTH).unit_label
        assert "column" in Limit("b", Group.CLOSURE, 1.0, dist, kind=limits_mod.COLUMN).unit_label


class TestBeha2012PublishedExample:
    """Parity against a **published, independently computed** competing-limits case.

    Beha, Christensen & Young (2012), *A general method for the consistent volume assessment of
    complex hydrocarbon traps*, J. Petroleum Geology 35(1), 85–98. DONG E&P and Rose & Associates.

    Their worked example is a faulted four-way closure with a crest at 2000 m:

    * NE fault cuts top reservoir at **2050 m**, P(seals) = 0.4
    * SW fault cuts top reservoir at **2100 m**, P(seals) = 0.7
    * lowest closing contour (spill) at **2150 m**

    They enumerate four scenarios by hand (their Tables 1–2) and collapse them onto three leak
    points: **0.60 at 2050 m, 0.12 at 2100 m, 0.28 at 2150 m**. Note the deepest outcome is *not*
    the least likely, which they flag as counter-intuitive.

    This matters more than an ordinary test. Every other validation in this repo is internal —
    analytic identities and self-consistency, which cannot catch a shared misconception. This is
    the only check against a number somebody else computed, and the engine reproduces all three to
    Monte Carlo error.
    """

    @staticmethod
    def _limit_set():
        return LimitSet(
            apex=DepthDistribution("fixed", {"value": 2000.0}),
            limits=(
                Limit("NE fault", Group.RETENTION, 0.6,
                      DepthDistribution("fixed", {"value": 2050.0}), kind=limits_mod.DEPTH),
                Limit("SW fault", Group.RETENTION, 0.3,
                      DepthDistribution("fixed", {"value": 2100.0}), kind=limits_mod.DEPTH),
                Limit("Spill point", Group.CLOSURE, 1.0,
                      DepthDistribution("fixed", {"value": 2150.0}), kind=limits_mod.DEPTH),
            ), name="Beha et al. (2012) example")

    def test_the_three_leak_point_frequencies_match_the_paper(self):
        result = engine.run(self._limit_set(), 400_000, seed=7)
        for depth, published in ((2050.0, 0.60), (2100.0, 0.12), (2150.0, 0.28)):
            got = float(np.mean(np.isclose(result.contact_m, depth)))
            assert got == pytest.approx(published, abs=0.004), f"{depth:.0f} m"

    def test_the_deepest_outcome_is_not_the_least_likely(self):
        """The point Beha et al. call counter-intuitive, and the reason the enumeration is worth
        doing rather than guessed at: filling to spill needs *both* faults to seal (0.28), yet it
        is more likely than the intermediate leak point (0.12), because that one needs the NE fault
        to seal *and* the SW fault to fail."""
        result = engine.run(self._limit_set(), 200_000, seed=11)
        at = {d: float(np.mean(np.isclose(result.contact_m, d))) for d in (2050.0, 2100.0, 2150.0)}
        assert at[2150.0] > at[2100.0]
        assert at[2050.0] > at[2150.0]

    def test_a_shallow_leak_absorbs_the_deeper_fault_entirely(self):
        """Their Scenarios 3 and 4 share a leak point: once the NE fault leaks, the SW fault's
        state cannot matter. The argmin gives that for free, and the share at 2050 m is therefore
        P(NE leaks) exactly, not P(NE leaks AND SW leaks)."""
        result = engine.run(self._limit_set(), 200_000, seed=13)
        assert float(np.mean(np.isclose(result.contact_m, 2050.0))) == pytest.approx(0.6, abs=0.005)
