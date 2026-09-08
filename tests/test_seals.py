"""Seal capacity, and the two unit traps that get the most tests.

Both conversions fail *upward* and produce capacities that look plausible on a chart, so a
correction that is not pinned is a correction that will be quietly undone. The rest is ordinary
parity against hand-computed values.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from hcwc.core import seals

# The sheet's own inputs, so parity is against its own cached numbers.
GAMMA = 33.45005225957953   # C6, = the gas correlation at 80 C
THETA = 30 * 0.0174533      # C7
R_SEAL = 3e-7               # C8
R_RES = 8e-7                # C9
RHO_W = 1.05                # C10
RHO_HC = 0.80               # C11
H = 350.0                   # C13


class TestAplinYang:
    def test_gas_interfacial_tension_matches_O8(self):
        assert seals.interfacial_tension_gas_dyne_cm(80.0) == pytest.approx(33.45005225957953)

    def test_oil_interfacial_tension_matches_O10(self):
        assert seals.interfacial_tension_oil_dyne_cm(80.0) == pytest.approx(9.778)

    def test_the_oil_fit_is_refused_where_it_goes_negative(self):
        """Linear, so it crosses zero near 132 C. Unguarded, it returns a negative tension."""
        assert seals.interfacial_tension_oil_dyne_cm(130.0) > 0
        with pytest.raises(ValueError, match="132 C"):
            seals.interfacial_tension_oil_dyne_cm(140.0)

    def test_pore_throat_radius_matches_O17(self):
        assert seals.pore_throat_radius_nm(0.4) == pytest.approx(32.4842144)

    def test_metres_form_agrees_with_nanometres(self):
        assert seals.pore_throat_radius_m(0.4) == pytest.approx(32.4842144e-9)


class TestVoidRatio:
    def test_derived_from_porosity(self):
        assert seals.void_ratio_from_porosity(0.30) == pytest.approx(0.30 / 0.70)

    def test_the_porosity_void_ratio_pair_is_inconsistent(self):
        """`O15 = 0.30` porosity and `O16 = 0.40` void ratio cannot both be true."""
        assert seals.void_ratio_from_porosity(0.30) == pytest.approx(0.4286, abs=1e-3)
        assert not math.isclose(seals.void_ratio_from_porosity(0.30), 0.40, rel_tol=0.02)

    @pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
    def test_out_of_range_porosity_rejected(self, bad):
        with pytest.raises(ValueError, match="strictly inside"):
            seals.void_ratio_from_porosity(bad)


class TestHansenPorosityDepth:
    def test_matches_D47(self):
        assert seals.porosity_from_depth(2050.0) == pytest.approx(0.24957637236999575)

    def test_round_trips(self):
        assert seals.depth_from_porosity(seals.porosity_from_depth(2050.0)) == pytest.approx(2050.0)

    def test_surface_value(self):
        assert seals.porosity_from_depth(0.0) == pytest.approx(0.71)

    def test_inverse_rejects_impossible_porosity(self):
        with pytest.raises(ValueError, match="0.71"):
            seals.depth_from_porosity(0.8)


class TestBuoyancy:
    def test_matches_C14(self):
        assert seals.buoyancy_pressure_pa(H, RHO_W, RHO_HC) == pytest.approx(858375.0)

    def test_denser_hydrocarbon_than_water_is_refused(self):
        with pytest.raises(ValueError, match="buoyant"):
            seals.buoyancy_pressure_pa(H, 1.0, 1.1)


class TestTheDyneCmConversion:
    """`/100` instead of `x 1e-3` makes the capillary pressure 10x too high."""

    def test_capillary_pressure_is_a_tenth_of_the_misconverted_value(self):
        misconverted_pc_pa = 1931239.4174391928
        correct = seals.capillary_entry_pressure_pa(GAMMA, THETA, R_SEAL)
        assert correct == pytest.approx(misconverted_pc_pa / 10.0)
        assert correct == pytest.approx(193123.94174391928)

    def test_the_conversion_constant_is_the_defensible_one(self):
        """1 dyne/cm = 1e-5 N / 1e-2 m = 1e-3 N/m, which is also 1 mN/m."""
        assert seals.DYNE_PER_CM_TO_N_PER_M == 1e-3

    def test_seal_only_column_height_is_a_tenth_of_C22(self):
        misconverted_seal_m = 787.4574586908024
        got = seals.max_column_height_m(GAMMA, THETA, R_SEAL, RHO_W, RHO_HC)
        assert got == pytest.approx(misconverted_seal_m / 10.0)
        assert got == pytest.approx(78.75, abs=0.01)


class TestTheMissingGravityTerm:
    """`C23` also omits g, so it compounds to 98.1x."""

    def test_seal_minus_reservoir_is_98x_below_C23(self):
        misconverted_with_reservoir_m = 4828.098543597981
        got = seals.max_column_height_m(GAMMA, THETA, R_SEAL, RHO_W, RHO_HC,
                                        reservoir_pore_throat_radius_m=R_RES)
        assert got == pytest.approx(misconverted_with_reservoir_m / (10.0 * seals.G), rel=1e-9)
        assert got == pytest.approx(49.2, abs=0.1)

    def test_subtracting_the_reservoir_lowers_the_capacity(self):
        seal_only = seals.max_column_height_m(GAMMA, THETA, R_SEAL, RHO_W, RHO_HC)
        with_res = seals.max_column_height_m(GAMMA, THETA, R_SEAL, RHO_W, RHO_HC,
                                             reservoir_pore_throat_radius_m=R_RES)
        assert with_res < seal_only

    def test_a_reservoir_tighter_than_the_seal_is_refused(self):
        with pytest.raises(ValueError, match="not a seal"):
            seals.max_column_height_m(GAMMA, THETA, R_SEAL, RHO_W, RHO_HC,
                                      reservoir_pore_throat_radius_m=1e-7)


class TestTheSheetContradictsItself:
    """How the defects were found, kept as a test because it is the whole argument.

    The published entry-pressure models are the independent route to the same answer. At 2050 m
    they return 67-351 m across four datasets. The correctly converted calculation gives 79 m,
    which sits among them; the mis-converted one gives 787 m, an order of magnitude above all
    four. Two routes disagreeing by an order of magnitude is how the trap gets found.
    """

    PHI_PCT = 0.71 * math.exp(-0.00051 * 2050) * 100
    RHO_W2, RHO_HC2 = 1.04, 0.70          # D50, D49

    def _heights(self):
        return {name: seals.column_height_from_entry_pressure_m(
            seals.entry_pressure_bar(name, self.PHI_PCT), self.RHO_W2, self.RHO_HC2)
            for name in seals.ENTRY_PRESSURE_MODELS}

    def test_the_four_datasets_bracket_the_corrected_answer(self):
        hs = self._heights()
        corrected = seals.max_column_height_m(GAMMA, THETA, R_SEAL, RHO_W, RHO_HC)
        assert min(hs.values()) < corrected < max(hs.values())

    def test_the_misconverted_answer_lies_above_all_four(self):
        assert 787.4574586908024 > max(self._heights().values())

    def test_the_entry_pressure_block_itself_reproduces_exactly(self):
        """`AC46` for Ibrahim at 1 % porosity, from the sheet's cached value."""
        pe = seals.ENTRY_PRESSURE_MODELS["Ibrahim"](1.0)
        assert pe == pytest.approx(47.1525697)
        assert seals.column_height_from_entry_pressure_m(pe, 1.04, 0.70) == pytest.approx(
            1413.700596630089, rel=1e-9)


