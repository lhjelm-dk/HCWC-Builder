"""Seal capacity: capillary entry pressure, buoyancy, and the column a seal can hold.

Schowalter's (1979) balance, from published entry-pressure calibrations, with every intermediate
quantity carrying its unit in its name.

**That naming is not decoration**, and :data:`UNIT_TRAPS` is why. Two conversions in this
calculation are easy to get wrong, both fail *upward*, and both produce seal capacities that look
entirely plausible on a chart. They are stated there and asserted in ``tests/test_seals.py``.

Sources:

* **Yang & Aplin (1998)** — pore-throat radius against void ratio. The gas–water tension line
  below is of unknown provenance and is consistent with methane–brine data; the oil–water line
  that stood beside it was not, and was replaced on 15 Sep 2026 by an elicited range
  (``archive/development_notes/IFT_CHECK_2026-09-15.md``).
* **Schowalter (1979)**, **Buckley & Fan (2005)**, **Hjelmeland & Larrondo (1986)** — the
  oil–water tension range and its weak temperature dependence.
* **Hansen (1996)** — the porosity–depth calibration.
* **Sperrevik et al. (2002)**, **Manzocchi et al. (1999)** — fault-rock permeability.
* Entry-pressure-against-porosity curves from four independent datasets, reproduced as published:
  Ibrahim, Hildebrand, PetroMod(R) and Greenland.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Callable

import numpy as np

#: Standard gravity, m/s^2. One value for the whole module: until 15 Sep 2026 the capillary
#: path used 9.81 and the mechanical path 9.80665 through its bar-per-metre constant (audit
#: P3-1), a 0.03 % disagreement that no elicitation could notice and no module should carry.
G = 9.80665

#: 1 dyne/cm = 1e-5 N / 1e-2 m = 1e-3 N/m. Identical to 1 mN/m, which is how modern
#: laboratory reports quote interfacial tension.
DYNE_PER_CM_TO_N_PER_M = 1e-3

UNIT_TRAPS = """
Two conversions in this calculation are easy to get wrong. Both fail *upward*, both give a
seal capacity that looks plausible, and they compound.

1  Interfacial tension is quoted in dyne/cm. The conversion to N/m is `x 1e-3`. Doing it
   with `/100` makes the capillary entry pressure, and every column height derived from
   it, **10x too high** — 787 m where the same inputs give 79 m.

2  Schowalter's balance divides by `g x (rho_w - rho_hc)`. Dropping `g` and dividing by the
   density contrast alone is **9.81x too high** on its own, and **98.1x** combined with the
   first: 4828 m where the correct answer is 49 m.