class TestEntryPressureModels:
    @pytest.mark.parametrize("name, phi, expected", [
        ("Ibrahim", 1.0, 47.1525697),        # Q46
        ("Hildebrand", 1.0, 43.14587688733013),   # T46
        ("PetroMod", 1.0, 47.7505),          # W46
        ("Greenland", 1.0, 260.19),          # Z46
    ])
    def test_mid_case_matches_the_sheet(self, name, phi, expected):
        assert seals.entry_pressure_bar(name, phi) == pytest.approx(expected)

    def test_low_and_high_cases_shift_porosity_by_five_points(self):
        """`low` means low *entry pressure*, i.e. the high-porosity case."""
        mid = seals.entry_pressure_bar("Hildebrand", 25.0)
        assert seals.entry_pressure_bar("Hildebrand", 25.0, case="low") < mid
        assert seals.entry_pressure_bar("Hildebrand", 25.0, case="high") > mid
        assert seals.entry_pressure_bar("Hildebrand", 25.0, case="high") == pytest.approx(
            seals.entry_pressure_bar("Hildebrand", 20.0))

    def test_the_models_disagree_by_a_factor_of_five(self):
        """Not a bug — the honest state of the art, and why all four are offered."""
        vals = [seals.entry_pressure_bar(m, 25.0) for m in seals.ENTRY_PRESSURE_MODELS]
        assert max(vals) / min(vals) > 4.0

    def test_greenland_undefined_at_zero_porosity_becomes_nan_not_a_crash(self):
        spread = seals.entry_pressure_spread(3.0)     # high case shifts to -2 %
        assert math.isnan(spread["Greenland"]["high"])
        assert not math.isnan(spread["Hildebrand"]["high"])

    def test_unknown_model_and_case_rejected(self):
        with pytest.raises(ValueError, match="unknown model"):
            seals.entry_pressure_bar("Yielding", 25.0)
        with pytest.raises(ValueError, match="low, mid or high"):
            seals.entry_pressure_bar("Ibrahim", 25.0, case="p50")


class TestFaultPermeability:
    def test_sperrevik_matches_C34(self):
        assert seals.sperrevik_permeability_md(0.2, 2300.0, 700.0) == pytest.approx(
            0.9558238823894273)

    def test_sperrevik_falls_with_shale_gouge_ratio(self):
        vals = [seals.sperrevik_permeability_md(s, 2300.0, 700.0) for s in (0.1, 0.2, 0.4, 0.6)]
        assert vals == sorted(vals, reverse=True)

    def test_sperrevik_falls_with_burial(self):
        shallow = seals.sperrevik_permeability_md(0.2, 1000.0, 700.0)
        deep = seals.sperrevik_permeability_md(0.2, 3500.0, 700.0)
        assert deep < shallow

    def test_manzocchi_published_form(self):
        """log10(k) = -4 SGR - 0.25 log10(D) (1-SGR)^5."""
        got = seals.manzocchi_permeability_md(0.2, 100.0)
        expect = 10 ** (-4 * 0.2 - 0.25 * math.log10(100.0) * 0.8**5)
        assert got == pytest.approx(expect)

    def test_manzocchi_falls_with_throw(self):
        assert seals.manzocchi_permeability_md(0.2, 500.0) < \
               seals.manzocchi_permeability_md(0.2, 10.0)

    def test_zero_throw_refused_rather_than_returning_inf(self):
        with pytest.raises(ValueError, match="positive"):
            seals.manzocchi_permeability_md(0.2, 0.0)

    @pytest.mark.parametrize("bad", [-0.1, 1.1])
    def test_sgr_must_be_a_fraction(self, bad):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            seals.sperrevik_permeability_md(bad, 2300.0, 700.0)
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            seals.manzocchi_permeability_md(bad, 100.0)


class TestCapacityCurve:
    def test_capacity_falls_with_depth_because_porosity_does(self):
        depths = np.array([1000.0, 2000.0, 3000.0, 4000.0])
        caps = seals.max_column_height_curve(depths, 1.04, 0.70)
        assert np.all(np.diff(caps) > 0), "deeper means tighter seal means a taller column"

    def test_it_agrees_with_the_scalar_path(self):
        phi_pct = seals.porosity_from_depth(2050.0) * 100.0
        expect = seals.column_height_from_entry_pressure_m(
            seals.entry_pressure_bar("Hildebrand", phi_pct), 1.04, 0.70)
        assert seals.max_column_height_curve(np.array([2050.0]), 1.04, 0.70)[0] == pytest.approx(
            expect)


class TestExtrapolationGuards:
    """The four curves are fits, and fits misbehave outside the range they were fitted over."""

    def test_petromod_crosses_zero_at_high_porosity(self):
        assert seals.ENTRY_PRESSURE_MODELS["PetroMod"](28.0) > 0
        assert seals.ENTRY_PRESSURE_MODELS["PetroMod"](30.0) < 0

    def test_a_negative_entry_pressure_is_refused_not_converted(self):
        with pytest.raises(ValueError, match="not physical"):
            seals.column_height_from_entry_pressure_m(-5.0, 1.04, 0.70)

    def test_the_spread_returns_nan_rather_than_a_negative_pressure(self):
        spread = seals.entry_pressure_spread(35.0)
        assert math.isnan(spread["PetroMod"]["mid"])
        assert spread["Hildebrand"]["mid"] > 0, "the exponential stays positive everywhere"

    def test_the_capacity_curve_is_nan_where_a_model_breaks_down(self):
        """At 500 m the Hansen porosity is ~55 %, well past where the linear fit is meaningful."""
        shallow = seals.max_column_height_curve(np.array([500.0]), 1.04, 0.70, model="PetroMod")
        assert math.isnan(float(shallow[0]))

    def test_no_curve_ever_returns_a_negative_column(self):
        depths = np.linspace(300.0, 5000.0, 200)
        for name in seals.ENTRY_PRESSURE_MODELS:
            caps = seals.max_column_height_curve(depths, 1.04, 0.70, model=name)
            finite = caps[np.isfinite(caps)]
            assert np.all(finite > 0), f"{name} produced a non-positive column height"