The cross-check that catches both: the published entry-pressure models return 67-351 m across
the four datasets at 2050 m. A corrected calculation gives 79 m and sits among them. Anything
in the hundreds or thousands does not.
"""


# --------------------------------------------------------------------------- fluid properties
def interfacial_tension_gas_dyne_cm(temperature_c: float) -> float:
    """Gas/water interfacial tension against temperature.

    ``91.657·exp(−0.0126 T)``: 63 dyne/cm at 30 °C, 38 at 70 °C, 23 at 110 °C. **An empirical
    default of unrecorded provenance**: the attribution it arrived with (Aplin & Yang 1998) is
    not supported by that paper, and no source for the line has been found. Its only support is
    agreement with measured methane–brine tension at reservoir pressure
    (``archive/development_notes/IFT_CHECK_2026-09-15.md``). The tab labels it so and lets a
    measured value override it (``SealInputs.gas_tension_dyne_cm``).
    """
    return 91.657 * math.exp(-0.0126 * temperature_c)


#: Oil–water interfacial tension, dyne/cm, as an elicited range rather than a line in
#: temperature. Dead crudes against brine measure about 20–35 at ambient (Buckley & Fan 2005),
#: a 796-point compilation over 25–140 °C has a median of 23 (Sci. Rep. 2024), Schowalter
#: (1979) took 21 for 30–40 °API oils, and live-oil studies find the tension flat or rising
#: with temperature (Hjelmeland & Larrondo 1986; Sauerer et al. 2017). The line this replaced,
#: ``−0.1886 T + 24.866``, gave 11.7 at 70 °C and 4 at 110 °C, below every source found, and
#: understated the shipped oil seal capacity by about 1.9×.
DEFAULT_OIL_TENSION_DYNE_CM: tuple[float, float] = (18.0, 28.0)


# --------------------------------------------------------------------------- pore geometry
def void_ratio_from_porosity(porosity_frac: float) -> float:
    """``e = phi / (1 - phi)``.

    Provided because porosity and void ratio are commonly entered as two independent numbers and
    then disagree: 0.30 porosity is a void ratio of 0.4286, not 0.40. Deriving one from the other
    removes the chance to disagree.
    """
    if not 0.0 < porosity_frac < 1.0:
        raise ValueError(f"porosity must be a fraction strictly inside (0, 1), got {porosity_frac}")
    return porosity_frac / (1.0 - porosity_frac)


#: The void-ratio range Aplin & Yang's (1998) quartic was fitted over; porosities of about
#: 9 % to 50 %. Outside it the polynomial is an extrapolation and says so.
PORE_THROAT_FIT_VOID_RATIO = (0.1, 1.0)


def pore_throat_radius_nm(void_ratio: float) -> float:
    """Pore-throat radius in nanometres from void ratio, after Aplin & Yang (1998).

    A quartic fit, meaningful over the range it was fitted to, :data:`PORE_THROAT_FIT_VOID_RATIO`.
    Outside that range the value is returned with a ``UserWarning`` naming it an extrapolation,
    so a caller can show it as such rather than as calibrated.
    """
    e = float(void_ratio)
    lo, hi = PORE_THROAT_FIT_VOID_RATIO
    if not lo <= e <= hi:
        warnings.warn(
            f"void ratio {e:.3f} is outside the range the pore-throat fit covers ({lo} to {hi}, "
            f"porosity about 9 % to 50 %); the radius is an extrapolation, not a calibrated value",
            UserWarning, stacklevel=2)
    return 393.974 * e**4 + 463.27 * e**3 - 323.62 * e**2 + 89.439 * e + 8.7528


def pore_throat_radius_m(void_ratio: float) -> float:
    """As :func:`pore_throat_radius_nm`, in metres — the unit the pressure formulae want."""
    return pore_throat_radius_nm(void_ratio) * 1e-9


def porosity_from_depth(depth_m: float) -> float:
    """Porosity as a fraction, from the Hansen (1996) depth calibration."""
    return 0.71 * math.exp(-0.00051 * depth_m)


def depth_from_porosity(porosity_frac: float) -> float:
    """Inverse of :func:`porosity_from_depth`."""
    if not 0.0 < porosity_frac < 0.71:
        raise ValueError(
            f"the Hansen calibration reaches 0.71 at the surface and decays; "
            f"{porosity_frac} is outside (0, 0.71)"
        )
    return math.log(porosity_frac / 0.71) / -0.00051


# --------------------------------------------------------------------------- pressures
#: Mercury–air interfacial tension and contact angle, the laboratory pair behind every MICP
#: displacement pressure (Purcell 1949; the values ZetaWare's and most vendors' conversions use).
MERCURY_AIR_TENSION_DYNE_CM = 480.0
MERCURY_AIR_CONTACT_ANGLE_DEG = 140.0
PSI_TO_PA = 6894.757


def pore_throat_radius_from_micp_um(displacement_pressure_psi: float) -> float:
    """The largest connected pore-throat radius, µm, from an MICP displacement pressure.

    The Washburn relation run backwards: ``r = 2·γ_Hg·|cos θ_Hg| / P_d``. A mercury–air
    displacement pressure is what a laboratory reports for a seal sample, and it is the number
    an assessor has when a radius is not; the calculator converts it here so the rest of the
    balance is the same whichever was typed. 1 000 psi is about 0.11 µm; 10 000 psi about
    0.011 µm.
    """
    if displacement_pressure_psi <= 0:
        raise ValueError("the displacement pressure must be positive")
    gamma = MERCURY_AIR_TENSION_DYNE_CM * DYNE_PER_CM_TO_N_PER_M
    cos_theta = abs(math.cos(math.radians(MERCURY_AIR_CONTACT_ANGLE_DEG)))
    return 2.0 * gamma * cos_theta / (displacement_pressure_psi * PSI_TO_PA) * 1e6


def capillary_entry_pressure_pa(interfacial_tension_dyne_cm: float, contact_angle_rad: float,
                                pore_throat_radius_m: float) -> float:
    """``Pc = 2 gamma cos(theta) / r``, in pascals.

    **This is the function the first unit trap lives in**: converting dyne/cm with ``/100``
    instead of ``x 1e-3`` makes it ten times too large. See :data:`UNIT_TRAPS`.
    """
    if pore_throat_radius_m <= 0:
        raise ValueError("pore-throat radius must be positive")
    gamma = interfacial_tension_dyne_cm * DYNE_PER_CM_TO_N_PER_M
    return 2.0 * gamma * math.cos(contact_angle_rad) / pore_throat_radius_m


def buoyancy_pressure_pa(column_height_m: float, water_density_g_cm3: float,
                         hc_density_g_cm3: float) -> float:
    """``dP = (rho_w - rho_hc) g h``, in pascals."""
    delta_rho = (water_density_g_cm3 - hc_density_g_cm3) * 1000.0
    if delta_rho <= 0:
        raise ValueError(
            f"water density ({water_density_g_cm3}) must exceed hydrocarbon density "
            f"({hc_density_g_cm3}); nothing is buoyant otherwise"
        )
    return delta_rho * G * column_height_m


def max_column_height_m(interfacial_tension_dyne_cm: float, contact_angle_rad: float,
                        seal_pore_throat_radius_m: float, water_density_g_cm3: float,
                        hc_density_g_cm3: float,
                        reservoir_pore_throat_radius_m: float | None = None) -> float:
    """The tallest column the seal can hold, in metres.

    With ``reservoir_pore_throat_radius_m``, the reservoir's own entry pressure is subtracted —
    the physically complete form, since hydrocarbon already occupies the reservoir pores and only
    the *difference* in entry pressure has to be overcome. That is where the second unit trap
    lives — see :data:`UNIT_TRAPS`. Without it, the seal-only form.
    """
    delta_rho = (water_density_g_cm3 - hc_density_g_cm3) * 1000.0
    if delta_rho <= 0:
        raise ValueError(
            f"water density ({water_density_g_cm3}) must exceed hydrocarbon density "
            f"({hc_density_g_cm3}); nothing is buoyant otherwise"
        )
    pc = capillary_entry_pressure_pa(interfacial_tension_dyne_cm, contact_angle_rad,
                                     seal_pore_throat_radius_m)
    if reservoir_pore_throat_radius_m is not None:
        if reservoir_pore_throat_radius_m <= seal_pore_throat_radius_m:
            raise ValueError(
                "the reservoir's pore throats must be larger than the seal's, or it is not a seal; "
                f"got seal {seal_pore_throat_radius_m:g} m, reservoir "
                f"{reservoir_pore_throat_radius_m:g} m"
            )
        pc -= capillary_entry_pressure_pa(interfacial_tension_dyne_cm, contact_angle_rad,
                                          reservoir_pore_throat_radius_m)
    return pc / (delta_rho * G)


def column_height_from_entry_pressure_m(entry_pressure_bar: float, water_density_g_cm3: float,
                                        hc_density_g_cm3: float) -> float:
    """Column height from a measured or modelled entry pressure in bar.

    The independent route to the same answer, and therefore the cross-check that catches both unit
    traps: two routes disagreeing by an order of magnitude means only one of them can be right.
    """
    delta_rho = (water_density_g_cm3 - hc_density_g_cm3) * 1000.0
    if delta_rho <= 0:
        raise ValueError("water density must exceed hydrocarbon density")
    if entry_pressure_bar <= 0:
        raise ValueError(
            f"entry pressure is {entry_pressure_bar:.3g} bar, which is not physical. The four "
            f"published curves are *fits*, and the linear and polynomial ones go negative when "
            f"extrapolated to high porosity -- PetroMod crosses zero at about 28.5 %. The "
            f"chart will happily plot those negative values; this refuses them, because a rock "
            f"with no entry pressure is not a seal."
        )
    return entry_pressure_bar * 1e5 / (delta_rho * G)


# --------------------------------------------------------------------------- entry pressure models
def _ibrahim(porosity_pct: float) -> float:
    p = porosity_pct
    return (-0.0000003 * p**5 + 0.00007 * p**4 - 0.0063 * p**3
            + 0.2756 * p**2 - 5.9528 * p + 52.836)


def _hildebrand(porosity_pct: float) -> float:
    return 48.793 * math.exp(-0.123 * porosity_pct)


def _petromod(porosity_pct: float) -> float:
    return -1.7345 * porosity_pct + 49.485


def _greenland(porosity_pct: float) -> float:
    if porosity_pct <= 0:
        raise ValueError("the Greenland power law is undefined at zero porosity")
    return 260.19 * porosity_pct**-0.964


#: name -> entry pressure in **bar** from porosity in **percent**. Four independent datasets,
#: reproduced as published. They disagree by a factor of five at
#: 25 % porosity, which is the honest state of the art and is why all four are offered rather
#: than one being chosen.
#:
#: **They are fits, and they misbehave outside the porosity range they were fitted over.**
#: PetroMod is linear and crosses zero near 28.5 % porosity; Ibrahim is a quintic and turns over;
#: Greenland is a power law and diverges towards zero porosity. Callers get NaN rather than a
#: negative or absurd column height -- see :func:`column_height_from_entry_pressure_m`.
ENTRY_PRESSURE_MODELS: dict[str, Callable[[float], float]] = {
    "Ibrahim": _ibrahim,
    "Hildebrand": _hildebrand,
    "PetroMod": _petromod,
    "Greenland": _greenland,
}

#: The uncertainty convention: shift porosity by +/- 5 **percentage points**, which moves entry
#: pressure the opposite way.
POROSITY_UNCERTAINTY_PCT = 5.0


def entry_pressure_bar(model: str, porosity_pct: float, *, case: str = "mid") -> float:
    """Entry pressure in bar for one model, with low/mid/high porosity cases.

    ``case`` is ``"low"``, ``"mid"`` or ``"high"`` in **entry pressure**, not in porosity — a *low*
    entry pressure is the *high* porosity case. Naming the case after the answer rather than the
    input is deliberate: it is the seal capacity the user is reasoning about, and a
    ``-0.05 / mid / +0.05`` heading is a standing invitation to read it backwards.
    """
    if model not in ENTRY_PRESSURE_MODELS:
        raise ValueError(f"unknown model {model!r}; choose from {sorted(ENTRY_PRESSURE_MODELS)}")
    shift = {"low": +POROSITY_UNCERTAINTY_PCT, "mid": 0.0, "high": -POROSITY_UNCERTAINTY_PCT}
    if case not in shift:
        raise ValueError(f"case must be low, mid or high; got {case!r}")
    return ENTRY_PRESSURE_MODELS[model](porosity_pct + shift[case])


def entry_pressure_spread(porosity_pct: float) -> dict[str, dict[str, float]]:
    """All four models at low/mid/high, for the comparison plot. Bar."""
    out: dict[str, dict[str, float]] = {}
    for name in ENTRY_PRESSURE_MODELS:
        row = {}
        for case in ("low", "mid", "high"):
            try:
                value = entry_pressure_bar(name, porosity_pct, case=case)
            except ValueError:
                # Greenland is a power law and is undefined at or below zero porosity, which the
                # high case reaches for a shallow section. A spreadsheet shows #NUM! and says nothing.
                value = float("nan")
            # A fit extrapolated past its range can return a negative pressure. That is not a
            # weaker seal, it is no longer a seal, and it must not be plotted as a column height.
            row[case] = value if value > 0 else float("nan")
        out[name] = row
    return out


# --------------------------------------------------------------------------- fault permeability
def sperrevik_permeability_md(sgr: float, max_burial_depth_m: float,
                              faulting_depth_m: float) -> float:
    """Fault-rock permeability in mD, after Sperrevik et al. (2002).

    ``k = 80000 exp[-(19.4 SGR + 0.00403 Zmax + (0.0055 Zf - 12.5)(1 - SGR)^7)]``

    ``sgr`` is the shale gouge ratio as a **fraction**. ``faulting_depth_m`` is the depth at which
    the fault was active, which is generally shallower than the maximum burial depth.
    """
    if not 0.0 <= sgr <= 1.0:
        raise ValueError(f"SGR is a fraction in [0, 1], got {sgr}")
    exponent = (19.4 * sgr + 0.00403 * max_burial_depth_m
                + (0.0055 * faulting_depth_m - 12.5) * (1.0 - sgr) ** 7)
    return 80000.0 * math.exp(-exponent)


def manzocchi_permeability_md(sgr: float, throw_m: float, a1: float = 4.0, a2: float = 0.25,
                              a3: float = 5.0) -> float:
    """Fault-rock permeability in mD, after Manzocchi et al. (1999).

    ``log10(k) = -a1 SGR - a2 log10(D) (1 - SGR)^a3``

    Worth transcribing carefully: ``(1-SGR)*A3`` for ``(1-SGR)^A3`` is a single character and
    changes the permeability by orders of magnitude. The published form is what is implemented.
    """
    if not 0.0 <= sgr <= 1.0:
        raise ValueError(f"SGR is a fraction in [0, 1], got {sgr}")
    if throw_m <= 0:
        raise ValueError("fault throw must be positive; log10 of it is taken")
    return 10.0 ** (-a1 * sgr - a2 * math.log10(throw_m) * (1.0 - sgr) ** a3)


# --------------------------------------------------------------------------- vectorised helper
def max_column_height_curve(depths_m: np.ndarray, water_density_g_cm3: float,
                            hc_density_g_cm3: float, model: str = "Hildebrand",
                            case: str = "mid") -> np.ndarray:
    """Seal capacity against depth, via Hansen porosity and one entry-pressure model.

    The natural input to the capillary limits in the engine: it produces the column a seal can
    support at each depth, which is what the limit distribution is elicited around.
    """
    out = np.empty(np.shape(depths_m), dtype=float)
    for i, z in np.ndenumerate(np.asarray(depths_m, dtype=float)):
        phi_pct = porosity_from_depth(float(z)) * 100.0
        try:
            pe = entry_pressure_bar(model, phi_pct, case=case)
            out[i] = column_height_from_entry_pressure_m(pe, water_density_g_cm3, hc_density_g_cm3)
        except ValueError:
            out[i] = float("nan")
    return out


# --------------------------------------------------------------------------- sampled capacity
@dataclass(frozen=True)
class SealInputs:
    """Seal-capacity inputs as ranges, so the calculator can produce a *distribution*.

    The deterministic form above answers "what column does this seal hold". A limit needs "what
    column *might* it hold", and the two differ by a lot: ``Pc`` goes as ``1/r``, so the spread on
    pore-throat radius dominates everything else here. A calculator that returns one number invites
    an assessor to type it in as a mode and invent a spread — this samples the spread they actually
    stated instead.

    Each pair is a (low, high) range sampled uniformly. Uniform rather than triangular on purpose:
    nothing constrains the shape, and a PERT here would be inventing a mode nobody
    elicited.
    """
    temperature_c: tuple[float, float] = (70.0, 90.0)
    contact_angle_deg: tuple[float, float] = (0.0, 30.0)
    seal_radius_um: tuple[float, float] = (0.1, 0.5)
    reservoir_radius_um: tuple[float, float] = (0.8, 3.0)
    water_density_g_cm3: tuple[float, float] = (1.00, 1.10)
    hc_density_g_cm3: tuple[float, float] = (0.70, 0.85)
    fluid: str = "Gas"
    subtract_reservoir: bool = True
    #: Oil–water tension, used for ``fluid == "Oil"`` only. Elicited, and flat in
    #: temperature: see :data:`DEFAULT_OIL_TENSION_DYNE_CM`.
    oil_tension_dyne_cm: tuple[float, float] = DEFAULT_OIL_TENSION_DYNE_CM
    #: Gas–water tension, used for ``fluid == "Gas"`` only. ``None`` follows the temperature
    #: line :func:`interfacial_tension_gas_dyne_cm` per realisation, the default; a range
    #: overrides it, flat in temperature, where a measured value exists (15 Sep 2026).
    gas_tension_dyne_cm: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        for name in ("temperature_c", "contact_angle_deg", "seal_radius_um",
                     "reservoir_radius_um", "water_density_g_cm3", "hc_density_g_cm3",
                     "oil_tension_dyne_cm"):
            lo, hi = getattr(self, name)
            if hi < lo:
                raise ValueError(f"{name}: the high value must not be below the low one")
        if self.oil_tension_dyne_cm[0] <= 0:
            raise ValueError("the oil–water tension must be positive")
        if self.gas_tension_dyne_cm is not None:
            lo, hi = self.gas_tension_dyne_cm
            if hi < lo:
                raise ValueError("gas_tension_dyne_cm: the high value must not be below the low one")
            if lo <= 0:
                raise ValueError("the gas–water tension must be positive")
        if self.seal_radius_um[1] >= self.reservoir_radius_um[0]:
            raise ValueError(
                "the seal's pore throats overlap the reservoir's. A seal is a seal because its "
                "throats are tighter; if the ranges overlap, some realisations have a reservoir "
                "tighter than its own seal and no column at all"
            )
        if self.hc_density_g_cm3[1] >= self.water_density_g_cm3[0]:
            raise ValueError(
                "the hydrocarbon and water density ranges overlap, so some realisations have "
                "nothing buoyant"
            )
        if self.fluid not in ("Gas", "Oil"):
            raise ValueError("fluid must be 'Gas' or 'Oil'")


def sample_max_column_m(inputs: SealInputs, n: int, seed: int = 20260825) -> np.ndarray:
    """A distribution of the column the seal can hold, for use as a limit.

    Vectorised over realisations. The interfacial-tension correlation is applied per realisation
    from the sampled temperature, so a hot prospect gets a weaker seal in every draw rather than on
    average.
    """
    rng = np.random.default_rng(seed)

    def u(pair: tuple[float, float]) -> np.ndarray:
        lo, hi = pair
        return np.full(n, lo) if hi == lo else rng.uniform(lo, hi, n)

    temperature = u(inputs.temperature_c)
    if inputs.fluid == "Gas":
        gamma = (91.657 * np.exp(-0.0126 * temperature) if inputs.gas_tension_dyne_cm is None
                 else u(inputs.gas_tension_dyne_cm))
    else:
        # Elicited and flat in temperature; the line this replaced is recorded at
        # DEFAULT_OIL_TENSION_DYNE_CM. The temperature draw still happens, so the gas and oil
        # cases consume the stream identically and a fluid switch changes one factor only.
        gamma = u(inputs.oil_tension_dyne_cm)
    theta = np.radians(u(inputs.contact_angle_deg))
    r_seal = u(inputs.seal_radius_um) * 1e-6
    rho_w = u(inputs.water_density_g_cm3)
    rho_hc = u(inputs.hc_density_g_cm3)
    delta_rho = (rho_w - rho_hc) * 1000.0

    pc = 2.0 * gamma * DYNE_PER_CM_TO_N_PER_M * np.cos(theta) / r_seal
    if inputs.subtract_reservoir:
        r_res = u(inputs.reservoir_radius_um) * 1e-6
        pc = pc - 2.0 * gamma * DYNE_PER_CM_TO_N_PER_M * np.cos(theta) / r_res
    return pc / (delta_rho * G)


# --------------------------------------------------------------------------- mechanical top seal
#: Pressure gradient of a fluid of unit density, in **bar per metre**. One g/cm3 under gravity is
#: 9806.65 Pa/m, and a bar is 1e5 Pa. Derived from :data:`G` so the two paths cannot disagree.
BAR_PER_M_PER_G_CM3 = G * 1000.0 / 1e5

#: Equivalent mud weight of a gradient, in specific gravity, is the gradient divided by this.
#: Same number, kept under its own name because the two readings are used for different things and
#: `gradient / BAR_PER_M_PER_G_CM3` reads as arithmetic rather than as a unit conversion.
EMW_PER_BAR_PER_M = BAR_PER_M_PER_G_CM3


def fracture_headroom_bar(s_hmin_bar, pore_pressure_bar):
    """``S_Hmin - P_p`` — the pressure a trap can still take before the top seal hydrofractures.

    Grant (2020), equation 7: the seal fails when ``P_f >= S_Hmin + T``, with the tensile strength
    ``T`` usually taken as zero because natural flaws and pre-existing sealed fractures leave the
    intact rock's tensile strength unrepresentative. It is therefore folded into ``S_Hmin`` rather
    than asked for separately.

    A **negative or zero headroom is not a short column, it is a failed trap**: the aquifer alone
    already satisfies the fracture criterion, with no hydrocarbon buoyancy needed. That is a
    different finding from "this trap holds fifty metres": it is a failure of retention, `not G`,
    and belongs in the element chance on tab 2.0. :func:`mechanical_column_m` refuses it.
    """
    return np.asarray(s_hmin_bar, dtype=float) - np.asarray(pore_pressure_bar, dtype=float)


def mechanical_column_m(s_hmin_bar, pore_pressure_bar, water_density_g_cm3, hc_density_g_cm3):
    """The column a trap can hold before the top seal fails in tension.

    Grant (2020), equation 8::

        H = (S_Hmin - P_p) / (grad_w - grad_h)

    written there in pressure gradients. The buoyant column raises the pressure at the crest above
    the aquifer's by ``(grad_w - grad_h)`` per metre, so the headroom divided by that excess is how
    many metres fit before the crest pressure reaches ``S_Hmin``.

    **This is a different mechanism from capillary failure, not a refinement of it.** A capillary
    seal leaks when the buoyancy pressure exceeds the entry pressure of the *pore throats*; a
    mechanical seal breaks when the total pressure exceeds the *minimum stress* and the rock parts.
    The first is a property of the shale's texture, the second of the stress state, and a trap can
    be comfortable on one and against the wall on the other. Both belong in the competition.

    Grant is careful that this is a **valve, not a catastrophe**: pressure bleeds off through the
    fracture, the fracture closes and reseals, so the mechanism caps a column rather than emptying
    an accumulation. Which is exactly what a limit in this tool does.
    """
    headroom = fracture_headroom_bar(s_hmin_bar, pore_pressure_bar)
    contrast = (np.asarray(water_density_g_cm3, dtype=float)
                - np.asarray(hc_density_g_cm3, dtype=float)) * BAR_PER_M_PER_G_CM3
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(contrast > 0, headroom / contrast, np.nan)
    # Headroom already spent is a failed trap, not a column, and it is refused rather than
    # clipped: a 0 m column would enter the competition as a contact at the apex, the spike the
    # engine refuses for a depth-stated limit (red team, 22 Sep 2026). `MechanicalSealInputs`
    # refuses any range in which it can happen; this guard covers a direct call.
    out = np.asarray(out, dtype=float)
    if np.any(out < 0.0):
        share = float(np.mean(out < 0.0))
        raise ValueError(
            f"the minimum stress is at or below the pore pressure in {share:.1%} of the "
            f"realisations, so in those the trap is at its fracture pressure with no hydrocarbon "
            f"in it. That is a failed trap, not a 0 m column: carry it as Retention risk on tab "
            f"2.0 and keep this limit to the range in which the trap holds."
        )
    return out


@dataclass(frozen=True)
class MechanicalSealInputs:
    """Fracture-limited column inputs as ranges, sampled uniformly like :class:`SealInputs`.

    Pressures are **absolute, in bar, at the crest of the trap** rather than gradients, because
    that is the form the data arrives in: a leak-off or formation-integrity test gives a pressure at
    a depth, and an MDT or RFT gives a reservoir pressure at a depth. The UI defaults them from the
    crest depth at typical gradients and reports the gradients back, so a number that came from a
    gradient can still be checked against one.
    """
    s_hmin_bar: tuple[float, float] = (300.0, 330.0)
    pore_pressure_bar: tuple[float, float] = (215.0, 225.0)
    water_density_g_cm3: tuple[float, float] = (1.00, 1.10)
    hc_density_g_cm3: tuple[float, float] = (0.70, 0.85)

    def __post_init__(self) -> None:
        for name in ("s_hmin_bar", "pore_pressure_bar",
                     "water_density_g_cm3", "hc_density_g_cm3"):
            lo, hi = getattr(self, name)
            if hi < lo:
                raise ValueError(f"{name}: the high value must not be below the low one")
        if self.hc_density_g_cm3[1] >= self.water_density_g_cm3[0]:
            raise ValueError(
                "the hydrocarbon and water density ranges overlap, so some realisations have "
                "nothing buoyant"
            )
        if self.s_hmin_bar[0] <= self.pore_pressure_bar[1]:
            # Any overlap of the two ranges puts negative headroom in some realisations. Until
            # 22 Sep 2026 only total overlap was refused and the partial case was clipped to a
            # 0 m column, which entered the competition as a contact at the apex (red team).
            lo_s, hi_s = self.s_hmin_bar
            lo_p, hi_p = self.pore_pressure_bar
            every = hi_s <= lo_p
            raise ValueError(
                ("the minimum stress is at or below the pore pressure in every realisation"
                 if every else
                 f"the minimum stress range ({lo_s:,.0f} to {hi_s:,.0f} bar) overlaps the pore "
                 f"pressure range ({lo_p:,.0f} to {hi_p:,.0f} bar), so in some realisations")
                + ", the trap is at its fracture pressure with no hydrocarbon in it. That is a "
                "failed trap, not a column limit: carry that chance as Retention risk on tab 2.0, "
                "and keep this limit to a stress range above the pore pressure."
            )


def sample_mechanical_column_m(inputs: MechanicalSealInputs, n: int,
                               seed: int = 20260825) -> np.ndarray:
    """A distribution of the fracture-limited column, for use as a limit.

    Stress and pore pressure are sampled **independently**, which overstates the spread wherever
    they are coupled -- and they usually are, since pore-pressure/stress coupling is most of why a
    fracture gradient rises with overpressure at all (Swarbrick & Lahann 2016). The honest place to
    put that back is the correlation matrix on tab 3.0, where every other dependence in this tool
    lives, rather than a hidden coupling here that an assessor cannot see or override.
    """
    rng = np.random.default_rng(seed)

    def u(pair: tuple[float, float]) -> np.ndarray:
        lo, hi = pair
        return np.full(n, lo) if hi == lo else rng.uniform(lo, hi, n)

    return mechanical_column_m(u(inputs.s_hmin_bar), u(inputs.pore_pressure_bar),
                               u(inputs.water_density_g_cm3), u(inputs.hc_density_g_cm3))