class TestSampledCapacity:
    """The distribution form — `SealInputs` + `sample_max_column_m`, which feeds a limit row.

    The deterministic function answers "what column does this seal hold". A limit needs "what
    column *might* it hold", and the gap between the two is the point: `Pc ∝ 1/r`, so the spread on
    pore-throat radius dominates. These tests pin the guards that stop a physically impossible
    range being sampled silently, and the one identity that must survive vectorisation.
    """

    def test_it_agrees_with_the_deterministic_function_on_a_degenerate_range(self):
        """Every range collapsed to a point must reproduce `max_column_m` exactly.

        This is the test that would catch a unit slip introduced by the vectorisation — the same
        class of defect as B-13, one layer up.
        """
        inputs = seals.SealInputs(
            temperature_c=(80.0, 80.0), contact_angle_deg=(0.0, 0.0),
            seal_radius_um=(0.1, 0.1), reservoir_radius_um=(2.0, 2.0),
            water_density_g_cm3=(1.05, 1.05), hc_density_g_cm3=(0.75, 0.75),
            fluid="Gas", subtract_reservoir=False)
        drawn = seals.sample_max_column_m(inputs, 64)
        expected = seals.max_column_height_m(
            seals.interfacial_tension_gas_dyne_cm(80.0), 0.0, 0.1e-6, 1.05, 0.75)
        assert np.allclose(drawn, expected)
        assert drawn.std() < 1e-9 * expected  # constant to within floating-point noise

    def test_pore_throat_radius_dominates_every_other_input(self):
        """One input at a time across its default range, everything else pinned at its midpoint.

        The reason the calculator asks for ranges rather than a number, and the reason the UI names
        `r` as the input to think hardest about — stated as a test so the claim cannot quietly stop
        being true. On the defaults the seal radius produces a P10–P90 spread of about 120 m; the
        next-largest contributor, hydrocarbon density, produces about 31 m.

        Measured one-at-a-time rather than by variance decomposition because `Pc ∝ 1/r` is strongly
        non-linear, so there is no meaningful linear apportionment to do.
        """
        defaults = seals.SealInputs()
        ranged = ("temperature_c", "contact_angle_deg", "seal_radius_um", "reservoir_radius_um",
                  "water_density_g_cm3", "hc_density_g_cm3")
        pinned = {n: ((sum(getattr(defaults, n)) / 2,) * 2) for n in ranged}

        def spread(varying: str) -> float:
            kw = dict(pinned, **{varying: getattr(defaults, varying)})
            drawn = seals.sample_max_column_m(seals.SealInputs(**kw), 40_000)
            lo, hi = np.percentile(drawn, [10, 90])
            return float(hi - lo)

        by_radius = spread("seal_radius_um")
        others = {n: spread(n) for n in ranged if n != "seal_radius_um"}
        assert by_radius > 3 * max(others.values()), (by_radius, others)

    def test_subtracting_the_reservoir_can_only_lower_the_column(self):
        kw = dict(seal_radius_um=(0.10, 0.20), reservoir_radius_um=(1.0, 3.0))
        net = seals.sample_max_column_m(seals.SealInputs(subtract_reservoir=True, **kw), 5_000)
        gross = seals.sample_max_column_m(seals.SealInputs(subtract_reservoir=False, **kw), 5_000)
        assert np.median(net) < np.median(gross)
        assert (net > 0).all()

    def test_a_seal_no_tighter_than_its_reservoir_is_refused(self):
        """Not a range check for its own sake — the overlap makes the answer *negative*.

        `Pc_seal - Pc_reservoir` goes below zero when the seal's throats are the wider pair, and a
        negative column would sail through the engine as a limit shallower than the apex.
        """
        with pytest.raises(ValueError, match="tighter"):
            seals.SealInputs(seal_radius_um=(0.5, 1.2), reservoir_radius_um=(1.0, 3.0))

    def test_hydrocarbon_no_lighter_than_water_is_refused(self):
        with pytest.raises(ValueError, match="buoyant"):
            seals.SealInputs(water_density_g_cm3=(1.00, 1.10), hc_density_g_cm3=(0.95, 1.05))

    def test_an_inverted_range_is_refused(self):
        with pytest.raises(ValueError, match="must not be below"):
            seals.SealInputs(temperature_c=(90.0, 70.0))

    def test_the_oil_correlation_refuses_the_temperature_where_it_breaks_down(self):
        """Aplin & Yang's oil fit goes non-positive near 132 °C. Silently returning a negative
        interfacial tension there would produce a negative column, so it raises instead."""
        hot = seals.SealInputs(temperature_c=(120.0, 145.0), fluid="Oil",
                               hc_density_g_cm3=(0.70, 0.85))
        with pytest.raises(ValueError, match="132"):
            seals.sample_max_column_m(hot, 1_000)

    def test_the_same_seed_gives_the_same_answer(self):
        inputs = seals.SealInputs()
        assert np.array_equal(seals.sample_max_column_m(inputs, 500, 7),
                              seals.sample_max_column_m(inputs, 500, 7))
        assert not np.array_equal(seals.sample_max_column_m(inputs, 500, 7),
                                  seals.sample_max_column_m(inputs, 500, 8))

    def test_the_defaults_are_the_ones_the_ui_advertises(self):
        """Gas defaults: P90 35 m / P50 67 m / P10 ~160 m. If these move, the seal capacity shown
        under a limit row moves with them, and the caption on tab 3.0 becomes wrong."""
        p90, p50, p10 = np.percentile(
            seals.sample_max_column_m(seals.SealInputs(), 40_000), [10, 50, 90])
        assert p90 == pytest.approx(35, abs=3)
        assert p50 == pytest.approx(67, abs=4)
        assert p10 == pytest.approx(160, abs=12)


# --------------------------------------------------------------------------- Grant (2020) eq. 8
#
# The capillary path above gets two whole classes about its unit traps, because both fail upward
# and produce plausible-looking capacities. The mechanical path had none: four tests on tab 3.0
# checked that its calculator renders and is off by default, and nothing anywhere checked that it
# returns the right number. Same class of unit-sensitive physics, held to a lower standard.

#: The shipped `MechanicalSealInputs` midpoints, so the assertions below are against the case a
#: user actually meets rather than a contrived one.
S_HMIN, P_PORE = 315.0, 220.0
MECH_RHO_W, MECH_RHO_HC = 1.05, 0.775


class TestTheFractureHeadroom:
    """`S_Hmin - P_p`, Grant's equation 7, with the tensile strength folded into `S_Hmin`."""

    def test_it_is_the_difference(self):
        assert seals.fracture_headroom_bar(S_HMIN, P_PORE) == pytest.approx(95.0)

    def test_it_is_signed_rather_than_clipped(self):
        """The sign is the finding. A trap already at its fracture pressure with no hydrocarbon in
        it is a failed trap, not a short column, and `mechanical_column_m` is what decides how to
        say so -- this function must not hide the distinction by clipping first."""
        assert seals.fracture_headroom_bar(200.0, 220.0) == pytest.approx(-20.0)

    def test_it_is_vectorised(self):
        got = seals.fracture_headroom_bar([315.0, 200.0], [220.0, 220.0])
        assert got == pytest.approx([95.0, -20.0])


class TestTheBarPerMetreConversion:
    """The unit trap on this path, and it fails *downward* -- which is why it needs pinning.

    A density contrast in g/cm3 is not a pressure gradient. Dividing the headroom by the contrast
    directly, without `BAR_PER_M_PER_G_CM3`, gives a column **10.2x too short**: 345 m where the
    answer is 3 523 m. The capillary traps fail upward and shout; this one fails quietly in the
    conservative direction, and an assessor would simply believe the smaller number.
    """

    def test_the_constant_is_the_gradient_of_unit_density(self):
        """1 g/cm3 under standard gravity is 9806.65 Pa/m, and a bar is 1e5 Pa."""
        assert seals.BAR_PER_M_PER_G_CM3 == pytest.approx(0.0980665)
        assert seals.BAR_PER_M_PER_G_CM3 * 1e5 / 1000.0 == pytest.approx(9.80665)

    def test_this_module_carries_two_values_of_gravity_and_they_disagree(self):
        """Found by writing this file, 8 Sep 2026. Pinned rather than fixed.

        `seals.G` is 9.81 and is commented *Standard gravity*; it drives the capillary path.
        `BAR_PER_M_PER_G_CM3` is 0.0980665, which implies **9.80665** -- the actual standard
        value -- and it drives the mechanical path. So one module computes two limits under two
        gravities, and the one labelled *standard* is the rounded one.

        The size of it is 0.034 %: 1.2 m on the 3 523 m mechanical column, and 0.017 m on the
        49 m capillary one. Immaterial to any answer this tool gives.

        It is asserted rather than corrected because unifying them is a decision with a cost.
        `G = 9.81` is what the original workbook used, and several tests above are parity checks
        against that sheet's cached numbers; changing it moves every capillary capacity in the
        app by 0.03 % for no gain in accuracy that any seal elicitation could notice. If it is
        ever unified, this test is what will say so out loud.
        """
        implied_by_the_mechanical_path = seals.BAR_PER_M_PER_G_CM3 * 1e5 / 1000.0
        assert seals.G == 9.81
        assert implied_by_the_mechanical_path == pytest.approx(9.80665)
        assert seals.G != pytest.approx(implied_by_the_mechanical_path, rel=1e-6)
        disagreement = abs(seals.G - implied_by_the_mechanical_path) / seals.G
        assert disagreement < 0.001, "the two gravities have drifted further apart"

    def test_equivalent_mud_weight_is_the_same_number_under_another_name(self):
        assert seals.EMW_PER_BAR_PER_M == seals.BAR_PER_M_PER_G_CM3

    def test_omitting_it_is_10_2x_too_short(self):
        wrong = (S_HMIN - P_PORE) / (MECH_RHO_W - MECH_RHO_HC)
        got = float(seals.mechanical_column_m(S_HMIN, P_PORE, MECH_RHO_W, MECH_RHO_HC))
        assert wrong == pytest.approx(345.45, abs=0.01)
        assert got / wrong == pytest.approx(1.0 / seals.BAR_PER_M_PER_G_CM3, rel=1e-9)


class TestTheMechanicalColumn:
    """Grant (2020) eq. 8: `H = (S_Hmin - P_p) / (grad_w - grad_h)`."""

    def test_it_matches_the_hand_computed_case(self):
        expected = (S_HMIN - P_PORE) / ((MECH_RHO_W - MECH_RHO_HC)
                                        * seals.BAR_PER_M_PER_G_CM3)
        got = float(seals.mechanical_column_m(S_HMIN, P_PORE, MECH_RHO_W, MECH_RHO_HC))
        assert got == pytest.approx(expected, rel=1e-12)
        assert got == pytest.approx(3522.66, abs=0.01)

    def test_one_bar_of_headroom_per_tenth_of_contrast_is_10197_m(self):
        """A round anchor independent of the shipped defaults: the reciprocal of the constant,
        times ten. If the conversion is ever rewritten, this is the number that moves."""
        assert float(seals.mechanical_column_m(100.0, 0.0, 1.0, 0.9)) == pytest.approx(
            10197.16, abs=0.01)

    def test_a_normally_pressured_trap_gets_a_column_no_closure_can_reach(self):
        """The finding the tab reports rather than a defect: at these pressures the mechanism is
        correct and irrelevant, because 3.5 km of column is not a limit any real closure meets."""
        got = float(seals.mechanical_column_m(S_HMIN, P_PORE, MECH_RHO_W, MECH_RHO_HC))
        assert got > 3000.0

    def test_spent_headroom_is_no_column_rather_than_a_negative_one(self):
        """A negative column competing in the engine's `min` would win every realisation and
        report a contact above the crest."""
        assert float(seals.mechanical_column_m(200.0, 220.0, 1.05, 0.8)) == 0.0
        assert float(seals.mechanical_column_m(220.0, 220.0, 1.05, 0.8)) == 0.0

    def test_no_buoyancy_is_nan_rather_than_infinity(self):
        """Equal densities divide by zero. `inf` would be a limit that never bites, which is the
        wrong answer for inputs that describe nothing buoyant at all."""
        assert math.isnan(float(seals.mechanical_column_m(315.0, 220.0, 0.8, 0.8)))
        assert math.isnan(float(seals.mechanical_column_m(315.0, 220.0, 0.8, 1.05)))

    def test_more_headroom_holds_more_column(self):
        low = float(seals.mechanical_column_m(300.0, 220.0, 1.05, 0.8))
        high = float(seals.mechanical_column_m(340.0, 220.0, 1.05, 0.8))
        assert high > low

    def test_a_lighter_hydrocarbon_holds_less(self):
        """Gas is more buoyant than oil, so it reaches the fracture pressure in fewer metres --
        the same direction as the capillary path, for an unrelated reason."""
        oil = float(seals.mechanical_column_m(S_HMIN, P_PORE, 1.05, 0.80))
        gas = float(seals.mechanical_column_m(S_HMIN, P_PORE, 1.05, 0.25))
        assert gas < oil

    def test_it_is_vectorised_elementwise(self):
        got = seals.mechanical_column_m([315.0, 200.0], [220.0, 220.0],
                                        [1.05, 1.05], [0.775, 0.8])
        assert got[0] == pytest.approx(3522.66, abs=0.01)
        assert got[1] == 0.0


class TestMechanicalSealInputs:
    """The three refusals, each of which describes a prospect rather than a typo."""

    def test_the_shipped_defaults_are_usable(self):
        got = seals.sample_mechanical_column_m(seals.MechanicalSealInputs(), 500, seed=1)
        assert np.isfinite(got).all()
        assert (got > 0).all()

    def test_a_reversed_range_is_refused(self):
        with pytest.raises(ValueError, match="high value"):
            seals.MechanicalSealInputs(s_hmin_bar=(330.0, 300.0))

    def test_overlapping_densities_are_refused(self):
        with pytest.raises(ValueError, match="nothing buoyant"):
            seals.MechanicalSealInputs(water_density_g_cm3=(0.80, 0.90),
                                       hc_density_g_cm3=(0.85, 0.95))

    def test_a_trap_already_at_its_fracture_pressure_is_refused(self):
        """Not a short column -- a Retention failure, and the message has to say which."""
        with pytest.raises(ValueError, match="trap failure rather than a column limit"):
            seals.MechanicalSealInputs(s_hmin_bar=(200.0, 210.0),
                                       pore_pressure_bar=(215.0, 225.0))


class TestSampledMechanicalColumn:
    def test_it_is_reproducible(self):
        a = seals.sample_mechanical_column_m(seals.MechanicalSealInputs(), 200, seed=7)
        b = seals.sample_mechanical_column_m(seals.MechanicalSealInputs(), 200, seed=7)
        assert np.array_equal(a, b)

    def test_a_different_seed_gives_a_different_sample(self):
        a = seals.sample_mechanical_column_m(seals.MechanicalSealInputs(), 200, seed=7)
        b = seals.sample_mechanical_column_m(seals.MechanicalSealInputs(), 200, seed=8)
        assert not np.array_equal(a, b)

    def test_every_draw_lies_between_the_extremes_the_ranges_allow(self):
        """The sampler draws each input independently, so the tightest possible column pairs the
        least headroom with the largest contrast, and the widest does the reverse."""
        inputs = seals.MechanicalSealInputs()
        tightest = float(seals.mechanical_column_m(
            inputs.s_hmin_bar[0], inputs.pore_pressure_bar[1],
            inputs.water_density_g_cm3[1], inputs.hc_density_g_cm3[0]))
        widest = float(seals.mechanical_column_m(
            inputs.s_hmin_bar[1], inputs.pore_pressure_bar[0],
            inputs.water_density_g_cm3[0], inputs.hc_density_g_cm3[1]))
        got = seals.sample_mechanical_column_m(inputs, 2000, seed=11)
        assert got.min() >= tightest - 1e-9
        assert got.max() <= widest + 1e-9

    def test_a_degenerate_range_is_a_constant(self):
        inputs = seals.MechanicalSealInputs(s_hmin_bar=(315.0, 315.0),
                                            pore_pressure_bar=(220.0, 220.0),
                                            water_density_g_cm3=(1.05, 1.05),
                                            hc_density_g_cm3=(0.775, 0.775))
        got = seals.sample_mechanical_column_m(inputs, 50, seed=3)
        assert got == pytest.approx(3522.66, abs=0.01)
